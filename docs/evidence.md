# Genuine ModelSim evidence

Eight unaltered Wave-window PNG captures and one Transcript-window PNG were
captured directly from **ModelSim Intel FPGA Starter Edition 2020.1**, using X11
ImageMagick `import -window`. They are actual simulator GUI pixels. No screenshot
was fabricated, redrawn, cropped or annotated. Filenames and this index supply
labels. Each folder also preserves a distinct native ModelSim PostScript export
(`native.ps`) and Ghostscript-rendered copy (`native_rendered.png`); those exports
are not screenshots. Numbered `native_page_XX.png` files preserve every exported
page; `native_rendered.png` is a first-page preview. ModelSim's native print format
can paginate signal rows and elide short bus labels. GUI screenshots and logs
retain the corresponding values. All originals were visually inspected at native size.

All views replay the passing **fixed-latency directed/random N=16, seed=1** run
`20261020T044128702411Z_translation_16_s1`, tested source
`a1d99ee2c83f29c0ef101bbe72a2f68f06361917`. The matching complete
[event log](../evidence/validation/fixed_s1/translation_16.jsonl.gz),
[transaction table](../evidence/validation/fixed_s1/translation_16.transactions.csv),
[readable listing](../evidence/validation/fixed_s1/translation_16.listing.txt.gz),
[batch transcript](../evidence/validation/fixed_s1/translation_16.transcript),
[WLF](../evidence/validation/fixed_s1/translation_16.wlf.gz), and
[run manifest](../evidence/validation/fixed_s1/manifest.json) establish execution.
The [full regression report](../evidence/validation/regression.json) is separate
from the selected replay. Logs establish the checked behavior; pictures aid review.

The column of values follows the yellow cursor. Sample-handshake views place it
1 ps before the edge, post-state views 1 ps after; completion uses the final saved
time. The clock is 10 ns. Inactive external response payloads can be undefined
before their first valid return (visible red cookie trace in the cold view);
unknowns on valid payloads or checked controls fail the regression. The completion
zoom includes 1 ns beyond the saved endpoint for visibility; no simulation work
after the saved endpoint is implied. Primary IDs identify the focus; other visible
transactions are listed separately. Each linked `replay.json` records the exact
signal paths and displayed radices, source hashes and original command; `focus.do`
contains the executable view configuration.
The driver deliberately changes external request context after acceptance in
these correctness tests; the walker must continue using its latched VA/context.

To replay all captures from fresh simulations and regenerate observed logs:

```sh
python3 sim/reproduce.py --out "runs/evidence reproduction" --screenshots
```

Add `--config /private/path/modelsim.json` for local command overrides. To inspect
an existing view, use its replay command below; append `--capture-x11 --export
--rasterize` for fresh GUI pixels and native exports. Capture requires a working
X11 display, `xwininfo`, ImageMagick `import`, and Ghostscript. Normal ModelSim
interactive replay remains available without those capture utilities.

## Cold two-level walk and refill

Transaction 1 accepts VA 0x80000031 at 35 ns. L1 byte address 0x1800 accepts/returns at 45/95 ns (PTE 0x00000801); L0 address 0x2000 at 105/155 ns (PTE 0x80004cdf). Entry 0 refills at 155 ns. PA 0x200013031 first appears for sampling and is consumed at 165 ns: 13 cycles, offset 0x031 unchanged.

N=16, seed=1, fixed L=5; primary transaction IDs [1]; visible IDs [1, 2]. Window 20–185 ns; cursor 34.999 ns; anchor event sequence 7.

[Original screenshot](../results/screenshots/N16_s1_cold/screenshot_original.png), [native PS](../results/screenshots/N16_s1_cold/native.ps), [first export page](../results/screenshots/N16_s1_cold/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_cold/replay.transcript), [exact macro](../results/screenshots/N16_s1_cold/focus.do), [hashes/provenance](../results/screenshots/N16_s1_cold/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_cold/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case cold --out runs/replay_cold
```

## Immediate accepted and consumed hit

Transaction 3 is a store hit in entry 0: VA 0x80000001 → PA 0x200013001. Acceptance, first result and consumption all occur at 225 ns with zero sampled latency and no PTE reads. Neighboring hits demonstrate consecutive traffic.

N=16, seed=1, fixed L=5; primary transaction IDs [3]; visible IDs [2, 3, 4, 5]. Window 210–245 ns; cursor 224.999 ns; anchor event sequence 36.

[Original screenshot](../results/screenshots/N16_s1_hit/screenshot_original.png), [native PS](../results/screenshots/N16_s1_hit/native.ps), [first export page](../results/screenshots/N16_s1_hit/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_hit/replay.transcript), [exact macro](../results/screenshots/N16_s1_hit/focus.do), [hashes/provenance](../results/screenshots/N16_s1_hit/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_hit/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case hit --out runs/replay_hit
```

## Full TLB tree-PLRU eviction

With all sixteen entries occupied, transaction 29 refills at 3725 ns using PLRU victim 0. Old VPN/PPN 0x80000/0x200013 is replaced by 0x80010/0x2000a3. Tree bits update 0x0000 → 0x008b. PA 0x2000a3025 is consumed at 3735 ns. The independent log/oracle checks both victim and old/new mappings.

N=16, seed=1, fixed L=5; primary transaction IDs [29]; visible IDs [28, 29, 30]. Window 3590–3755 ns; cursor 3724.999 ns; anchor event sequence 560.

[Original screenshot](../results/screenshots/N16_s1_eviction/screenshot_original.png), [native PS](../results/screenshots/N16_s1_eviction/native.ps), [first export page](../results/screenshots/N16_s1_eviction/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_eviction/replay.transcript), [exact macro](../results/screenshots/N16_s1_eviction/focus.do), [hashes/provenance](../results/screenshots/N16_s1_eviction/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_eviction/native_page_01.png), [2](../results/screenshots/N16_s1_eviction/native_page_02.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case eviction --out runs/replay_eviction
```

## Final-level PTE fault

Transaction 124 reads the valid L1 pointer, then invalid final PTE 0x80004cde at 0x2000 (V=0). INVALID_PTE is returned at L0 with PA=0 at 14755 ns; no refill occurs. The full regression separately covers every supported fault/access combination at each legal level.

N=16, seed=1, fixed L=5; primary transaction IDs [124]; visible IDs [124, 125]. Window 14610–14775 ns; cursor 14754.999 ns; anchor event sequence 2349.

[Original screenshot](../results/screenshots/N16_s1_fault/screenshot_original.png), [native PS](../results/screenshots/N16_s1_fault/native.ps), [first export page](../results/screenshots/N16_s1_fault/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_fault/replay.transcript), [exact macro](../results/screenshots/N16_s1_fault/focus.do), [hashes/provenance](../results/screenshots/N16_s1_fault/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_fault/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case fault --out runs/replay_fault
```

## All populated entries cleared

At 6835 ns, the observed validity mask changes 0xffff → 0x0000 and PLRU 0x3f4f → 0x0000. All sixteen individual valid bits, including 8–15, are visibly set before the edge and clear afterward. Transaction 53 subsequently misses. This is a local full-capacity test, not a reproduced upstream run.

N=16, seed=1, fixed L=5; primary transaction IDs []; visible IDs [52, 53]. Window 6815–6870 ns; cursor 6835.001 ns; anchor event sequence 1056.

[Original screenshot](../results/screenshots/N16_s1_full_flush/screenshot_original.png), [native PS](../results/screenshots/N16_s1_full_flush/native.ps), [first export page](../results/screenshots/N16_s1_full_flush/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_full_flush/replay.transcript), [exact macro](../results/screenshots/N16_s1_full_flush/focus.do), [hashes/provenance](../results/screenshots/N16_s1_full_flush/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_full_flush/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case full_flush --out runs/replay_full_flush
```

## Mid-walk reset, late discard and recovery

Transaction 120 has an accepted L1 read, then reset cancels it at 14205 ns. Its late return at 14245 ns is discarded. Recovery transaction 121 walks and completes PA 0x200013023 at 14385 ns. Cookie and state traces distinguish the canceled and current work; no stale refill/result is accepted.

N=16, seed=1, fixed L=5; primary transaction IDs [120, 121]; visible IDs [119, 120, 121]. Window 14160–14400 ns; cursor 14204.999 ns; anchor event sequence 2261.

[Original screenshot](../results/screenshots/N16_s1_mid_reset/screenshot_original.png), [native PS](../results/screenshots/N16_s1_mid_reset/native.ps), [first export page](../results/screenshots/N16_s1_mid_reset/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_mid_reset/replay.transcript), [exact macro](../results/screenshots/N16_s1_mid_reset/focus.do), [hashes/provenance](../results/screenshots/N16_s1_mid_reset/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_mid_reset/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case mid_reset --out runs/replay_mid_reset
```

## Mid-walk flush, late discard and recovery

Transaction 122 has an accepted L1 read, then flush cancels it at 14425 ns. The late return at 14465 ns is discarded. Transaction 123 recovers with a new walk and PA 0x200013023 at 14605 ns. Reset/flush at other phases and return-edge conflicts are covered in the full logs.

N=16, seed=1, fixed L=5; primary transaction IDs [122, 123]; visible IDs [121, 122, 123]. Window 14380–14620 ns; cursor 14424.999 ns; anchor event sequence 2299.

[Original screenshot](../results/screenshots/N16_s1_mid_flush/screenshot_original.png), [native PS](../results/screenshots/N16_s1_mid_flush/native.ps), [first export page](../results/screenshots/N16_s1_mid_flush/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_mid_flush/replay.transcript), [exact macro](../results/screenshots/N16_s1_mid_flush/focus.do), [hashes/provenance](../results/screenshots/N16_s1_mid_flush/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_mid_flush/native_page_01.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case mid_flush --out runs/replay_mid_flush
```

## Completed checks and zero failures

The final saved state has completed=1 and failures=0. The separate genuine Transcript-window capture prints the saved TRANSLATION_PASS/RUN_COMPLETE lines verbatim and observed finish counts: 1317 accepted, 1294 completed, 23 canceled, 2,193,117 checks. It also identifies the saved full regression as passed with 31 steps and 19 expected failures. These are explicitly labeled saved-run records, not a new live execution of the full regression.

N=16, seed=1, fixed L=5; primary transaction IDs []; visible IDs [1319]. Window 161980–162011 ns; cursor 162010 ns; anchor event sequence 26501.

[Original screenshot](../results/screenshots/N16_s1_completion/screenshot_original.png), [native PS](../results/screenshots/N16_s1_completion/native.ps), [first export page](../results/screenshots/N16_s1_completion/native_rendered.png), [GUI transcript](../results/screenshots/N16_s1_completion/replay.transcript), [exact macro](../results/screenshots/N16_s1_completion/focus.do), [hashes/provenance](../results/screenshots/N16_s1_completion/replay.json).

Native export pages: [1](../results/screenshots/N16_s1_completion/native_page_01.png).

[Original Transcript-window screenshot](../results/screenshots/N16_s1_completion/transcript_screenshot_original.png).

```sh
python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case completion --out runs/replay_completion
```
