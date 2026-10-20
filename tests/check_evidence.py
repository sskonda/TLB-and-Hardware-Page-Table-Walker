#!/usr/bin/env python3
"""Check replay windows and observed coverage, including deliberately corrupted records."""
import copy
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'sim'),str(ROOT/'tools')]
from replay import selections
from coverage_report import inspect


def main():
    regression=Path(sys.argv[1]);checks=0
    for n in [4,8,16]:
        path=regression/'fixed_s1'/f'translation_{n}.jsonl'
        raw=path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.jsonl.gz').read_bytes())
        events=[json.loads(line) for line in raw.splitlines()]
        chosen=selections(events,n)
        if len(chosen)!=8: raise ValueError('Missing replay cases')
        for case,window in chosen.items():
            event=next(e for e in events if e['seq']==window['event_seq'])
            if not window['start_ns']<=event['time_ns']<=window['end_ns']:raise ValueError('Replay omits selected event '+case)
            checks+=1
        inspect(events,n);checks+=1
        mutations=[]
        illegal=copy.deepcopy(events)
        fsm=next(e for e in illegal if e['event']=='fsm');fsm['top']=3
        mutations.append(illegal)
        mutations.append([e for e in events if e['event']!='offer_cancel'])
        discard={e['cycle'] for e in events if e['event']=='discard'}
        mutations.append([e for e in events if not(e['event']=='pte_accept' and e['cycle'] in discard)])
        for mutation in mutations:
            try:inspect(mutation,n)
            except ValueError:checks+=1
            else:raise ValueError('Coverage mutation was accepted')
    print('EVIDENCE_CHECK_PASS checks='+str(checks));return 0


if __name__=='__main__':sys.exit(main())
