#!/usr/bin/env python3
"""One-command positive, coverage, parser, and failure-propagation regression."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--negative-only", action="store_true", help="Focused harness/checker tests; does not close the full regression")
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (args.out or ROOT / "runs" / ("regression_" + stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    config_args = ["--config", str(args.config.resolve())] if args.config else []
    config = json.loads(args.config.read_text()) if args.config else {}
    env = os.environ.copy()
    env.update(config.get("env", {}))
    programs = {tool: config.get("programs", {}).get(tool, [shutil.which(tool) or tool]) for tool in ["vlib", "vlog", "vsim"]}
    report = {"schema": 1, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for folder in ["rtl", "tb", "sim", "tools", "tests"] for p in sorted((ROOT/folder).glob("*")) if p.is_file()},
              "scope": "negative_only" if args.negative_only else "full",
              "steps": [], "passed": False}

    def invoke(name, command, expected_success=True, reason=None, cwd=ROOT):
        result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=300)
        (out / (name + ".txt")).write_text(result.stdout)
        record = {"name": name, "command": command, "exit": result.returncode,
                  "expected_success": expected_success, "reason": reason}
        report["steps"].append(record)
        if (result.returncode == 0) != expected_success or (reason and reason not in result.stdout):
            raise RuntimeError(name + " unexpected result\n" + result.stdout[-5000:])
        print(name + " PASS", flush=True)

    def suite(name, kind, extra=None, expected=True, reason=None):
        invoke(name, [sys.executable, str(ROOT / "sim/run.py"), "--suite", kind,
                      "--out", str(out / name), *config_args, *(extra or [])], expected, reason)

    try:
        if args.negative_only:
            suite("plru", "plru", ["--entries", "4"])
        else:
            for suite_name in ["plru", "tlb", "empty"]:
                suite(suite_name, suite_name)
            for capacity in [4, 8, 16]:
                empty = json.loads((out/"empty"/f"empty_{capacity}.summary.json").read_text())
                if any(empty["groups"]["whole"][field] is not None for field in ["hit_rate", "miss_rate", "average_latency"]):
                    raise RuntimeError("Zero-sample metrics must be null")
            for seed in [1, 7, 42]:
                for variable in [False, True]:
                    name = ("variable" if variable else "fixed") + "_s" + str(seed)
                    suite(name, "translation", ["--seed", str(seed), *(["--variable"] if variable else [])])
            for name, variable in [("fixed_s1", False), ("variable_s1", True)]:
                invoke("parser_" + name, [sys.executable, str(ROOT / "tests/check_logs.py"),
                       str(out/name/"translation_4.jsonl"), str(out/name/"inputs/page_table.mem"),
                       "--entries", "4", *(["--variable"] if variable else [])], reason="PARSER_PASS")
        failures = {"checker":"translation response", "path":"PTE presentation path", "victim":"refill victim",
                    "duplicate":"multiple lookup matches", "flush":"entry validity", "unknown":"known translation payload",
                    "cookie":"translation response", "coverage":"cancel coverage", "timeout":"TRANSLATION_WATCHDOG",
                    "unexpected":"RUN_INCOMPLETE_BREAK", "finishbad":"RUN_INCOMPLETE_BREAK"}
        for injection, reason in failures.items():
            suite("negative_"+injection, "translation", ["--entries", "16" if injection == "flush" else "4",
                  "--inject", injection, *(["--watchdog", "32"] if injection == "timeout" else [])], False, reason)
        for injection, reason in {"checker":"PLRU_CHECK_FAILED victim", "coverage":"PLRU_CHECK_FAILED coverage",
                                  "timeout":"PLRU_WATCHDOG", "unexpected":"RUN_INCOMPLETE_BREAK"}.items():
            suite("plru_negative_"+injection, "plru", ["--entries", "4", "--inject", injection,
                  *(["--watchdog", "32"] if injection == "timeout" else [])], False, reason)
        invoke("missing_design", programs["vsim"] + ["-c", "work.missing_expected_design", "-do", "quit -f -code 31"], False, "Error loading design", out/"plru")
        invoke("invalid_capacity", programs["vsim"] + ["-c", "-gENTRIES=3", "work.plru_tb", "-do", "quit -f -code 31"], False, "UNSUPPORTED_TLB_CAPACITY", out/"plru")
        with tempfile.TemporaryDirectory(prefix="tlb-compile-probe-") as temporary:
            folder = Path(temporary)
            (folder/"bad.sv").write_text("module deliberate_compile_failure; syntax error endmodule\n")
            invoke("negative_library", programs["vlib"]+["work"], cwd=folder)
            invoke("negative_compile", programs["vlog"]+["-sv", "bad.sv"], False, "** Error", folder)
        suite("wall_timeout", "empty", ["--entries", "4", "--timeout", "0.001"], False, "wall-clock timeout")
        report["passed"] = True
        return 0
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
        return 1
    finally:
        (out/"regression.json").write_text(json.dumps(report, indent=2)+"\n")
        print("Regression records: " + str(out), flush=True)


if __name__ == "__main__":
    sys.exit(main())
