# ModelSim execution

Run from any directory with Python 3 and Tcl 8.5 or newer available:

```sh
python3 /path/to/project/sim/run.py --suite plru --entries all
```

`vlib`, `vlog`, `vsim`, and `tclsh` normally come from PATH. Each invocation uses
a new output directory, clean work library, ordered SystemVerilog compilation,
batch Tcl checks, per-capacity transcripts and WLF, and a JSON manifest containing
source commit, working-tree status, hashes, commands, and exits. `--out` selects
a new output path, including paths with spaces. Existing output directories are
rejected to prevent mixing runs. `--seed` selects the recorded seed; exhaustive
PLRU tests do not use randomness.

The translation suite builds all RTL and checks byte-image translations,
refill/hit/replacement, both-level malformed PTEs and faults, permission encodings,
boundary/high-bit addresses, backpressure, cancellation and seeded traffic:

```sh
python3 sim/run.py --suite translation --entries all
```

`--variable` selects separate variable-latency stress. `--inputs` accepts an
existing directory from `python3 tools/make_inputs.py /new/input/directory`.
Generated performance traces are frozen and hashed before replay. Select one
with `--trace sequential` only after a full correctness regression. Each
translation PASS includes independent offline log replay and reconciliation.

The complete regression runs all capacities, exhaustive PLRU, standalone TLB
allocation/flush, empty metrics, three seeds with fixed and variable latency,
parser mutation tests, actual DUT-output/state corruption, and tool/exit failures:

```sh
python3 sim/regress.py --config /private/path/modelsim.json
```

Omit `--config` for a normal PATH installation. `--negative-only` is a focused
debug option and does not close the full regression. The report explicitly
records its scope. The core harness and parsers use only Python/Tcl standard
libraries; no UVM, DPI, SVA, covergroups, class randomization or vendor IP is needed.
The [event schema](../docs/logs.md) documents the complete observed logs.

```sh
python3 sim/run.py --entries 4 --inject checker
python3 sim/run.py --entries 4 --inject coverage
python3 sim/run.py --entries 4 --inject timeout --watchdog 32
python3 sim/run.py --entries 4 --inject unexpected
```

All four negative commands must exit nonzero for their designated reason.
The batch script also rejects missing completion or nonzero checker counts.
`--timeout` is a wall-clock limit per subprocess. Compile/elaboration failures
are propagated. PASS requires both the bench sentinel and the final Tcl marker.

Use `--config /private/path/modelsim.json` for platform-specific command arrays
and environment overrides. Keep that file outside the repository. For example:

```json
{
  "programs": {
    "vlog": ["/path/to/32bit/loader", "/path/to/modelsim/linuxaloem/vlog"],
    "vsim": ["/path/to/modelsim-launcher"]
  },
  "env": {"LD_LIBRARY_PATH": "/path/to/private/32bit/libraries"}
}
```

This override retains ModelSim and does not change the simulator. On the current
Linux host the installed proot-based compiler wrapper truncates the smoke source
at its first semicolon; direct invocation through its private 32-bit loader
compiles correctly. The existing simulator launcher executes the result. No
vendor binary or system installation was modified. Version checks alone are
insufficient to establish execution support. Tool probes and their raw transcripts
are retained outside this repository.

Reproduce the complete matrix and lossless evidence archive with one command:

```sh
python3 sim/reproduce.py --out "runs/complete reproduction" --config /private/path/modelsim.json --screenshots
```

The optional `--screenshots` switch runs eight genuine ModelSim GUI WLF replays
and captures their Wave windows through X11. Completion also captures the
Transcript window; saved-run counts are explicitly labeled as saved evidence.
It requires `xwininfo`, ImageMagick `import`, a working display, and Ghostscript.
Native PostScript waveform exports and their rendered copies are distinct from
pixel screenshots. No image editing or synthetic simulator views are used.
Omit the switch on a batch-only host; screenshot reproduction is then excluded.
Publication plots additionally require Matplotlib; the core simulations and
archive/log verification use the Python standard library.

```sh
python3 tools/evidence.py --verify evidence
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --list
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case mid_flush
```

Replays accept archived gzip logs/WLF without modifying them. `--out` selects a
new replay directory. For a reproducible capture add `--capture-x11 --export
--rasterize`; for manual viewing the GUI remains open until closed. Exact signal
paths/radices, transaction IDs, time windows, original hashes, and source commit
are saved in `replay.json`. Config overrides apply to replay as well as batch.


Rebuild the four-page course-style paper after archive verification:

```sh
python3 -m pip install -r requirements-report.txt
python3 tools/build_report.py evidence results/plots runs/report.pdf
python3 tools/write_captions.py
```

Use a separate Python environment for publication dependencies if desired. The
recorded figures used Matplotlib 3.11.0 and ReportLab 5.0.1. Report building is
separate from core verification. `write_captions.py` first checks each original
capture hash and WLF/log provenance; it never edits the original PNG or PS.
The archive is about 324 MiB because it preserves every canonical observed log,
its CSV/readable projections, input sets, transcripts and waveform files. Failed
injection runs retain partial raw logs/WLF and are clearly labeled expected failures.
