# TLB and hardware page table walker

SystemVerilog study of a fully associative TLB and simplified two-level hardware
page table walker, comparing 4, 8, and 16 entries using tree pseudo-LRU.
ModelSim is the required simulator; Zybo Z7-20 validation is optional.

The architecture and experiment settings have been selected, including
combinational immediate-hit responses. Relevant proposal/course sources have
been reviewed. The PLRU, associative TLB, PTE walker, and immediate-hit wrapper
are implemented. Exhaustive standalone PLRU and incremental translation tests
are available. Full fault/protocol coverage, offline reconciliation, measured
performance, and simulator evidence are still in progress.

- [Architecture and cycle/metric contracts](docs/architecture.md)
- [Requirements to tests and mandatory coverage](docs/verification.md)
- [Source review and review limitations](docs/source-review.md)
- [ModelSim usage](sim/README.md)
- [Observed logs and independent reconciliation](docs/logs.md)

Research mirrors, tool probes, private course sources, and temporary working
material remain outside the repository. Generated simulation libraries and runs
belong in `build/` and `runs/`; required build scripts and curated evidence are
not covered by blanket ignore rules.
