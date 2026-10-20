# Validation and provenance status

The simulation deliverables are complete. All supported capacities compile,
elaborate and pass the directed/random/coverage matrix in ModelSim. Performance
metrics reconcile with actual observed transactions and expected fixed walk
timing. Genuine GUI evidence, complete canonical logs and the course-style paper
are included. No execution/capture blocker remains for this simulation scope.

| Record | Executed scope | Source revision |
| --- | --- | --- |
| [Canonical full regression](../evidence/validation/regression.json) | 27 positive simulations, 60 rejected log mutations, 19 designated negative failures; 31 orchestration steps | a1d99ee2c83f29c0ef101bbe72a2f68f06361917 |
| [Canonical experiments](../evidence/performance/experiments.json) | 16 once-generated traces × 3 capacities × 8192 translations | 11cec033b13e5b175b98a9b4dbb1744121f301e0 |
| [Archive verification](../results/archive-validation.json) | 69 complete successful logs, 48 measured configurations, 144 metric rows, 1158 archived files | Same core hashes |
| [Clean full pipeline](../results/clean-pipeline.json) | New clean checkout and output paths containing spaces; complete regression/experiments/archive/coverage/plots/eight GUI replays; all 14 steps exit zero | 519062811f0ead885d63d970472e621d4576663e |
| [Supplemental duplicate injections](../results/supplemental/supplemental.json) | N=8 and N=16 both fail the intended multiple-match checker; N=4 is already in the canonical negatives | 519062811f0ead885d63d970472e621d4576663e |

All 144 clean-run measured rows equal the canonical rows, excluding their
different source-revision field; concrete input hashes are identical. Core RTL,
benches, generator, batch scripts and log-checker bytes match the committed
correctness/experiment sources. Subsequent commits add replay, review,
publication and evidence tools or documentation. They are not represented as
the original tested RTL revision. [validation.json](../results/validation.json)
records source/manifest hashes, publication-artifact hashes and the clean run's
original location. Its full original outputs remain at
`/home/sanat/tlb-work-private/complete clean reproduction`.

The canonical archive was added by commit `8a9a894` (“Add evidence”). Commit
`15c611d` preserves exact evidence bytes across Git checkouts and adds all pages
of the native waveform exports. Source/tool increments and normal pushes are
recorded on `main`; no history rewrite or force push was used. The final results
documentation follows those source/evidence commits.

## Reproduction on the tested host

```sh
python3 sim/regress.py --config /home/sanat/tlb-work-private/modelsim.json
python3 sim/reproduce.py --config /home/sanat/tlb-work-private/modelsim.json --out "runs/reproduction" --screenshots
python3 tools/evidence.py --verify evidence
```

The host uses ModelSim Intel FPGA Starter Edition 2020.1 with a private 32-bit
runtime, Python 3.14.6 and Tcl 8.6.15. The private config selects the compiler's
direct 32-bit loader; the existing ModelSim launcher runs simulations and GUI
replays. Compilation, elaboration, execution, intentional failure exits, WLF
and GUI export/capture were actually exercised. This record does not diagnose
or claim execution on the previously mentioned Windows installation.

On a normal PATH installation omit `--config`. The core harness/parsers have no
third-party Python dependencies. Publication plots/report use the separately
pinned [publication requirements](../requirements-report.txt). GUI capture uses
X11 `xwininfo` and ImageMagick `import`; Ghostscript renders native PS pages.
Interactive ModelSim replay is separate from X11 capture. Source line endings
and raw evidence bytes are protected by `.gitattributes`.

## Limits and exclusions

Zybo Z7-20 validation was optional and was not performed. No synthesis results,
physical timing/area/power, CPU CPI/IPC, real DRAM performance, CPU/OS integration,
video recording or course submission is claimed. The adopted Sv32-derived
profile and unsupported functional cases are explicit in the architecture/test
matrix. Public reference histories were fully inventoried across fetched refs
and merge parents; semantic review is selected, with its actual depth documented,
not exhaustive certification of the upstream projects. Upstream defects were
not locally reproduced. Finite regressions and coverage are not a proof.

Private proposal, guidelines, textbook and lecture files remain read-only and
unpublished. Their hashes and review scope are in the source-review record.
Research mirrors, tool probes, private runtime configuration and temporary
working material remain outside this repository. The unrelated locally supplied
proposal PDF is excluded only through the local Git exclude file.
