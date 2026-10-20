# TLB and hardware page table walker

SystemVerilog study of a fully associative TLB and simplified two-level hardware
page table walker, comparing 4, 8, and 16 entries using tree pseudo-LRU.
ModelSim is the required simulator; Zybo Z7-20 validation is optional.

The architecture and experiment settings have been selected, including
combinational immediate-hit responses. Implementation is awaiting access to the
course guidelines, textbook, and lectures so their requirements can be reviewed
first. There is currently no translation RTL, regression result, measured
performance, or simulator screenshot in this repository.

- [Architecture and cycle/metric contracts](docs/architecture.md)
- [Requirements to tests and mandatory coverage](docs/verification.md)

Research mirrors, tool probes, private course sources, and temporary working
material remain outside the repository. Generated simulation libraries and runs
belong in `build/` and `runs/`; required build scripts and curated evidence are
not covered by blanket ignore rules.
