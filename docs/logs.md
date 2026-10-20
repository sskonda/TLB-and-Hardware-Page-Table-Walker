# Observed transaction logs

`translation_N.jsonl` is the canonical event stream. It is emitted by the passive
monitor from actual request/response ports and internal cache/walker observations.
Expected values come from a separate byte-image translator and interval-based
PLRU model. `tools/analyze.py` independently replays the original image, stimulus
edits, cache contents, replacement, handshakes, faults, cancellation and metrics.
The launcher requires that validation before reporting PASS.

Every row has schema version 1, globally distinct run ID, contiguous event
sequence number, cycle, reset epoch, transaction cookie, event, phase and observed
simulation time in ns. Cookies remain unique across resets. Transaction 0 denotes
run-level events. Sequence numbers define ordering within an edge; timestamps in
ns are rounded, and the post-edge phase distinguishes the 1 ps register-settle
sample. Initial pre-reset register contents are represented by null, never an
invented reset value. Other unknown meaningful values fail checking.

| Event | Observed content and purpose |
| --- | --- |
| accept | Accepted VA, access, root PPN, actual hit/miss, entry and complete match vector; independent expected PA/fault/read count |
| walk_start | Actual accepted miss starts the walker, once per request |
| pte_request | First post-edge availability of level, physical byte address, cookie and expected address; includes requests later withdrawn |
| pte_accept | Memory handshake, unique read sequence, level, byte address and expected address |
| pte_response | Accepted returned word/error, read/level/address/cookie, expected word and actual elapsed cycles |
| decode | Actual and expected decoded fault/outcome at that level; NONE at L1 is a pointer, NONE at L0 is a successful leaf |
| refill | Actual/expected entry, eviction flag, old/new VPN and PPN, and old PLRU; no fault or canceled work may refill |
| state | Actual before/after valid mask and N-1-bit PLRU, plus independent expected after-state; checked after register updates |
| fsm | Actual wrapper/walker state changes for timing, replay and occupancy reconciliation |
| first_result | First sampled availability, actual PA/fault/level, expected PA/fault and first-result latency; occurs even if consumer not ready |
| consume | Response handshake, total latency and consumer delay from first result |
| reset/flush | Sampled controls, including both bits when simultaneous; reset has priority |
| cancel | Accepted unfinished transaction canceled, with whether a first result had already been observed |
| offer_cancel | Offered request withdrawn by control before acceptance; excluded from accepted-transaction metrics |
| pte_withdraw | Presented PTE request canceled before memory acceptance |
| discard | Known outstanding canceled memory response drained; orphan responses are failures |
| stall_interval | Closed half-open interval [start,end), channel and length; replaces repeated stall rows |
| image_write / memory_error_set / memory_error_clear | Explicit correctness-test stimulus edits, enabling independent replay; absent from performance traces |
| entry_coverage / coverage | Actual monitor counter reports at the quiescent end of directed/random testing |
| finish | Final drained accounting, observed sums and checker count; required last row |

Stall channels are 0 requester queueing, 1 memory-request backpressure,
2 response-consumer backpressure, and 3 accepted translation awaiting its first
result. Only channel 3 contributes to the defined translation stall metric.
Walker occupancy includes its RESULT state and is reported separately.

At an edge, control/cancellation precedes PTE withdrawal. New translation
acceptance is recorded before immediate hit results. An old memory response and
its decode/discard precede any new memory acceptance. Refill and translation
first-result/consumption records follow. After register updates, state/FSM changes
and new PTE presentations are recorded. The next PTE may therefore be presented
in the response edge's post phase, and accepted on the following edge. Coverage
and finish records are emitted from stored monitor counters while the driver is
quiescent; their actual time is included.

The validator rejects malformed/truncated JSONL, duplicate JSON keys/events/IDs,
mixed runs, unexpected X/Z, invalid widths/order/epochs, missing decode/refill/
discard/state records, absent coverage/completion, orphan responses and inconsistent
counters. Mutation tests use genuine successful logs and deliberately corrupt
these properties. A passing test name alone cannot establish coverage.

The deterministic projections are `translation_N.events.csv.gz` (all events and
details), `translation_N.listing.txt.gz` (chronological readable transaction
listing), `translation_N.transactions.csv` (one row per accepted transaction),
and `translation_N.summary.json`. Gzip is lossless standard-library compression;
the original observed values are preserved. The manifest records source revision,
working-tree state, source/input SHA-256, simulator/options, configuration, seeds,
commands and exits. Failed/injected runs are distinct from successful runs.

Performance metrics use acceptance-ordinal regions: first 1024, remaining 7168,
and whole 8192. Rates use eligible accepted lookups; average first-result latency
uses completed eligible lookups. A zero sample count produces null. A real
nonempty all-hit region has measured zero sampled latency, a different case.
Correctness runs report raw counts; faults, cancellation, backpressure and
variable latency are excluded from performance comparisons. See
[architecture.md](architecture.md) for the exact edge definitions and equations.
