#!/usr/bin/env python3
"""Focus genuine ModelSim WLF replays using observed transaction events."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def selections(events, entries):
    accepts = {e['txn']: e for e in events if e['event'] == 'accept'}
    consumes = {e['txn']: e for e in events if e['event'] == 'consume'}
    def interval(event, title, before=15, after=20):
        txn = event['txn']
        start = accepts.get(txn, event)['time_ns'] - before
        end = consumes.get(txn, event)['time_ns'] + after
        return {'title': title, 'start_ns': max(0, start), 'end_ns': end,
                'transactions': [txn] if txn else [], 'event_seq': event['seq']}
    cold = next(e for e in accepts.values() if not e['hit'] and not e['expected_fault'] and e['txn'] in consumes)
    hit = next(e for e in accepts.values() if e['hit'] and e['txn'] in consumes and consumes[e['txn']]['cycle'] == e['cycle'])
    eviction = next(e for e in events if e['event'] == 'refill' and e['evict'])
    fault = next(e for e in events if e['event'] == 'first_result' and e['fault'] and e['level'] == 0)
    controls = {e['cycle']: e for e in events if e['event'] in ['flush', 'reset']}
    clear = next(e for e in events if e['event'] == 'state' and e['valid_before'] is not None
                 and int(e['valid_before'], 16) == (1 << entries)-1 and int(e['valid_after'], 16) == 0
                 and controls.get(e['cycle'], {}).get('event') == 'flush')
    result = {'cold': interval(cold, 'Cold two-level walk and refill'),
              'hit': interval(hit, 'Immediate accepted and consumed hit'),
              'eviction': interval(eviction, 'Full TLB tree-PLRU eviction'),
              'fault': interval(fault, 'Final-level PTE fault'),
              'full_flush': {'title':'All populated entries cleared', 'start_ns':clear['time_ns']-20, 'end_ns':clear['time_ns']+35, 'transactions':[], 'event_seq':clear['seq']}}
    for control in ['reset', 'flush']:
        cancel = next(e for e in events if e['event'] == 'cancel' and controls[e['cycle']]['event'] == control
                      and any(d['event'] == 'discard' and d['txn'] == e['txn'] for d in events))
        discarded = next(e for e in events if e['event'] == 'discard' and e['txn'] == cancel['txn'])
        recovery = next(e for e in events if e['event'] == 'consume' and e['cycle'] > discarded['cycle'])
        selected = interval(cancel, 'Mid-walk '+control+', late discard and recovery', 25, 25)
        selected['end_ns'] = recovery['time_ns'] + 15
        selected['transactions'] += [recovery['txn']]
        result['mid_'+control] = selected
    finish = next(e for e in events if e['event'] == 'finish')
    result['completion'] = interval(finish, 'Completed checks and zero failures', 30, 0)
    return result


def tcl_quote(value):
    escaped = str(value).translate(str.maketrans({'\\': '\\\\', '"': '\\"', '$': '\\$', '[': '\\[', ']': '\\]'}))
    return '"'+escaped+'"'


def wave_windows():
    result = subprocess.run(['xwininfo', '-root', '-tree'], text=True, capture_output=True)
    return set(re.findall(r'(0x[0-9a-f]+) "[^"]*": \("wave" "WindowObj"\)', result.stdout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Directory with manifest.json and translation_N logs/WLF')
    parser.add_argument('--entries', type=int, choices=[4, 8, 16], default=16)
    parser.add_argument('--case', choices=['cold', 'hit', 'eviction', 'fault', 'full_flush', 'mid_reset', 'mid_flush', 'completion'], default='cold')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--export', action='store_true', help='Native PostScript waveform, not a screenshot')
    parser.add_argument('--capture-x11', action='store_true', help='Unaltered actual Wave-window pixels using X11 ImageMagick import')
    parser.add_argument('--rasterize', action='store_true', help='Render native PS separately with Ghostscript')
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = json.loads((run/'manifest.json').read_text())
    if not manifest.get('passed') or manifest.get('suite') != 'translation' or manifest.get('trace'):
        raise ValueError('A passing directed translation run is required')
    stem = 'translation_'+str(args.entries)
    log = run/(stem+'.jsonl')
    log_bytes = log.read_bytes() if log.exists() else gzip.decompress((run/(stem+'.jsonl.gz')).read_bytes())
    events = [json.loads(line) for line in log_bytes.splitlines()]
    cases = selections(events, args.entries)
    if args.list:
        print(json.dumps(cases, indent=2)); return 0
    out = (args.out or ROOT/'runs'/('replay_'+args.case+'_'+str(time.time_ns()))).resolve()
    out.mkdir(parents=True, exist_ok=False)
    wlf = run/(stem+'.wlf')
    if not wlf.exists():
        wlf = out/(stem+'.wlf')
        wlf.write_bytes(gzip.decompress((run/(stem+'.wlf.gz')).read_bytes()))
    chosen = cases[args.case]
    focus_event = next(event for event in events if event['seq']==chosen['event_seq'])
    chosen['cursor_ns'] = focus_event['time_ns'] + (0.001 if focus_event['phase']=='post' else -0.001)
    if args.case=='completion':
        chosen['cursor_ns'] = focus_event['time_ns']
        chosen['end_ns'] = focus_event['time_ns']+1
    prefix = '/translation_tb/dut/'
    signals = [('clk','binary'), ('reset','binary'), ('flush','binary')]
    if args.case == 'full_flush':
        signals += [('cache/entries_q['+str(i)+'].valid','binary') for i in range(args.entries)]
        signals += [('cache/replacement/state_q','hexadecimal'), ('req_valid','binary'), ('req_ready','binary'), ('resp_valid','binary')]
    elif args.case == 'completion':
        signals += [('req_valid','binary'), ('resp_valid','binary')]
    else:
        signals += [('req_valid','binary'), ('req_ready','binary'), ('req_va','hexadecimal'), ('req_cookie','unsigned'),
                    ('lookup_hit','binary'), ('walker/va_q','hexadecimal'), ('walker/state_q','symbolic'),
                    ('walker/level_q','unsigned'), ('mem_req_valid','binary'), ('mem_req_ready','binary'),
                    ('mem_req_addr','hexadecimal'), ('mem_resp_valid','binary'), ('mem_resp_cookie','unsigned'),
                    ('mem_resp_data','hexadecimal'), ('fill_valid','binary')]
        if args.case == 'eviction':
            signals += [('cache/fill_index','unsigned'), ('cache/victim','unsigned'), ('fill_vpn','hexadecimal'),
                        ('cache/replacement/state_q','hexadecimal')]
        signals += [('resp_valid','binary'), ('resp_ready','binary'), ('resp_cookie','unsigned'),
                    ('resp_pa','hexadecimal'), ('resp_fault','symbolic')]
    paths = [(prefix+path, radix) for path,radix in signals]
    if args.case == 'completion':
        paths += [('/translation_tb/completed','unsigned'), ('/translation_tb/failures','unsigned')]
    commands = ['onerror {puts REPLAY_FAILED; quit -f -code 21}', 'view wave -undock -width 1800 -height 820 -x 20 -y 20', 'delete wave *']
    for path,radix in paths:
        label = {'/translation_tb/dut/cache/replacement/state_q':'plru_bits', '/translation_tb/dut/walker/state_q':'walker_state'}.get(path,path.rsplit('/',1)[1])
        commands.append('add wave -label '+tcl_quote(label)+' -radix '+radix+' '+tcl_quote(path))
    commands += ['configure wave -namecolwidth 190', 'configure wave -valuecolwidth 100',
                 'wave zoom range '+str(chosen['start_ns'])+'ns '+str(chosen['end_ns'])+'ns',
                 'wave cursor time -time '+str(chosen['cursor_ns'])+'ns 1', 'wave cursor active 1']
    if args.case == 'completion':
        transcript = (run/(stem+'.transcript')).read_text()
        for line in transcript.splitlines():
            if 'TRANSLATION_PASS' in line or 'RUN_COMPLETE' in line:
                commands.append('puts '+tcl_quote('SAVED_RUN_TRANSCRIPT: '+line))
        commands.append('view transcript -undock -width 1500 -height 600 -x 30 -y 30')
        for keys in [('accepted','completed','canceled'),('hits','misses','walks'),('first_results','checks'),('stall_cycles','queue_cycles','walker_busy_cycles')]:
            commands.append('puts '+tcl_quote('OBSERVED_FINISH: '+'  '.join(key+'='+str(events[-1][key]) for key in keys)))
        report_path=run.parent/'regression.json'
        if report_path.exists():
            report=json.loads(report_path.read_text())
            commands.append('puts '+tcl_quote('SAVED_FULL_REGRESSION: passed='+str(report['passed'])+'  scope='+report['scope']+'  steps='+str(len(report['steps']))+'  expected_failures='+str(sum(not step['expected_success'] for step in report['steps']))))
    if args.export:
        commands.append('write wave '+tcl_quote(out/'native.ps')+' -start '+str(chosen['start_ns'])+'ns -end '+str(chosen['end_ns'])+'ns -portrait -width 12 -height 9 -margin 0.5')
    commands.append('puts REPLAY_READY')
    if args.capture_x11:
        commands.append('after 8000 {quit -f -code 0}')
    macro = out/'focus.do'; macro.write_text('\n'.join(commands)+'\n')
    config = json.loads(args.config.read_text()) if args.config else {}
    env = os.environ.copy();env.update(config.get('env',{}))
    program = config.get('programs',{}).get('vsim',[shutil.which('vsim') or 'vsim'])
    command = program+['-gui','-view',str(wlf),'-l',str(out/'replay.transcript'),'-do','do '+tcl_quote(macro)]
    before = wave_windows() if args.capture_x11 else set()
    record = {'schema':1,'kind':'ModelSim native waveform replay', 'case':args.case, **chosen,
              'source_commit':manifest['source_commit'], 'run_id':events[0]['run'], 'entries':args.entries,
              'seed':manifest['seed'], 'source_log_sha256':hashlib.sha256(log_bytes).hexdigest(),
              'source_wlf_sha256':hashlib.sha256(wlf.read_bytes()).hexdigest(),
              'signal_radices':paths,'command':command,'screenshot_status':'not_requested'}
    with (out/'stdout.txt').open('w') as stdout:
        process = subprocess.Popen(command,cwd=out,env=env,stdout=stdout,stderr=subprocess.STDOUT)
        if args.capture_x11:
            deadline = time.monotonic()+90
            while time.monotonic()<deadline:
                transcript = out/'replay.transcript'
                ready = transcript.exists() and 'REPLAY_READY' in transcript.read_text(errors='replace')
                new = wave_windows()-before if ready else set()
                if ready and len(new)==1:
                    window = new.pop()
                    subprocess.run(['import','-window',window,str(out/'screenshot_original.png')],check=True,timeout=10)
                    record['screenshot_status']='captured';record['x11_window']=window
                    if args.case=='completion':
                        tree=subprocess.run(['xwininfo','-root','-tree'],text=True,capture_output=True).stdout
                        matches=re.findall(r'(0x[0-9a-f]+) "Transcript": \("[^"]+" "WindowObj"\)',tree)
                        if len(matches)!=1: raise RuntimeError('Cannot uniquely locate Transcript window')
                        subprocess.run(['import','-window',matches[0],str(out/'transcript_screenshot_original.png')],check=True,timeout=10)
                    break
                if process.poll() is not None:
                    raise RuntimeError('GUI exited before capture; inspect replay transcript')
                time.sleep(.2)
            else:
                process.terminate();raise RuntimeError('GUI capture timeout')
            record['exit']=process.wait(timeout=20)
            if record['exit']:
                raise RuntimeError('ModelSim replay failed')
        else:
            print('Interactive replay opened. Close ModelSim when finished.');process.wait()
    if 'REPLAY_READY' not in (out/'replay.transcript').read_text():
        raise RuntimeError('Replay did not finish configuration')
    if args.rasterize:
        if not args.export: raise ValueError('--rasterize requires --export')
        subprocess.run(['gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=png16m','-r150',
                        '-sOutputFile='+str(out/'native_page_%02d.png'),str(out/'native.ps')],check=True)
        shutil.copyfile(out/'native_page_01.png',out/'native_rendered.png')
    record['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
    (out/'replay.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Replay records: '+str(out));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError,KeyError,StopIteration) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
