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
PLRU tests do not use randomness. More suites will be added with the walker.

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
