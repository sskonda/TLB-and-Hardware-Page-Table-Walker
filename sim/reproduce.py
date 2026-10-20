#!/usr/bin/env python3
"""Reproduce ModelSim regressions, frozen experiments, archives, plots and optional GUI captures."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--screenshots',action='store_true',help='Requires GUI display, xwininfo, ImageMagick import and Ghostscript')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    config=['--config',str(args.config.resolve())] if args.config else []
    records=[]
    def invoke(script,*arguments):
        command=[sys.executable,str(ROOT/script),*map(str,arguments)]
        result=subprocess.run(command,cwd=ROOT)
        records.append({'command':command,'exit':result.returncode})
        (out/'reproduction.json').write_text(json.dumps({'schema':1,'passed':False,'steps':records},indent=2)+'\n')
        if result.returncode: raise RuntimeError(script+' failed')
    invoke('sim/regress.py',*config,'--out',out/'regression')
    invoke('sim/experiments.py',*config,'--regression',out/'regression/regression.json','--out',out/'experiments')
    invoke('tests/check_evidence.py',out/'regression')
    invoke('tools/evidence.py','--regression',out/'regression','--experiments',out/'experiments','--out',out/'archive')
    invoke('tools/coverage_report.py',out/'archive/validation',out/'coverage.json')
    invoke('tools/plot_results.py',out/'archive/performance/metrics.csv',out/'plots')
    if args.screenshots:
        for name in ['cold','hit','eviction','fault','full_flush','mid_reset','mid_flush','completion']:
            invoke('sim/replay.py',out/'archive/validation/fixed_s1',*config,'--entries','16','--case',name,
                   '--export','--rasterize','--capture-x11','--out',out/'captures'/name)
    (out/'reproduction.json').write_text(json.dumps({'schema':1,'passed':True,'screenshots_requested':args.screenshots,'steps':records},indent=2)+'\n')
    print('REPRODUCTION_PASS '+str(out));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,OSError) as error:print(str(error),file=sys.stderr);sys.exit(1)
