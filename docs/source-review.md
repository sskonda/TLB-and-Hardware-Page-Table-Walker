# Source review

## Course material

The two-page project proposal was read and visually inspected. The complete text
and tables of `eel5764-project-guidelines-fall2026.docx` were read. The guidelines
permit a justified HDL prototype instead of gem5. The proposal specifies ModelSim,
so no simulator substitution or CPU integration is required. The guidelines also
call for an IEEE double-column final paper and a separate short video and course
discussion; no video recording or course submission is claimed here.

Relevant material reviewed in the supplied Hennessy and Patterson, *Computer
Architecture: A Quantitative Approach*, sixth edition: Section 2.4's protection
overview and Appendix B.4, especially the TLB tag/valid/permission comparisons,
physical-frame selection and unchanged page offset on pages B-44 through B-49.
These support the circuit decomposition, but do not set this project's exact
widths, encoding, timing, or memory latency. The solutions manual was not used.

The lecture archive was indexed by extracting searchable text from its PDFs.
Review focused on lectures 1-2's project milestones, 7-8's workload/aggregation
discussion, 13-14's controlled experiments, and lecture 15's scope and platform
guidance. General CPU performance claims are outside this standalone experiment.
The full textbook and every lecture were not read cover to cover. Source archives,
extractions, and private course documents are not redistributed in this repository.

| Private source | SHA-256 |
| --- | --- |
| Proposal PDF | a0825cd4549484338d6e598ee2348730df068ebe2eafab14b8c47bc29897f2e8 |
| Course guidelines DOCX | fc5012f92fb6485e1e39e687ebb719df2419d7f2a100600756a9168f772a3b55 |
| Lectures ZIP | 375559aacd8f2fb015add6a8f73b618222c4156b6e2ca94085e43af6e9e89ade |
| Textbooks ZIP | b150c56d9f40424e953dde35dc5d55d7b58d17e056027929435445f7e701845e |

## Public references and actual review depth

Full non-shallow mirrors were fetched outside the repository on 2026-10-20 UTC.
Counts below include every ref exposed by those mirrors, including fetched pull
heads and non-default branches. They are not counts of semantically reviewed
revisions. Historical path and merge-parent inventories were generated with
`git log --all --full-history -m`; that enumeration is separate from code review.

| Reference | Default tip | Refs | Reachable commits | Merge commits | License |
| --- | --- | ---: | ---: | ---: | --- |
| [BSC MMU](https://github.com/bsc-loca/mmu) | 0f4727a7ed57651f465f4eeeae509859693ad4dc | 2 | 70 | 2 | Solderpad Hardware License 2.1; Apache-2.0 option |
| [CVA5](https://github.com/openhwfoundation/cva5) | 2acf79fa87a94869eb8650c9b5805f14a7d3d9f8 | 20 | 921 | 41 | Apache-2.0 |
| [tlb-v](https://github.com/Naminar/tlb-v) | aa62aea79953fe15531ca5f74b7f255a600f2bb4 | 14 | 100 | 12 | MIT |
| [Stitt tutorial](https://github.com/ARC-Lab-UF/sv-tutorial) | 212f2850a9c848508132221a8b8b7d70a239337e | 14 | 382 | 21 | GPL-3.0 |

[reference-history.json](reference-history.json) records the complete reachable
graph, all fetched ref names/tips, and changed historical paths separately against
**each parent**, including roots and merge parents. Its 72/962/112 parent
comparisons cover BSC/CVA5/tlb-v respectively. The tutorial has 403 comparisons.
No mirror, source extraction, or probe is published here. Hidden/unadvertised
remote objects and unreachable commits are outside the meaning of reachable.

Semantic review is **selected**, not exhaustive review of every line in these
repositories. The ledger flags 17 BSC, 18 CVA5 and 3 tlb-v revisions where selected
patch/code semantics were inspected; a flag does not mean the entire commit was
reviewed. BSC review included current TLB lookup/invalidation and PLRU, the complete
common PLRU change history, PPN/invalid-PTE fixes, latch/default and integer-width
changes, A/D fault policy changes, and the historical simulator scripts. Deleted
benches and the large generated Chisel and hypervisor blocks were inspected by
inventory or selected excerpts, not fully reviewed or executed. CVA5 review
included its current walker/permission unit, changed-code excerpts through the
MMU/TLB candidate history, old-to-new TLB pipeline/refill paths, discarded-return
tracking, validity, and its byte-address to word-address memory-interface change.
Unrelated CPU/AXI implementation details were not exhaustively reviewed.
tlb-v review included the PLRU inversion patch, hit/miss pulse fix, current lookup
and insertion sections, the pipeline integration patch, and the complete current
top-level bench. Most earlier integration patches received subject/path triage,
not complete semantic review. No upstream defect has been locally reproduced.

An initial path filter found 60/69/60 candidate revisions. It was insufficient:
`adapter` matched a loose `pte` substring, while BSC's common `pseudoLRU` path
needed separate review. The final ledger therefore inventories **all** historical
paths without that filter. Renames include BSC's `src/rtl/`, `rtl/`, `hw/rtl/`
and return to `rtl/`, and CVA5's `core/mmu.sv` to `core/mmu/mmu.sv`.

The two BSC merge commits and all 41 CVA5 and 12 tlb-v merges are represented
against every parent; ancestry enumeration is not treated as semantic coverage.
Branch-only changes, deleted simulation infrastructure, and alternative interface
generations help identify failure modes but do not set this project's interface.
The review supports the local regression targets below; it certifies none of the
upstream implementations.

## Findings used to define regressions

- BSC [fd7131d](https://github.com/bsc-loca/mmu/commit/fd7131dc56fb28a0f3265e5bcd22b8fd29696e7f)
  replaces a narrow PLRU loop iterator with an integer iterator and explicit
  narrowing at the output. This motivates bounded combinational loops and
  exhaustive state/leaf checks, not a claim that our design has that defect.
- BSC [01cc68e](https://github.com/bsc-loca/mmu/commit/01cc68eb089616051dfb6284594ff5872bd9615b)
  adds invalid non-leaf U/A/D detection. BSC
  [c8554a9](https://github.com/bsc-loca/mmu/commit/c8554a9618c4b4c005201b328d197ac5eeea139c)
  changes the upper PPN response slice. Both motivate explicit malformed-pointer
  and high-PPN tests.
- At BSC tip `rtl/tlb/tlb.sv:253`, all-entry invalidation assigns `clear_mask =
  'hFF` while the mask is parameter-width and the default is eight entries.
  For a 16-bit mask, that value sets only the low eight bits. This is a static
  width finding, not a simulated upstream failure. Populate entries 8-15 before
  local all-entry flush tests. The current BSC PLRU register also declares
  `2*(ENTRIES-1)` bits; this project deliberately uses exactly N-1.
- BSC [b502b4f](https://github.com/bsc-loca/mmu/commit/b502b4fb7d3c1758d926fcbbaef19be735510eae)
  introduced simulation infrastructure later removed by
  [87237d0](https://github.com/bsc-loca/mmu/commit/87237d0a52fd4e4f8321db964f059445c3cc6cf0).
  Historical scripts use a working-directory assumption, warning suppression,
  and an ELF/DPI-oriented setup. They are not adopted as evidence or baseline
  verification infrastructure.
- CVA5 [ee55226](https://github.com/openhwfoundation/cva5/commit/ee55226240468ec44d57a702f2262f614f3b466c)
  changes tag width and superpage matching;
  [7d94630](https://github.com/openhwfoundation/cva5/commit/7d946306bdf689570be93c5d958e90af1e357f4d)
  uses the registered flush indication for written validity;
  [01fde60](https://github.com/openhwfoundation/cva5/commit/01fde601a0036535187f56c6a68c71996c07d216)
  prevents discarded data from updating the next walk address; and
  [e72c948](https://github.com/openhwfoundation/cva5/commit/e72c948cfa336579ae884123049b8a3df3db603f)
  adds final-level V and reserved R/W checks. Local tests target high tag bits,
  coincident control timing, canceled-response corruption, and both-level validity.
- tlb-v [dca03c2](https://github.com/Naminar/tlb-v/commit/dca03c2b4b127f9b2fdbe5a2ad53c2db116bc1a0)
  inverts PLRU branch decisions in its insertion macro. The current top-level
  bench supplies a clock and waveform dump, then finishes after a fixed delay;
  it has no translation scoreboard. It cannot establish local correctness.

These projects are useful primary code/history references, not normative
specifications or verification certificates. BSC includes much broader Sv39 and
virtualization behavior; CVA5 is an integrated CPU MMU; tlb-v uses set-associative
and multi-level TLB structures with fixed-way code. Their interfaces and features
do not define this original standalone implementation. No reference RTL has been
copied into the project. Preserve upstream notices if any code is later adopted.

CVA5's historical [registered-data lookup fix](https://github.com/openhwfoundation/cva5/commit/fc5fe7d291ec8dbbeddba7c2c60069d9513ad605) and [pipeline balancing](https://github.com/openhwfoundation/cva5/commit/2082e78c2f1b686860463c9620ef5173df393bc1) additionally motivate mutating external context after acceptance and
checking held results. Its [20a60b3 interface transition](https://github.com/openhwfoundation/cva5/commit/20a60b3c7981978a9ed366a57661f38008e31ffe) removes byte-offset bits
when changing to word addresses; this project instead fixes physical **byte**
address units and verifies every PTE address. BSC's latch and loop-width fixes
reinforce complete defaults and bounded integer loops. tlb-v's pipeline patch
includes internal timed stimulus and identity-derived incoming physical values;
those mechanisms are not a memory-backed walker or independent verification
model and are not adopted. These are design-review conclusions, not execution
measurements.

## Design and verification methodology

At the pinned Stitt revision, the combinational, sequential, FSM, FSMD, gotchas,
RAM and testbench README explanations were read. Code review included the full
combinational mux and priority encoder examples, race/reset-race examples,
gotchas RAM example, register/reset patterns, two-process Moore and FSMD
sections, and the register testbench's unknown-comparison discussion. This was
selected semantic review, not execution of the tutorial examples. Several examples
are intentionally flawed; RAM templates note Quartus Pro constraints. The project
uses complete combinational defaults, explicit widths and net types, clocked
nonblocking updates, and separate testbench responsibilities. Procedural checks
retain the intended verification without requiring SVA or advanced verification IP.

The [versioned RISC-V supervisor specification](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html)
was retrieved directly when the browser fetch failed. Its Sv32 geometry,
translation algorithm, permission bits, non-leaf reserved fields, and Svade A/D
behavior were read. The project adopts only the explicitly documented subset.
The background paper by Barr, Cox and Rixner,
[*Translation Caching: Skip, Don't Walk (the Page Table)*](https://cs.rice.edu/CS/Architecture/docs/barr-isca10.pdf),
was reviewed for its introduction and radix-walk explanation. Its partial
translation/walk-cache optimizations remain outside the baseline; its measured
results are not this project's results.
