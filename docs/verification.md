# Requirements to tests matrix

The accepted contracts are in [architecture.md](architecture.md), including
immediate combinational hits. **P** denotes an adopted choice; **R** a project or
proposal requirement. A row's presence is not test evidence. All applicable tests
run separately at 4, 8 and 16 entries; executed closure is recorded below.

| ID | Origin and requirement | Independent checks and coverage goal |
| --- | --- | --- |
| T01 | R configurable fully associative TLB | Compile/elaborate/run N=4/8/16 with no source edits; reject unsupported capacity before design simulation |
| T02 | R reset/empty | Empty miss, all valid bits cleared, tree zero, outputs known; reset both idle and busy |
| T03 | R actual multi-level walks | Independent byte-image decode predicts every L1/L0 PTE address/data and outcome; root and pointer must affect next read |
| T04 | R offsets and high bits | Non-identity mappings, offset 0/1/4095, adjacent pages, index 0/1023, 4 MiB boundary, VA/PPN upper-bit distinctions |
| T05 | R refill and hit | Cold L1 then L0, exactly one refill, next request hits without memory traffic; every entry including N-1 hit/refill |
| T06 | R invalid-first | Holes at every index, lowest invalid selected; full occupancy reached before first eviction; valid vector checked independently |
| T07 | R tree PLRU | Exhaust all 2^(N-1) states, every victim and N leaf updates, every resulting bit; reset zero, repeated hits, refill updates, no stalled updates |
| T08 | R duplicates | No duplicate valid VPNs after each event, full match vector one-hot-or-zero; hierarchy-only inject duplicate/multiple-match states and require checker detection |
| T09 | P invalid PTEs | At both levels V=0; W=1/R=0; non-leaf U/A/D separately and combined; terminal non-leaf; L1 leaf unsupported fault; no refill after any fault |
| T10 | P access permissions | Load/store/fetch, denied R/W/X, U=0, A=0, store D=0, successful allowed combinations on walks and cached hits; fault priority checked |
| T11 | P memory errors | Access-error on each level, fault level/address/context, no extra reads/refill; recover with a later successful request |
| T12 | R immediate hit and P miss timing | Hit=0, including same-edge acceptance/result/consumption; hit capture under backpressure; miss=2L+3 without stalls, no earlier miss result, exactly one first result |
| T13 | R held/gapped/consecutive traffic | Hold valid through not-ready, back-to-back eligible requests, random gaps; accepted context isolated from later input changes |
| T14 | R backpressure | Delay memory request acceptance and translation consumption for 1/2/7 cycles; stable payload/valid, no duplicate acceptance/refill/counting |
| T15 | R all-entry flush | Populate and hit every index (explicitly entries 8-15 at N=16), flush, require every mapping to miss afterwards; no fixed eight-bit mask |
| T16 | R mid-walk cancellation | Reset and flush separately in ISSUE before acceptance, WAIT at each level, pointer transition, final decode/refill edge, RESULT held/consuming; no stale refill/result |
| T17 | R late response/recovery | Keep real accepted read pending across cancellation; logged discard on return, unique cookie, correct next request even when stale response and new acceptance coincide |
| T18 | R repeated controls | Reset/flush pulses repeated, combined reset+flush priority, controls coincident with memory/response handshakes; recovery checked for each case |
| T19 | R seeded randomized tables/traffic | Seeds 1/7/42; independently generated sparse image and arbitrary offsets/high bits/accesses; compare translation and full PTE paths |
| T20 | R variable-latency stress | Separate seeded L=1..11 with request/response stalls and random controls; no performance mixing; scoreboard uses actual accepted timing |
| T21 | R invariant/unknown checks | Explicit X/Z rejection on meaningful ports/state; no orphan/duplicate response, held payload changes, duplicate refill, or counters; no dependence on DUT victim/path |
| T22 | R checker sensitivity | Deliberate wrong PA, wrong PTE path, wrong victim, missed flush high entry, stale result, unknown payload, missing coverage and unexpected stop must each fail with nonzero exit |
| T23 | R log completeness | Schema/order/uniqueness, each useful observed event and expected/actual result; interval closure, per-epoch canceled accounting and no orphan read responses |
| T24 | R parser sensitivity | Mutations: malformed row, truncated final event/line/run, duplicate ID/event, wrong ordering/hash/counter/value, orphan response and missing cancellation must be rejected |
| T25 | R controlled experiments | Hash generated trace/image once; identical bytes N=4/8/16; record root/clock/latency/policy/boundaries/seeds/source/tool/options |
| T26 | R metric reconciliation | Recompute A/H/M/walks/first/consume/stalls independently from observed events; A=C, H+M=A, walks=M only in eligible drained profile; null denominator case |
| T27 | R automation | Clean ordered build in spaced path, batch/seed/trace options, transcripts/WLF, focused GUI replay; inject compile/elab/runtime/coverage/timeout/unexpected-exit failures |
| T28 | R evidence | Real ModelSim captures for cold/refill, hit, PLRU eviction, faults, full flush, mid-walk reset/flush recovery and regression completion/counts; verify commit and logs against captures |

The implementation provides separate exhaustive PLRU and standalone TLB benches,
a procedural translation bench, and an offline byte-image/cache replay. The
normal full regression selects seeds 1/7/42 at all capacities in fixed and
variable-latency modes. Directed cancellation-phase and overlap cases explicitly
hold memory latency at five cycles so each requested phase is reachable;
randomized variable-latency traffic uses 1-11 cycles and is excluded from
performance. Random correctness traffic has 1000 requests per seed over
128 seeded non-identity mappings, with arbitrary offsets/accesses and consumer
delays. These are verification workloads, not the performance manifest.

Cached U/A faults are unreachable through normal refill because the walker
rejects those leaves. Cached access-denial and D-clear faults are exercised via
leaves that allow an initial load or fetch. Successful superpages, privilege
switching, ASIDs, virtualization and A/D writes are excluded by the architecture.

## Explicit coverage acceptance

Each directed coverage bin below must have a nonzero observed count at **each**
capacity. Counters are sampled by the passive monitor and reconciled with the
scoreboard; test-name execution alone does not close coverage. Stage completion
and coverage totals are exported, and missing mandatory bins fail the run.

- Entry bins: every slot allocated, hit, chosen as full-TLB victim, and cleared
  by reset and flush. At N=16, high entries must be occupied before the flush.
- PTE path bins: L1 and L0 requests accepted and responded; index endpoints;
  pointer traversal; every supported success/fault outcome at each legal level.
- Standalone PLRU: 8/128/32768 tree states respectively, each leaf update and
  victim. Totals: 32/1024/524288 state-leaf updates, plus 8/128/32768 victim
  checks. The oracle partitions leaf sets recursively. Verification-only force
  or deposit is released before clocked update checks; no functional test ports.
- Controller bins: every legal state and transition, including stalls,
  success/fault return, cancel from each state and discard/recovery. The final
  implementation publishes the exact legal transition list below.
- Conflict bins: all pairs among active memory response, translation response
  consumption, reset, and flush that are reachable; miss start with delayed
  stale response; held-valid attempts while busy. Explain unreachable pairs.
- Fault bins: every enumerated fault at every supported level and access kind;
  precedence combinations; cached permission-denial hit. Unsupported privilege
  modes, superpage success, ASIDs and virtualization are explicit exclusions.
- Random stress: seed-specific accepted/completed/canceled/fault totals, watchdog
  margin, observed latency min/max and high-bit/boundary bins. Random tests do
  not replace directed closure.

Every injected-failure run is recorded separately as an expected negative test;
it must fail its designated checker and exit nonzero. A failure elsewhere is
not adequate evidence of that checker's sensitivity. The positive suite must
also reject a missing final completion marker. Finite coverage and regressions
increase confidence but are not a correctness proof.

## Historical findings mapped to tests

These regression targets originate from upstream fixes and inspection, not a
claim of reproducing those defects locally. Review status and exact revisions
belong in the reference-review record.

| Reference finding | Required local regression |
| --- | --- |
| BSC fd7131d PLRU loop width/wrap | T07 exhaustive state/leaf behavior and watchdog at 4/8/16 |
| BSC 01cc68e invalid non-leaf U/A/D | T09 level-specific malformed pointer matrix |
| BSC c8554a9 PPN response slice | T04/T05 non-identity high-PPN and unchanged-offset checks |
| BSC 0f4727a eight-bit flush mask | T15 all entries populated, including 8-15, then misses for all |
| BSC b502b4f scripts later removed by 87237d0 | T27 clean maintained scripts and reproducible evidence; historical script presence is not verification evidence |
| CVA5 ee55226 tag match changes | T04/T08 high tags, full match vector, independent translation checks |
| CVA5 7d94630 flush timing | T15/T16/T18 coincident controls and refill/read/response edges |
| CVA5 01fde60 discarded-response corruption | T16/T17 canceled return cannot change current translation |
| CVA5 e72c948 second-level PTE validity | T09/T11 every L0 invalid/error form after valid L1 pointer |
| tlb-v dca03c2 PLRU inversion | T07 independently defined direction convention and all state/leaf combinations |
| tlb-v top-level bench limitations | T03-T24 independent monitor/oracles/protocol/fault/log checks, not waveform-only stimulus |

## Executed closure

The committed results and per-run coverage are in [the results record](results.md)
and [coverage.json](../results/coverage.json). Every one of the 18 translation
configurations passed its mandatory bins: 79/83/91 explicit bins at 4/8/16 entries,
including each entry's allocation, hit and victim observations. Standalone PLRU
separately exhausts every legal bit pattern and every leaf update.

Walker encoding is IDLE=0, ISSUE=1, WAIT_PTE=2, RESULT=3. Legal transition bins
are 0→0, 0→1, 1→0, 1→1, 1→2, 2→0, 2→1, 2→2, 2→3, 3→0 and 3→3.
The five remaining pairs are illegal and must have zero observations. Cancellation
permits the transitions to IDLE from every occupied state. The wrapper encoding
is IDLE=0, WALK=1, HOLD_HIT=2; its seven legal pairs are 0→0, 0→1, 0→2, 1→0,
1→1, 2→0 and 2→2. `tools/coverage_report.py` reconstructs those seven pairs and
self-transition intervals from the observed FSM stream and requires each.

Cancellation phases are: unaccepted L1 request, accepted L1 wait, L1 response
edge, unaccepted L0 request, accepted L0 wait, L0 response edge, held successful
walk result, held fault result, and held immediate-hit result. Both reset and
flush cover every phase at every capacity and seed/memory mode. Directed phase
placement uses five-cycle latency even in the separate variable-latency suite;
the seeded random traffic in that suite uses latencies 1–11. Otherwise a short
random return could make a requested phase unavailable.

Reachable conflicts include reset+flush, each control with a PTE return, each
control with an offered translation result, a discarded old return plus a new
PTE-read acceptance, consecutive accepted hits, held request offers while busy,
and cancellation of unaccepted offers. Controls suppress translation consumption
by contract. An active PTE response and consumption of that same walk's result
cannot handshake together: the result is registered for the next edge. A second
unrelated active translation is excluded by the one-active-request contract.
Those exclusions are architectural, not disabled checks.

Fault/access goals include memory error, invalid PTE and reserved non-leaf fields
at both levels for load/store/fetch; unsupported leaves at L1 for all accesses;
terminal pointer, U denial, access denial and A-clear at L0 for all accesses;
and D-clear at L0 for stores. D-clear alone is permitted for loads/fetches.
Permission faults on cached entries still count as hits. Full privilege/SUM/MXR,
successful superpages, live coherent PTE edits, same-read zero-cycle memory
returns, cookie reuse while a late response is possible, and unsupported capacity
values are outside the adopted functional contract. Unsupported capacities are
required to fail elaboration.
