#!/usr/bin/env python3
"""Independently validate observed events, replay a memory-image model, and reconcile metrics."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import re


class InvalidLog(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidLog(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def hexadecimal(value, bits):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]+", value) is not None,
            "invalid or unknown hex value")
    number = int(value, 16)
    require(number < 1 << bits, "hex field exceeds width")
    return number


def image_file(path):
    image = {}
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        require(len(parts) == 2, "invalid memory-image row")
        address, value = hexadecimal(parts[0], 34), hexadecimal(parts[1], 8)
        require(address not in image, "duplicate image byte")
        image[address] = value
    return image


def word_at(image, address):
    return int.from_bytes(bytes(image.get(address + offset, 0) for offset in range(4)), "little")


def permissions(flags, access):
    if not flags & 0x10:
        return 6
    allowed = [bool(flags & 2), flags & 6 == 6, bool(flags & 8)][access]
    if not allowed:
        return 7
    if not flags & 0x40:
        return 8
    if access == 1 and not flags & 0x80:
        return 9
    return 0


def decode(word, level, access):
    if not word & 1 or word & 6 == 4:
        return 2
    if word & 14 == 0:
        return 3 if word & 0xd0 else (0 if level else 4)
    return 5 if level else permissions(word & 255, access)


def translate(image, errors, va, root, access):
    path = []
    table = root << 12
    for level, shift in [(1, 22), (0, 12)]:
        address = table + ((va >> shift) & 1023)*4
        word = word_at(image, address)
        fault = 1 if address in errors else decode(word, level, access)
        path.append({"address": address, "word": word, "level": level, "fault": fault})
        if fault:
            return 0, fault, level, path
        table = (word >> 10) << 12
    return table | (va & 4095), 0, 0, path


class Cache:
    def __init__(self, capacity):
        require(capacity in [4, 8, 16], "unsupported capacity")
        self.capacity = capacity
        self.entries = [None] * capacity
        self.tree = 0

    def clear(self):
        self.entries = [None] * self.capacity
        self.tree = 0

    def node_regions(self):
        for node in range(self.capacity - 1):
            depth = (node + 1).bit_length() - 1
            size = self.capacity >> depth
            start = (node + 1 - (1 << depth)) * size
            yield node, start, size

    def touch(self, leaf):
        for node, start, size in self.node_regions():
            if start <= leaf < start + size:
                self.tree = (self.tree & ~(1 << node)) | ((leaf < start + size//2) << node)

    def victim(self):
        candidates = set(range(self.capacity))
        for node, start, size in self.node_regions():
            removed = start if self.tree & (1 << node) else start + size//2
            candidates.difference_update(range(removed, removed + size//2))
        require(len(candidates) == 1, "PLRU oracle did not select one leaf")
        return candidates.pop()


def analyze(path, image_path, capacity, variable=False, performance=False, export=None, empty=False):
    image = image_file(image_path)
    errors = set()
    cache = Cache(capacity)
    transactions = {}
    active = None
    pending = None
    presented = None
    response_waiting = None
    decode_waiting = None
    last_cycle = -1
    last_phase = -1
    last_time = -1
    last_epoch = 0
    run_id = None
    finish = None
    read_number = 0
    coverage = {}
    intervals = []
    totals = dict(accepted=0, completed=0, canceled=0, hits=0, misses=0, walks=0,
                  first_results=0, latency_sum=0, consumption_sum=0)
    events = [] if export else None
    fsm_state = 0
    busy_start = None
    busy_cycles = 0
    cycle_tree_before = 0
    cycle_valid_before = 0
    state_required = False
    refill_required = None
    last_kind = None
    stream = gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)
    with stream:
        for sequence, line in enumerate(stream):
            require(line.endswith("\n"), "truncated JSONL line")
            try:
                row = json.loads(line, object_pairs_hook=unique_object)
            except (ValueError, TypeError) as error:
                raise InvalidLog("malformed event: " + str(error)) from error
            require(isinstance(row, dict), "event is not an object")
            for key in ["schema", "seq", "cycle", "epoch", "txn", "time_ns"]:
                require(type(row.get(key)) is int and row[key] >= 0, "missing/invalid integer " + key)
            require(row["schema"] == 1 and row["seq"] == sequence, "schema or event sequence mismatch")
            require(finish is None, "event after finish")
            cycle, txn, kind = row["cycle"], row["txn"], row.get("event")
            require(isinstance(kind, str), "missing event name")
            phase = {"drive": 0, "sample": 1, "post": 2}.get(row.get("phase"))
            require(phase is not None and cycle >= last_cycle and row["time_ns"] >= last_time, "event time/order")
            expected_phase = "post" if kind in ["state", "fsm", "pte_request"] else "drive" if kind in ["image_write", "memory_error_clear", "memory_error_set", "scenario"] else "sample"
            require(row["phase"] == expected_phase, "event phase type")
            if cycle != last_cycle:
                require(not state_required, "missing observed post-edge state")
                last_phase = -1
                cycle_tree_before = cache.tree
                cycle_valid_before = sum((entry is not None) << i for i, entry in enumerate(cache.entries))
            require(phase >= last_phase, "same-cycle phase order")
            require(row["epoch"] >= last_epoch and row["epoch"] <= last_epoch+1, "epoch order")
            if row["epoch"] != last_epoch:
                require(kind == "reset", "epoch change without reset")
            require(isinstance(row.get("run"), str) and row["run"], "missing run id")
            if run_id is None:
                run_id = row["run"]
            require(row["run"] == run_id, "mixed runs")
            last_cycle, last_phase, last_time, last_epoch = cycle, phase, row["time_ns"], row["epoch"]
            if events is not None:
                events.append(row)
            if decode_waiting is not None:
                require(kind == "decode" and (txn, cycle) == (decode_waiting[0], decode_waiting[2]), "missing PTE decode event")
            if response_waiting is not None:
                require(kind == "discard" and (txn, cycle) == response_waiting, "missing discarded response event")
            if refill_required is not None:
                require(kind == "refill" and (txn, cycle) == refill_required, "missing successful refill event")

            if kind in ["reset", "flush"]:
                cache.clear()
                state_required = True
            elif kind == "cancel":
                require(active == txn, "orphan cancellation")
                tx = transactions[txn]
                require(not tx.get("terminal"), "duplicate terminal outcome")
                tx.update(terminal="canceled", cancel_cycle=cycle)
                totals["canceled"] += 1
                active = None
            elif kind == "offer_cancel":
                require(txn not in transactions and txn > 0, "offered cancellation already accepted")
                hexadecimal(row["va"], 32)
                hexadecimal(row["root"], 22)
                require(row["access"] in [0, 1, 2], "offered cancellation context")
            elif kind == "image_write":
                address, word = hexadecimal(row["addr"], 34), hexadecimal(row["data"], 32)
                for offset, byte in enumerate(word.to_bytes(4, "little")):
                    image[address + offset] = byte
            elif kind == "memory_error_clear":
                errors.clear()
            elif kind == "memory_error_set":
                errors.add(hexadecimal(row["addr"], 34))
            elif kind == "accept":
                require(active is None and txn not in transactions and txn > 0, "duplicate/overlapping translation")
                va, root = hexadecimal(row["va"], 32), hexadecimal(row["root"], 22)
                access = row["access"]
                require(type(access) is int and 0 <= access < 3, "invalid access")
                matches = [i for i, entry in enumerate(cache.entries) if entry and entry[0] == va >> 12]
                require(len(matches) <= 1, "reference duplicate mapping")
                hit = bool(matches)
                entry = matches[0] if hit else -1
                require(row["hit"] == int(hit) and row["entry"] == entry, "lookup result/entry")
                require(hexadecimal(row["match_vector"], capacity) == (1 << entry if hit else 0), "lookup match vector")
                if hit:
                    _, ppn, flags = cache.entries[entry]
                    fault = permissions(flags, access)
                    pa, level, path_steps = ((ppn << 12) | (va & 4095)) if not fault else 0, 0, []
                    cache.touch(entry)
                else:
                    pa, fault, level, path_steps = translate(image, errors, va, root, access)
                require(hexadecimal(row["expected_pa"], 34) == pa and row["expected_fault"] == fault and row["expected_reads"] == len(path_steps), "online/offline reference disagreement")
                transactions[txn] = dict(run=run_id, txn=txn, epoch=row["epoch"], va=f"{va:08x}", access=access,
                                         hit=hit, entry=entry, accept=cycle, pa=pa, fault=fault, level=level,
                                         path=path_steps, path_index=0, reads=[], refills=0, walks=0,
                                         ordinal=len(transactions))
                active = txn
                state_required = True
                totals["accepted"] += 1
                totals["hits" if hit else "misses"] += 1
            elif kind == "walk_start":
                require(active == txn and not transactions[txn]["hit"] and transactions[txn]["walks"] == 0, "walk start ownership")
                require(cycle == transactions[txn]["accept"], "walk start timing")
                transactions[txn]["walks"] += 1
                totals["walks"] += 1
            elif kind == "pte_request":
                require(active == txn and presented is None, "PTE presentation ownership")
                tx = transactions[txn]
                require(tx["path_index"] < len(tx["path"]), "extra PTE request")
                step = tx["path"][tx["path_index"]]
                require(hexadecimal(row["addr"], 34) == step["address"] and row["level"] == step["level"], "presented PTE path")
                require(hexadecimal(row["expected_addr"], 34) == step["address"], "presentation reference address")
                require(cycle == (tx["accept"] if tx["path_index"] == 0 else tx["last_pte_response"]), "PTE presentation timing")
                presented = (txn, step["address"], cycle)
            elif kind == "pte_withdraw":
                require(presented and presented[:2] == (txn, hexadecimal(row["addr"], 34)), "PTE withdrawal ownership")
                require(transactions[txn].get("terminal") == "canceled", "withdrawal without cancellation")
                presented = None
            elif kind == "pte_accept":
                require(active == txn and pending is None and presented is not None, "PTE acceptance ownership")
                address = hexadecimal(row["addr"], 34)
                require(presented[:2] == (txn, address), "PTE acceptance without matching presentation")
                require(cycle >= presented[2]+1, "PTE accepted before registered issue")
                tx = transactions[txn]
                step = tx["path"][tx["path_index"]]
                require(address == step["address"] == hexadecimal(row["expected_addr"], 34) and row["level"] == step["level"], "accepted PTE path")
                read_number += 1
                require(row["read"] == read_number, "read identifier uniqueness/order")
                pending = dict(txn=txn, address=address, cycle=cycle, read=read_number, step=step,
                               word=word_at(image, address), error=int(address in errors))
                presented = None
            elif kind == "pte_response":
                require(pending is not None and pending["txn"] == txn and pending["read"] == row["read"], "orphan/duplicate PTE response")
                require(hexadecimal(row["addr"], 34) == pending["address"] and row["level"] == pending["step"]["level"], "response address/level")
                require(hexadecimal(row["data"], 32) == pending["word"] == hexadecimal(row["expected_data"], 32) and row["error"] == pending["error"], "response data/error")
                elapsed = cycle-pending["cycle"]
                require(row["elapsed"] == elapsed and (1 <= elapsed <= 11 if variable else elapsed == 5), "memory latency")
                tx = transactions[txn]
                tx["reads"].append((pending["cycle"], cycle))
                if active == txn and not tx.get("terminal"):
                    decode_waiting = (txn, pending["step"], cycle)
                    tx["path_index"] += 1
                    tx["last_pte_response"] = cycle
                else:
                    response_waiting = (txn, cycle)
                pending = None
            elif kind == "discard":
                require(response_waiting == (txn, cycle) and transactions[txn].get("terminal") == "canceled", "discard accounting")
                response_waiting = None
            elif kind == "decode":
                require(decode_waiting is not None and decode_waiting[0] == txn and active == txn, "decode without active response")
                step = decode_waiting[1]
                require(row["level"] == step["level"] and row["fault"] == row["expected_fault"] == step["fault"], "decoded fault")
                transactions[txn]["decoded"] = (cycle, step)
                if step["level"] == 0 and step["fault"] == 0:
                    refill_required = (txn, cycle)
                decode_waiting = None
            elif kind == "refill":
                require(active == txn, "orphan refill")
                tx = transactions[txn]
                require(tx.get("decoded") == (cycle, tx["path"][-1]) and not tx["fault"] and not tx["refills"], "fault/duplicate/early refill")
                index = next((i for i, entry in enumerate(cache.entries) if entry is None), cache.victim())
                require(row["entry"] == row["expected_entry"] == index, "replacement/invalid-first victim")
                old = cache.entries[index]
                require(row["evict"] == int(old is not None), "eviction validity")
                if old:
                    require(hexadecimal(row["old_vpn"], 20) == old[0] and hexadecimal(row["old_ppn"], 22) == old[1], "eviction old mapping")
                vpn, ppn = int(tx["va"], 16) >> 12, tx["pa"] >> 12
                require(hexadecimal(row["vpn"], 20) == vpn and hexadecimal(row["ppn"], 22) == ppn and hexadecimal(row["plru_before"], capacity-1) == cache.tree, "refill mapping/tree")
                cache.entries[index] = (vpn, ppn, tx["path"][-1]["word"] & 255)
                cache.touch(index)
                tx["refills"] += 1
                refill_required = None
                state_required = True
            elif kind == "first_result":
                require(active == txn, "orphan first result")
                tx = transactions[txn]
                require("first" not in tx and hexadecimal(row["pa"], 34) == tx["pa"] == hexadecimal(row["expected_pa"], 34), "first result PA/uniqueness")
                require(row["fault"] == row["expected_fault"] == tx["fault"] and row["level"] == tx["level"], "first result fault/level")
                require(cycle == (tx["accept"] if tx["hit"] else tx.get("last_pte_response", -100)+1), "first result timing")
                require(tx["path_index"] == len(tx["path"]) and tx["refills"] == int(not tx["hit"] and not tx["fault"]), "complete walk/refill")
                require(row["latency"] == cycle-tx["accept"], "latency field")
                tx["first"] = cycle
                totals["first_results"] += 1
                totals["latency_sum"] += cycle-tx["accept"]
            elif kind == "consume":
                require(active == txn, "orphan/duplicate consumption")
                tx = transactions[txn]
                require("first" in tx and not tx.get("terminal"), "consumption order")
                require(row["latency"] == cycle-tx["accept"] and row["backpressure"] == cycle-tx["first"], "consumption timing")
                tx.update(consume=cycle, terminal="completed")
                totals["completed"] += 1
                totals["consumption_sum"] += cycle-tx["accept"]
                active = None
            elif kind == "state":
                require(state_required, "unexpected/duplicate state event")
                state_required = False
                if not (cycle == 0 and row["plru_before"] is None):
                    require(hexadecimal(row["plru_before"], capacity-1) == cycle_tree_before, "PLRU before-edge snapshot")
                require(hexadecimal(row["plru_after"], capacity-1) == cache.tree == hexadecimal(row["expected_plru"], capacity-1), "PLRU observed state")
                if not (cycle == 0 and row["valid_before"] is None):
                    require(hexadecimal(row["valid_before"], capacity) == cycle_valid_before, "valid before-edge snapshot")
                valid = sum((entry is not None) << i for i, entry in enumerate(cache.entries))
                require(hexadecimal(row["valid_after"], capacity) == valid == hexadecimal(row["expected_valid"], capacity), "observed validity snapshot")
            elif kind == "fsm":
                require(row["top"] in [0, 1, 2] and row["walker"] in [0, 1, 2, 3], "invalid controller state")
                new_state = row["walker"]
                if not fsm_state and new_state:
                    busy_start = cycle+1
                if fsm_state and not new_state:
                    require(busy_start is not None, "walker interval ownership")
                    busy_cycles += cycle+1-busy_start
                    busy_start = None
                fsm_state = new_state
            elif kind == "stall_interval":
                require(row["channel"] in range(4) and type(row["start"]) is int and row["start"] < row["end"] == cycle and row["length"] == row["end"]-row["start"], "invalid stall interval")
                intervals.append(row)
            elif kind == "coverage":
                key = (row["category"], row["bin"])
                require(key not in coverage and type(row["count"]) is int and row["count"] > 0, "coverage missing/duplicated/empty")
                coverage[key] = row["count"]
            elif kind == "entry_coverage":
                key = ("entry", row["entry"])
                require(key not in coverage and all(type(row[k]) is int and row[k] > 0 for k in ["fill", "hit", "victim"]), "entry coverage")
                coverage[key] = row
            elif kind == "finish":
                require(active is None and pending is None and presented is None and decode_waiting is None and response_waiting is None and refill_required is None and busy_start is None, "undrained run")
                require(all(tx.get("terminal") for tx in transactions.values()), "incomplete transaction")
                require(all(row.get(key) == value for key, value in totals.items()), "counter/log reconciliation")
                require(totals["accepted"] == totals["completed"]+totals["canceled"] and totals["hits"]+totals["misses"] == totals["accepted"] and totals["walks"] == totals["misses"], "transaction accounting")
                finish = row
            elif kind == "scenario":
                pass
            else:
                raise InvalidLog("unsupported/failure event: " + kind)
            last_kind = kind
    require(finish is not None and last_kind == "finish", "missing final completion")
    interval_totals = {channel: sum(e["length"] for e in intervals if e["channel"] == channel) for channel in range(4)}
    require(interval_totals[0] == finish["queue_cycles"] and interval_totals[3] == finish["stall_cycles"], "stall counter reconciliation")
    require(busy_cycles == finish["walker_busy_cycles"], "walker busy counter reconciliation")
    require(busy_cycles == sum(tx.get("consume", tx.get("cancel_cycle"))-tx["accept"] for tx in transactions.values() if not tx["hit"]), "independent walker occupancy")
    for txn, tx in transactions.items():
        stall_end = tx.get("first", tx.get("cancel_cycle"))
        require(stall_end is not None, "translation has no first/cancel boundary")
        tx_stalls = [e for e in intervals if e["txn"] == txn and e["channel"] == 3]
        require(sum(e["length"] for e in tx_stalls) == stall_end-tx["accept"], "per-transaction stall completeness")
        if stall_end > tx["accept"]:
            require(len(tx_stalls) == 1 and tx_stalls[0]["start"] == tx["accept"] and tx_stalls[0]["end"] == stall_end, "translation stall interval boundaries")
    if empty:
        require(totals["accepted"] == 0 and not performance and not variable, "empty-run exclusions")
    if not performance and not empty:
        mandatory = [("entry", i) for i in range(capacity)]
        mandatory += [(f"cancel_{control}", phase) for control in range(2) for phase in range(9)]
        mandatory += [("wrapper_state", i) for i in range(3)] + [("walker_state", i) for i in range(4)]
        mandatory += [("walker_transition", i) for i in [0, 1, 4, 5, 6, 8, 9, 10, 11, 12, 15]]
        mandatory += [("full_control", i) for i in [0, 1]]
        for level in [0, 1]:
            faults = [1, 2, 3, 5] if level else [1, 2, 3, 4, 6, 7, 8]
            mandatory += [("fault_access", level*30+fault*3+access) for fault in faults for access in range(3)]
        mandatory += [("fault_access", 9*3+1)]
        require(all(key in coverage for key in mandatory), "mandatory coverage bins missing")
    if performance:
        require(not variable and not totals["canceled"] and all(not tx["fault"] for tx in transactions.values()), "performance exclusions")
        require(totals["accepted"] == 8192 and totals["latency_sum"] == 13*totals["misses"] == interval_totals[3], "fixed-latency performance equality")
    groups = {}
    for label, selected in [("whole", list(transactions.values())),
                            ("cold", [tx for tx in transactions.values() if tx["ordinal"] < 1024]),
                            ("post_warmup", [tx for tx in transactions.values() if tx["ordinal"] >= 1024])]:
        done = [tx for tx in selected if tx.get("terminal") == "completed"]
        count = len(selected)
        hit_count = sum(tx["hit"] for tx in selected)
        first_sum = sum(tx["first"]-tx["accept"] for tx in done)
        groups[label] = dict(accepted=count, completed=len(done), hits=hit_count, misses=count-hit_count,
                             hit_rate=hit_count/count if count else None,
                             miss_rate=(count-hit_count)/count if count else None,
                             average_latency=first_sum/len(done) if done else None,
                             walks=sum(tx["walks"] for tx in selected), stall_cycles=first_sum)
    result = dict(schema=1, run=run_id, capacity=capacity, variable_latency=variable,
                  performance=performance, counters=totals, coverage_bins=len(coverage), groups=groups)
    if export:
        prefix = Path(export)
        prefix.with_suffix(".summary.json").write_text(json.dumps(result, indent=2) + "\n")
        with gzip.open(prefix.with_suffix(".events.csv.gz"), "wt", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["run", "seq", "cycle", "phase", "time_ns", "epoch", "txn", "event", "observed_details"])
            for row in events:
                writer.writerow([row[k] for k in ["run", "seq", "cycle", "phase", "time_ns", "epoch", "txn", "event"]] + [json.dumps({k:v for k,v in row.items() if k not in ["schema", "run", "seq", "cycle", "phase", "time_ns", "epoch", "txn", "event"]}, sort_keys=True)])
        with gzip.open(prefix.with_suffix(".listing.txt.gz"), "wt") as stream:
            for row in events:
                stream.write(f"{row['seq']:08d} cycle={row['cycle']:08d} {row['phase']:6s} epoch={row['epoch']} txn={row['txn']} {row['event']} " + json.dumps({k:v for k,v in row.items() if k not in ["schema", "run", "seq", "cycle", "phase", "time_ns", "epoch", "txn", "event"]}, sort_keys=True) + "\n")
        with prefix.with_suffix(".transactions.csv").open("w", newline="") as stream:
            fields = ["run", "txn", "epoch", "va", "access", "hit", "entry", "accept", "first", "consume", "cancel_cycle", "terminal", "pa", "fault", "level"]
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(transactions.values())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--entries", type=int, required=True)
    parser.add_argument("--variable", action="store_true")
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.log, args.image, args.entries, args.variable, args.performance, args.export), indent=2))
