#!/usr/bin/env python3
"""Reconstruct controller/conflict coverage from observed events, not DUT counters."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path


def inspect(events, capacity):
    fsm = [e for e in events if e['event']=='fsm']
    transitions = Counter()
    for old,new in zip(fsm,fsm[1:]):
        gap=new['cycle']-old['cycle']
        if gap<1: raise ValueError('FSM event order')
        if gap>1: transitions[(old['top'],old['top'])]+=gap-1
        transitions[(old['top'],new['top'])]+=1
    legal={(0,0),(0,1),(0,2),(1,0),(1,1),(2,0),(2,2)}
    if set(transitions)!=legal or any(transitions[key]<1 for key in legal):
        raise ValueError('Wrapper transition closure')
    accepts={e['txn']:e for e in events if e['event']=='accept'}
    hits=[e['cycle'] for e in accepts.values() if e['hit']]
    discard_cycles={e['cycle'] for e in events if e['event']=='discard'}
    overlaps=[e for e in events if e['event']=='pte_accept' and e['cycle'] in discard_cycles]
    offers=[e for e in events if e['event']=='offer_cancel']
    state=[e for e in events if e['event']=='state']
    full_clears=[e['cycle'] for e in state if e['valid_before'] is not None and int(e['valid_before'],16)==(1<<capacity)-1 and int(e['valid_after'],16)==0]
    adjacent=sum(b==a+1 for a,b in zip(hits,hits[1:]))
    if len(overlaps)<2 or len(offers)<2 or not adjacent or not full_clears:
        raise ValueError('Observed conflict/full-clear coverage')
    return {'run':events[0]['run'],'capacity':capacity,
            'wrapper_transitions':{str(a)+'->'+str(b):transitions[(a,b)] for a,b in sorted(legal)},
            'discard_and_new_read_same_cycle':len(overlaps),'unaccepted_offer_cancellations':len(offers),
            'consecutive_accepted_hits':adjacent,'fully_populated_clear_cycles':full_clears,
            'explicit_bins':sum(e['event'] in ['coverage','entry_coverage'] for e in events)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('regression',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();reports=[]
    for folder in sorted(args.regression.glob('*_s*')):
        if not folder.is_dir(): continue
        for capacity in [4,8,16]:
            path=folder/f'translation_{capacity}.jsonl'
            raw=path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.jsonl.gz').read_bytes())
            reports.append(inspect([json.loads(line) for line in raw.splitlines()],capacity))
    if len(reports)!=18: raise ValueError('Expected 18 correctness configurations')
    args.out.write_text(json.dumps({'schema':1,'passed':True,'runs':reports},indent=2)+'\n')
    print('COVERAGE_PASS configurations='+str(len(reports)))


if __name__=='__main__':main()
