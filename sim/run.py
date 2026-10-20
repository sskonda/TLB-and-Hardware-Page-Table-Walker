#!/usr/bin/env python3
"""Build and run ModelSim suites using only Python and Tcl standard libraries."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def tcl_list(items):
    escape = str.maketrans({"\\": "\\\\", '"': '\\"', "$": "\\$", "[": "\\[", "]": "\\]",
                           "\n": "\\n", "\r": "\\r"})
    return " ".join('"' + str(item).translate(escape) + '"' for item in items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["plru"], default="plru")
    parser.add_argument("--entries", choices=["4", "8", "16", "all"], default="all")
    parser.add_argument("--config", type=Path, help="Private JSON tool command/env overrides")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--inject", choices=["checker", "coverage", "timeout", "unexpected"])
    parser.add_argument("--watchdog", type=int)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config else {}
    env = os.environ.copy()
    env.update(config.get("env", {}))
    programs = {name: config.get("programs", {}).get(name, [shutil.which(name) or name])
                for name in ["vlib", "vlog", "vsim", "tclsh"]}
    for name, command in programs.items():
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            raise ValueError("Invalid command list for " + name)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (args.out or ROOT / "runs" / stamp).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_files = sorted([*ROOT.glob("rtl/*.sv"), *ROOT.glob("tb/*.sv"), *ROOT.glob("sim/*")])
    manifest = {"schema": 1, "suite": args.suite, "entries": args.entries, "seed": args.seed,
                "injection": args.inject, "started_utc": stamp, "programs": programs,
                "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "working_tree": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
                "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in source_files if p.is_file()}, "steps": [], "passed": False}

    def run(name, command, directory, extra=None):
        child_env = env.copy()
        child_env.update(extra or {})
        record = {"name": name, "command": command, "cwd": str(directory)}
        manifest["steps"].append(record)
        try:
            result = subprocess.run(command, cwd=directory, env=child_env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, timeout=args.timeout)
            record["exit"] = result.returncode
            (out / (name + ".txt")).write_text(result.stdout)
            if result.returncode:
                raise RuntimeError(name + " failed, exit " + str(result.returncode) + "\n" + result.stdout[-4000:])
            return result.stdout
        except subprocess.TimeoutExpired as error:
            record["timeout"] = True
            (out / (name + ".txt")).write_bytes(error.stdout or b"")
            raise RuntimeError(name + " wall-clock timeout") from error
        finally:
            (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    try:
        run("version", programs["vsim"] + ["-version"], out)
        run("compile", programs["tclsh"] + [str(ROOT / "sim/compile.tcl")], out,
            {"VM_VLIB": tcl_list(programs["vlib"]), "VM_VLOG": tcl_list(programs["vlog"])})
        for capacity in ([4, 8, 16] if args.entries == "all" else [int(args.entries)]):
            name = args.suite + "_" + str(capacity)
            command = programs["vsim"] + ["-c", "-onfinish", "stop", "-voptargs=+acc",
                       "-l", str(out / (name + ".transcript")), "-wlf", str(out / (name + ".wlf")),
                       "-gENTRIES=" + str(capacity), "work.plru_tb", "+SEED=" + str(args.seed)]
            if args.inject: command += ["+INJECT=" + args.inject]
            if args.watchdog: command += ["+WATCHDOG=" + str(args.watchdog)]
            command += ["-do", "do " + tcl_list([ROOT / "sim/batch.do"])]
            output = run(name, command, out, {"VM_TOP": "plru_tb"})
            if "PLRU_PASS" not in output or "RUN_COMPLETE" not in output:
                raise RuntimeError(name + " missing completion sentinel")
            print(name + " PASS", flush=True)
        manifest["passed"] = True
        return 0
    except (RuntimeError, OSError) as error:
        manifest["error"] = str(error)
        print(str(error), file=sys.stderr)
        return 1
    finally:
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print("Run records: " + str(out), flush=True)


if __name__ == "__main__":
    sys.exit(main())
