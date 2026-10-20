# TLB and hardware page table walker

SystemVerilog implementation of a fully associative 4/8/16-entry TLB, tree
pseudo-LRU and a two-level memory-backed walker. Hits respond combinationally;
a miss takes 13 sampled cycles with the fixed five-cycle PTE responder. The
adopted Sv32-derived profile uses 32-bit VA, 34-bit PA and 4 KiB pages.

ModelSim regressions passed 27 positive simulations, 32,904 exhaustive PLRU states,
525,344 state/leaf updates, 60 rejected log mutations and 19 designated negative
tests. The 48 performance simulations cover 393,216 translations. Complete logs,
transcripts, WLF, nine genuine GUI screenshots, measured plots and the paper are
included. Finite regressions do not prove correctness. FPGA validation and
physical timing/area/power measurements were not performed.

## Run

Require Python 3, Tcl 8.5+ and ModelSim's `vlib`, `vlog`, `vsim` on PATH.
Core verification and log parsers use the standard libraries; no UVM, DPI, SVA,
covergroups, class randomization or vendor IP is required.

```sh
python3 sim/regress.py
python3 sim/reproduce.py --out "runs/full reproduction" --screenshots
python3 tools/evidence.py --verify evidence
```

The first command runs the full correctness/coverage/parser/failure matrix. The
second also generates identical hashed inputs, runs all experiments, verifies
the archive, reconstructs coverage, plots results and replays eight GUI views.
Omit `--screenshots` on a batch-only host. Plots require Matplotlib; X11 capture
requires `xwininfo`, ImageMagick `import` and Ghostscript. Publication dependencies
are pinned in [requirements-report.txt](requirements-report.txt).

Scripts work from any directory, including spaced paths; use an absolute script
path when outside the checkout. `--out` must name a new directory. Runs create
clean libraries and preserve source/input hashes, options, transcripts, WLF and
exits in manifests. Compilation, elaboration, checker, coverage, timeout and
unexpected-exit failures return nonzero. PASS requires all completion checks.

For focused runs or replay:

```sh
python3 sim/run.py --suite translation --entries all --seed 7 --variable
python3 sim/experiments.py --regression runs/REGRESSION/regression.json --out runs/experiments
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --list
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case mid_flush
```

`run.py --suite` selects `plru`, `tlb`, `translation` or `empty`; `--entries`
selects 4/8/16/all. `--variable` is correctness stress, excluded from performance.
`experiments.py` requires a full passing regression with matching core hashes.
`--inputs` and `--trace` select frozen input files for individual performance
replays. Every translation PASS includes independent observed-log validation.
Use each script's `--help` for options. Replay accepts compressed logs/WLF and
keeps originals unchanged; add `--capture-x11 --export --rasterize` to capture.

For command/environment overrides, add `--config /private/path/modelsim.json`
to simulation/reproduction/replay commands. Keep this file outside the checkout:

```json
{
  "programs": {"vlog": ["/path/to/32bit/loader", "/path/to/modelsim/linuxaloem/vlog"]},
  "env": {"LD_LIBRARY_PATH": "/path/to/private/32bit/libraries"}
}
```

The tested Linux host uses ModelSim Intel FPGA Starter 2020.1, Python 3.14.6 and
Tcl 8.6.15. Its compiler wrapper required a direct private 32-bit loader; the
existing simulator launcher handled batch and GUI execution. No vendor binary
was modified. On that host use `--config /home/sanat/tlb-work-private/modelsim.json`;
on a normal PATH installation omit it. Windows execution is not claimed.

To rebuild the four-page paper after verifying the archive:

```sh
python3 -m pip install -r requirements-report.txt
python3 tools/build_report.py evidence results/plots runs/report.pdf
```

## Files and results

| Location | Purpose |
| --- | --- |
| [rtl/](rtl/) | Synthesizable package, PLRU, TLB, walker and wrapper |
| [tb/](tb/), [tests/](tests/) | Independent procedural verification and parser mutations |
| [sim/](sim/), [tools/](tools/) | ModelSim automation, input generation, log validation and reporting |
| [Architecture](docs/architecture.md) | Adopted interfaces, faults, cancellation, timing and experiment contracts |
| [Verification](docs/verification.md) | Requirements-to-tests matrix and mandatory coverage |
| [Logs](docs/logs.md) | Observed event schema, ordering and independent reconciliation |
| [Source review](docs/source-review.md) | Course/public references, licenses, history and actual review depth |
| [Results](docs/results.md) | Measured tables, baseline comparisons, validation scope and limitations |
| [Evidence](docs/evidence.md) | Original screenshots, captions, provenance and focused replay |
| [Paper](results/report.pdf) | Four-page course-style report |

Correctness source: `a1d99ee2c83f29c0ef101bbe72a2f68f06361917`;
experiment source: `11cec033b13e5b175b98a9b4dbb1744121f301e0`.
Core file hashes match. [validation.json](results/validation.json) records the
clean reproduction and artifact hashes; later documentation/evidence revisions
are distinct from the tested RTL. Raw per-seed metrics are in
[metrics.csv](evidence/performance/metrics.csv).

Private course sources remain read-only and unpublished. Research mirrors,
probes and local tool configuration stay outside the repository. Generated
libraries and runs belong in ignored `build/` and `runs/`; curated evidence stays
tracked. The archive preserves complete observed logs and their readable/CSV
projections, input bytes, transcripts and waveforms, including labeled expected
failures.
