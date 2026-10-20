#!/usr/bin/env python3
"""Archive observed runs and verify logs, measurements and original capture provenance."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def copy_records(source, target):
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source)
        if not path.is_file() or 'work' in relative.parts or path.name in ['modelsim.ini','transcript']:
            continue
        if path.suffix not in ['.json','.jsonl','.csv','.gz','.txt','.transcript','.trace','.mem','.wlf']:
            continue
        destination = target/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        if path.suffix in ['.jsonl','.wlf']:
            destination = destination.with_suffix(destination.suffix+'.gz')
            destination.write_bytes(gzip.compress(path.read_bytes(),compresslevel=9,mtime=0))
        else:
            shutil.copyfile(path,destination)


def verify(folder):
    from analyze import analyze
    record = json.loads((folder/'evidence.json').read_text())
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name!='evidence.json'}
    if actual != set(record['sha256']):
        raise ValueError('Archive file set differs')
    for name, expected in record['sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or digest((folder/name).read_bytes()) != expected:
            raise ValueError('Archive hash mismatch: '+name)
    regression = json.loads((folder/'validation/regression.json').read_text())
    experiments = json.loads((folder/'performance/experiments.json').read_text())
    if regression.get('passed') is not True or regression.get('scope')!='full' or experiments.get('passed') is not True:
        raise ValueError('Missing successful full regression/experiments')
    if len(experiments['runs']) != 16 or len(regression['steps']) != 31:
        raise ValueError('Unexpected validation matrix')
    summaries = {}
    accepted = completed = canceled = checks = log_count = 0
    with tempfile.TemporaryDirectory(prefix='tlb-evidence-verify-') as temporary:
        for manifest_path in sorted(folder.rglob('manifest.json')):
            manifest = json.loads(manifest_path.read_text())
            if not manifest.get('passed') or manifest.get('suite') not in ['translation','empty']:
                continue
            directory = manifest_path.parent
            is_performance = 'performance' in manifest_path.relative_to(folder).parts
            image_directory = folder/'performance/inputs' if is_performance else directory/'inputs'
            for name, expected in manifest['inputs']['sha256'].items():
                if Path(name).name!=name or digest((image_directory/name).read_bytes())!=expected:
                    raise ValueError('Input mismatch '+name)
            for log in sorted(directory.glob('*.jsonl.gz')):
                capacity = int(log.name.split('_')[1].split('.')[0])
                decoded = Path(temporary)/log.name[:-3]
                decoded.write_bytes(gzip.decompress(log.read_bytes()))
                result = analyze(decoded,image_directory/'page_table.mem',capacity,
                                 manifest.get('variable_latency',False),is_performance,empty=manifest['suite']=='empty')
                saved = json.loads((directory/(log.name[:-9]+'.summary.json')).read_text())
                if result != saved:
                    raise ValueError('Recomputed summary differs '+str(log))
                log_count += 1
                if is_performance:
                    summaries[(directory.name,capacity)] = result
                else:
                    accepted += result['counters']['accepted'];completed += result['counters']['completed']
                    canceled += result['counters']['canceled']
                    checks += json.loads(decoded.read_text().splitlines()[-1])['checks']
    rows=list(csv.DictReader((folder/'performance/metrics.csv').open()))
    if len(rows)!=144 or len({(r['trace'],r['capacity'],r['region']) for r in rows})!=144:
        raise ValueError('Incomplete or duplicate metric rows')
    for row in rows:
        capacity=int(row['capacity']); metrics=summaries[(row['trace'],capacity)]['groups'][row['region']]
        baseline=summaries[(row['trace'],4)]['groups'][row['region']]
        comparisons={'hit_delta_pp_vs4':100*(metrics['hit_rate']-baseline['hit_rate']),
                     'latency_reduction_pct_vs4':100*(baseline['average_latency']-metrics['average_latency'])/baseline['average_latency'] if baseline['average_latency'] else None}
        for field, expected in {**metrics,**comparisons}.items():
            if (expected is None and row[field]!='') or (expected is not None and float(row[field])!=expected):
                raise ValueError('Metric differs: '+str((row['trace'],capacity,row['region'],field)))
        if row['source_commit']!=experiments['source_commit'] or row['trace_sha256']!=experiments['inputs']['sha256'][row['trace']+'.trace'] or row['image_sha256']!=experiments['inputs']['sha256']['page_table.mem']:
            raise ValueError('Metric provenance differs')
    return {'status':'PASS','validated_logs':log_count,'performance_runs':len(summaries),
            'correctness_accepted':accepted,'correctness_completed':completed,'correctness_canceled':canceled,
            'correctness_checks':checks,'metric_rows':len(rows),'archived_files':len(actual)}


def verify_results(folder, evidence):
    record = json.loads((folder/'validation.json').read_text())
    expected = {}
    for name, value in record['artifact_sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or path.parts[0]!='results':
            raise ValueError('Invalid result path: '+name)
        expected[str(path.relative_to('results'))] = value
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p!=folder/'validation.json'}
    if record.get('passed') is not True or actual!=set(expected):
        raise ValueError('Result file set differs')
    for name, value in expected.items():
        if digest((folder/name).read_bytes())!=value:
            raise ValueError('Result hash mismatch: '+name)
    run = evidence/'validation/fixed_s1'
    manifest = json.loads((run/'manifest.json').read_text())
    log = gzip.decompress((run/'translation_16.jsonl.gz').read_bytes())
    wlf_hash = digest(gzip.decompress((run/'translation_16.wlf.gz').read_bytes()))
    events = [json.loads(line) for line in log.splitlines()]
    captures = sorted((folder/'screenshots').glob('*/replay.json'))
    cases = {'cold','hit','eviction','fault','full_flush','mid_reset','mid_flush','completion'}
    if {json.loads(p.read_text())['case'] for p in captures}!=cases or len(captures)!=len(cases):
        raise ValueError('Incomplete capture set')
    for path in captures:
        capture = json.loads(path.read_text())
        if (capture['source_log_sha256']!=digest(log) or capture['source_wlf_sha256']!=wlf_hash
                or capture['source_commit']!=manifest['source_commit'] or capture['run_id']!=events[0]['run']
                or capture['screenshot_status']!='captured' or capture['entries']!=16 or capture['seed']!=1):
            raise ValueError('Capture provenance mismatch: '+capture['case'])
        anchor = events[capture['event_seq']]
        if not capture['start_ns']<=anchor['time_ns']<=capture['end_ns']:
            raise ValueError('Capture window omits anchor')
        originals = {'screenshot_original.png','native.ps'}
        if capture['case']=='completion': originals.add('transcript_screenshot_original.png')
        if not originals<=capture['sha256'].keys(): raise ValueError('Missing original capture')
        for name, value in capture['sha256'].items():
            if Path(name).name!=name or digest((path.parent/name).read_bytes())!=value:
                raise ValueError('Changed capture: '+str(path.parent/name))
    return {'status':'PASS','result_files':len(actual),'capture_views':len(captures),'original_screenshots':9}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regression',type=Path);parser.add_argument('--experiments',type=Path)
    parser.add_argument('--out',type=Path);parser.add_argument('--verify',type=Path)
    parser.add_argument('--results',type=Path,help='Verify publication/capture files; uses --verify archive or repository evidence')
    args=parser.parse_args()
    reports = {}
    if args.verify: reports['archive'] = verify(args.verify.resolve())
    if args.results: reports['results'] = verify_results(args.results.resolve(),args.verify.resolve() if args.verify else ROOT/'evidence')
    if reports:
        print(json.dumps(next(iter(reports.values())) if len(reports)==1 else reports,indent=2));return 0
    if not all([args.regression,args.experiments,args.out]):
        parser.error('--regression, --experiments and --out are required to archive')
    regression=json.loads((args.regression/'regression.json').read_text())
    experiments=json.loads((args.experiments/'experiments.json').read_text())
    if not regression.get('passed') or regression.get('scope')!='full' or not experiments.get('passed'):
        raise ValueError('Passing full regression and experiment matrix required')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    copy_records(args.regression.resolve(),out/'validation')
    copy_records(args.experiments.resolve(),out/'performance')
    record={'schema':1,'regression_source':regression['source_commit'],'experiment_source':experiments['source_commit'],
            'compression':'gzip lossless; original JSONL/WLF bytes preserved; gzip mtime=0',
            'sha256':{str(p.relative_to(out)):digest(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}}
    (out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(verify(out),indent=2));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,OSError) as error:print(str(error),file=sys.stderr);sys.exit(1)
