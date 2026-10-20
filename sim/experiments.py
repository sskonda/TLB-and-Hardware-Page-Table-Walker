#!/usr/bin/env python3
"""Run the frozen performance matrix after a matching full correctness regression."""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_inputs import generate


def required_sources():
    files = [*ROOT.glob("rtl/*.sv"), *ROOT.glob("tb/*.sv")]
    files += [ROOT/path for path in ["sim/run.py", "sim/regress.py", "sim/compile.tcl", "sim/batch.do",
                                     "tools/analyze.py", "tools/make_inputs.py", "tests/check_logs.py"]]
    return files


def prerequisite(path):
    report = json.loads(Path(path).read_text())
    if report.get("passed") is not True or report.get("scope") != "full":
        raise ValueError("A passing full regression is required")
    for source in required_sources():
        relative = str(source.relative_to(ROOT))
        if report.get("source_sha256", {}).get(relative) != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError("Regression source differs: " + relative)
    required = {"plru", "tlb", "empty", "fixed_s1", "variable_s1", "fixed_s7", "variable_s7", "fixed_s42", "variable_s42",
                "parser_fixed_s1", "parser_variable_s1", "wall_timeout", "negative_compile", "invalid_capacity", "missing_design"}
    steps = report.get("steps", [])
    if not required <= {step["name"] for step in steps} or any((step["exit"] == 0) != step["expected_success"] for step in steps):
        raise ValueError("Incomplete or inconsistent regression report")
    return report


def cases():
    return ["sequential", "strided", "random_s1", "random_s7", "random_s42"] + [f"repeated_w{n}" for n in [2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 32]]


def comparison(candidate, baseline):
    return {"hit_delta_pp_vs4": 100*(candidate["hit_rate"]-baseline["hit_rate"]),
            "latency_reduction_pct_vs4": 100*(baseline["average_latency"]-candidate["average_latency"])/baseline["average_latency"] if baseline["average_latency"] else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regression", type=Path, required=True, help="Passing full regression.json")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true", help="Validate prerequisites and print the matrix without simulation")
    args = parser.parse_args()
    regression = prerequisite(args.regression)
    if args.plan:
        print(json.dumps({"status": "planned", "traces": cases(), "capacities": [4, 8, 16], "simulations": 48,
                          "requests_per_simulation": 8192, "regression_source": regression["source_commit"]}, indent=2))
        return 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (args.out or ROOT/"runs"/("experiments_"+stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    inputs = generate(out/"inputs")
    if inputs["traces"] != cases():
        raise ValueError("Trace generator differs from approved matrix")
    manifest = {"schema": 1, "source_commit": source_commit, "regression_source": regression["source_commit"],
                "regression_sha256": hashlib.sha256(args.regression.read_bytes()).hexdigest(),
                "inputs": inputs, "runs": [], "passed": False}
    rows = []
    try:
        for name in cases():
            prerequisite(args.regression)
            if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != source_commit:
                raise ValueError("Source revision changed during experiments")
            seed = int(name.split("_s")[1]) if name.startswith("random_s") else 1
            command = [sys.executable, str(ROOT/"sim/run.py"), "--suite", "translation", "--entries", "all",
                       "--inputs", str(out/"inputs"), "--trace", name, "--seed", str(seed), "--out", str(out/name)]
            if args.config: command += ["--config", str(args.config.resolve())]
            result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
            (out/(name+".txt")).write_text(result.stdout)
            manifest["runs"].append({"trace": name, "command": command, "exit": result.returncode})
            if result.returncode:
                raise RuntimeError(name+" failed\n"+result.stdout[-4000:])
            run_manifest = json.loads((out/name/"manifest.json").read_text())
            if not run_manifest["passed"] or run_manifest["source_commit"] != source_commit or run_manifest["inputs"] != inputs:
                raise ValueError("Run provenance differs: "+name)
            summaries = {n:json.loads((out/name/f"translation_{n}.summary.json").read_text()) for n in [4, 8, 16]}
            for n, summary in summaries.items():
                for region, metrics in summary["groups"].items():
                    baseline = summaries[4]["groups"][region]
                    rows.append({"trace":name, "trace_seed": seed if name.startswith("random_s") else "",
                                 "capacity":n, "region":region, **metrics, **comparison(metrics,baseline),
                                 "trace_sha256":inputs["sha256"][name+".trace"],
                                 "image_sha256":inputs["sha256"]["page_table.mem"], "source_commit":source_commit})
            (out/"experiments.json").write_text(json.dumps(manifest,indent=2)+"\n")
            print(name+" PASS (4/8/16)",flush=True)
        with (out/"metrics.csv").open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
        manifest["passed"]=True
        return 0
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:
        manifest["error"]=str(error);print(str(error),file=sys.stderr);return 1
    finally:
        (out/"experiments.json").write_text(json.dumps(manifest,indent=2)+"\n")
        print("Experiment records: "+str(out),flush=True)


if __name__=="__main__":
    sys.exit(main())
