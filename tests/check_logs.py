#!/usr/bin/env python3
"""Mutation tests against a genuine successful observed transaction log."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze import InvalidLog, analyze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--entries", type=int, required=True)
    parser.add_argument("--variable", action="store_true")
    args = parser.parse_args()
    analyze(args.log, args.image, args.entries, args.variable)
    original = args.log.read_text()
    rows = [json.loads(line) for line in original.splitlines()]
    mutations = {}

    def changed(name, event, key, value):
        data = copy.deepcopy(rows)
        target = next(row for row in data if row["event"] == event)
        target[key] = value(target[key]) if callable(value) else value
        mutations[name] = data

    changed("wrong_pa", "first_result", "pa", "000000001")
    changed("wrong_expected_pa", "accept", "expected_pa", "000000001")
    changed("wrong_path", "pte_accept", "addr", "000001804")
    changed("unknown_data", "pte_response", "data", "xxxxxxxx")
    changed("orphan_memory", "pte_response", "txn", 0xffffffff)
    changed("bad_counter", "finish", "hits", lambda n:n+1)
    changed("bad_latency", "first_result", "latency", lambda n:n+1)
    changed("bad_interval", "stall_interval", "length", lambda n:n+1)
    changed("bad_epoch", "pte_accept", "epoch", lambda n:n+2)
    changed("mixed_run", "pte_accept", "run", "different_run")
    changed("float_cycle", "pte_accept", "cycle", 1.5)
    changed("wrong_phase", "state", "phase", "sample")
    changed("empty_coverage", "coverage", "count", 0)
    changed("wrong_tree", "state", "plru_after", "1")
    changed("wrong_validity", "state", "valid_after", "1")
    mutations["missing_finish"] = rows[:-1]
    for event in ["cancel", "decode", "pte_response", "walk_start", "coverage", "state", "refill", "discard"]:
        data = copy.deepcopy(rows)
        del data[next(i for i, row in enumerate(data) if row["event"] == event)]
        for i, row in enumerate(data): row["seq"] = i
        mutations["missing_" + event] = data
    data = copy.deepcopy(rows)
    index = next(i for i, row in enumerate(data) if row["event"] == "accept")
    data.insert(index+1, copy.deepcopy(data[index]))
    for i, row in enumerate(data): row["seq"] = i
    mutations["duplicate_transaction"] = data
    data = copy.deepcopy(rows)
    index = next(i for i, row in enumerate(data) if row["event"] == "pte_accept")
    data[index], data[index+1] = data[index+1], data[index]
    for i, row in enumerate(data): row["seq"] = i
    mutations["reordered_events"] = data
    with tempfile.TemporaryDirectory(prefix="tlb-parser-") as directory:
        target = Path(directory) / "mutated.jsonl"
        raw_mutations = {name: "".join(json.dumps(row)+"\n" for row in data) for name, data in mutations.items()}
        raw_mutations["malformed_json"] = "{\n" + original.split("\n", 1)[1]
        raw_mutations["truncated_line"] = original[:-1]
        raw_mutations["duplicate_json_key"] = original.replace('"schema":1', '"schema":1,"schema":1', 1)
        raw_mutations["duplicate_event"] = original.splitlines(keepends=True)[0] + original
        for name, text in raw_mutations.items():
            target.write_text(text)
            try:
                analyze(target, args.image, args.entries, args.variable)
            except InvalidLog:
                continue
            raise AssertionError("Parser accepted mutation: " + name)
    print(f"PARSER_PASS positive=1 rejected={len(raw_mutations)}")


if __name__ == "__main__":
    main()
