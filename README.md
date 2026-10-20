# TLB and hardware page table walker

SystemVerilog study of a fully associative TLB and simplified two-level hardware
page table walker, comparing 4, 8, and 16 entries using tree pseudo-LRU.
ModelSim is the required simulator; Zybo Z7-20 validation is optional.

The RTL and procedural verification are implemented at all three capacities.
Hits respond combinationally; a two-level miss takes 13 sampled cycles with the
fixed five-cycle PTE responder. The explicitly adopted address/permission profile
is Sv32-derived, with documented exclusions. Proposal and course sources were
read before implementation and remain private.

The committed ModelSim matrix passed 27 positive simulations, all 32,904 PLRU
states and 525,344 state/leaf updates, 60 log-corruption tests, and 19 designated
negative tests. All 48 performance simulations passed independent log/counter
reconciliation, covering 393,216 translations. Complete observed logs, transcripts,
WLF, nine genuine GUI screenshots, measured figures and a four-page paper are
included. Finite regressions are not a correctness proof. Optional FPGA validation
and physical timing/area/power measurement were not performed.

```sh
python3 sim/regress.py
python3 sim/reproduce.py --out "runs/full reproduction" --screenshots
python3 tools/evidence.py --verify evidence
```

Add `--config /private/path/modelsim.json` to the simulation commands when tool
command/environment overrides are needed. The tested host uses ModelSim Intel
FPGA Starter 2020.1 on Linux with a private 32-bit runtime. ModelSim, Tcl and Python
are required; core verification uses only standard libraries. Publication plots
require Matplotlib. X11 capture additionally uses `xwininfo`, ImageMagick `import`
and Ghostscript. See [execution details](sim/README.md) for normal PATH setup,
spaced paths, failures and interactive replay.

- [Architecture and cycle/metric contracts](docs/architecture.md)
- [Requirements to tests and mandatory coverage](docs/verification.md)
- [Source review and review limitations](docs/source-review.md)
- [ModelSim usage](sim/README.md)
- [Observed logs and independent reconciliation](docs/logs.md)
- [Measured results and limitations](docs/results.md)
- [Genuine screenshot captions and focused replay](docs/evidence.md)
- [Course-style report](results/report.pdf)
- [Validation and provenance status](docs/status.md)

Correctness source: `a1d99ee2c83f29c0ef101bbe72a2f68f06361917`.
Experiment source: `11cec033b13e5b175b98a9b4dbb1744121f301e0`.
Core file hashes match; subsequent evidence/documentation commits are identified
separately. The CSV preserves all seeds, capacities, cold-prefix/post-prefix
regions, input hashes and four-entry baseline comparisons.

Research mirrors, tool probes, private course sources, and temporary working
material remain outside the repository. Generated simulation libraries and runs
belong in `build/` and `runs/`; required build scripts and curated evidence are
not covered by blanket ignore rules.
