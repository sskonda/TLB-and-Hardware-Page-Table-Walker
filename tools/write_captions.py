#!/usr/bin/env python3
"""Index unaltered ModelSim captures against their actual WLF/log provenance."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.root.resolve()
    log=root/'evidence/validation/fixed_s1/translation_16.jsonl.gz'
    raw=gzip.decompress(log.read_bytes());events=[json.loads(line) for line in raw.splitlines()]
    wlf=gzip.decompress((log.parent/'translation_16.wlf.gz').read_bytes())
    text='''# Genuine ModelSim evidence

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
transactions are listed separately.
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

'''
    notes={
      'cold':'Transaction 1 accepts VA 0x80000031 at 35 ns. L1 byte address 0x1800 accepts/returns at 45/95 ns (PTE 0x00000801); L0 address 0x2000 at 105/155 ns (PTE 0x80004cdf). Entry 0 refills at 155 ns. PA 0x200013031 first appears for sampling and is consumed at 165 ns: 13 cycles, offset 0x031 unchanged.',
      'hit':'Transaction 3 is a store hit in entry 0: VA 0x80000001 → PA 0x200013001. Acceptance, first result and consumption all occur at 225 ns with zero sampled latency and no PTE reads. Neighboring hits demonstrate consecutive traffic.',
      'eviction':'With all sixteen entries occupied, transaction 29 refills at 3725 ns using PLRU victim 0. Old VPN/PPN 0x80000/0x200013 is replaced by 0x80010/0x2000a3. Tree bits update 0x0000 → 0x008b. PA 0x2000a3025 is consumed at 3735 ns. The independent log/oracle checks both victim and old/new mappings.',
      'fault':'Transaction 124 reads the valid L1 pointer, then invalid final PTE 0x80004cde at 0x2000 (V=0). INVALID_PTE is returned at L0 with PA=0 at 14755 ns; no refill occurs. The full regression separately covers every supported fault/access combination at each legal level.',
      'full_flush':'At 6835 ns, the observed validity mask changes 0xffff → 0x0000 and PLRU 0x3f4f → 0x0000. All sixteen individual valid bits, including 8–15, are visibly set before the edge and clear afterward. Transaction 53 subsequently misses. This is a local full-capacity test, not a reproduced upstream run.',
      'mid_reset':'Transaction 120 has an accepted L1 read, then reset cancels it at 14205 ns. Its late return at 14245 ns is discarded. Recovery transaction 121 walks and completes PA 0x200013023 at 14385 ns. Cookie and state traces distinguish the canceled and current work; no stale refill/result is accepted.',
      'mid_flush':'Transaction 122 has an accepted L1 read, then flush cancels it at 14425 ns. The late return at 14465 ns is discarded. Transaction 123 recovers with a new walk and PA 0x200013023 at 14605 ns. Reset/flush at other phases and return-edge conflicts are covered in the full logs.',
      'completion':'The final saved state has completed=1 and failures=0. The separate genuine Transcript-window capture prints the saved TRANSLATION_PASS/RUN_COMPLETE lines verbatim and observed finish counts: 1317 accepted, 1294 completed, 23 canceled, 2,193,117 checks. It also identifies the saved full regression as passed with 31 steps and 19 expected failures. These are explicitly labeled saved-run records, not a new live execution of the full regression.'}
    index=[]
    for case in ['cold','hit','eviction','fault','full_flush','mid_reset','mid_flush','completion']:
        directory=root/'results/screenshots'/('N16_s1_'+case)
        record=json.loads((directory/'replay.json').read_text())
        if record['source_log_sha256']!=hashlib.sha256(raw).hexdigest() or record['source_wlf_sha256']!=hashlib.sha256(wlf).hexdigest() or record['screenshot_status']!='captured':
            raise ValueError('Capture provenance mismatch '+case)
        for name,expected in record['sha256'].items():
            if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('Changed original '+case+'/'+name)
        visible=sorted({e['txn'] for e in events if e['txn'] and record['start_ns']<=e['time_ns']<=record['end_ns'] and e['event'] not in ['state','fsm']})
        relative='../results/screenshots/'+directory.name+'/'
        command='python3 sim/replay.py evidence/validation/fixed_s1 --entries 16 --case '+case+' --out runs/replay_'+case
        text+='## '+record['title']+'\n\n'+notes[case]+'\n\n'
        text+=f"N=16, seed=1, fixed L=5; primary transaction IDs {record['transactions']}; visible IDs {visible}. "
        text+=f"Window {record['start_ns']}–{record['end_ns']} ns; cursor {record['cursor_ns']} ns; anchor event sequence {record['event_seq']}.\n\n"
        text+=f"[Original screenshot]({relative}screenshot_original.png), [native PS]({relative}native.ps), [rendered export]({relative}native_rendered.png), [GUI transcript]({relative}replay.transcript), [exact macro]({relative}focus.do), [hashes/provenance]({relative}replay.json).\n\n"
        pages=sorted(directory.glob('native_page_*.png'))
        if pages:text+='Native export pages: '+', '.join('['+str(i+1)+']('+relative+page.name+')' for i,page in enumerate(pages))+'.\n\n'
        if case=='completion':text+=f"[Original Transcript-window screenshot]({relative}transcript_screenshot_original.png).\n\n"
        text+='```sh\n'+command+'\n```\n\n'
        text+='<details><summary>Exact signal paths and displayed radices</summary>\n\n| Signal | Radix |\n| --- | --- |\n'
        for path,radix in record['signal_radices']:text+='| `'+path+'` | '+radix+' |\n'
        text+='\n</details>\n\n'
        index.append({'case':case,'visible_transactions':visible,'primary_transactions':record['transactions'],'replay':command,
                      'start_ns':record['start_ns'],'end_ns':record['end_ns'],'cursor_ns':record['cursor_ns'],
                      'source_commit':record['source_commit'],'original_png_sha256':record['sha256']['screenshot_original.png']})
    (root/'docs/evidence.md').write_text(text)
    (root/'results/caption-index.json').write_text(json.dumps({'schema':1,'captures':index},indent=2)+'\n')
    print('CAPTIONS_PASS captures='+str(len(index)));return 0


if __name__=='__main__':main()
