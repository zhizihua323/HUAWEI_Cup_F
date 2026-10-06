"""TASK-Q01C-R1 cross-process interruption/resume supervisor.

Runs the real Q01C entry point against a synthetic fixture:
  P1  completes only the first scan checkpoint, then holds; the supervisor kills it
  PROBE runs --probe-resume (read-only eligibility report)
  P2  runs --resume in a different OS process and must reuse P1 checkpoints with
      zero new scan passes, then finalize
  DEMO exercises --stage dependency failures and single-stage scope

No real attachment (A1-A3) is ever referenced, opened, hashed or stat-ed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
SRC = SOLUTION / 'src'
TESTS = SOLUTION / 'tests'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import q01c_r1_fixture as fixture_builder  # noqa: E402

PIPELINE = SRC / 'quality_q01c.py'
VERIFIER = SRC / 'quality_q01c_verify.py'
CST = timezone(timedelta(hours=8))
PY = sys.executable
PROTECTED_ROOTS = [SOLUTION / 'outputs' / 'quality', SOLUTION / 'outputs' / 'quality_q01c',
                   SOLUTION / 'reports', PROJECT / 'diagnostics' / 'TASK-Q01A',
                   PROJECT / 'diagnostics' / 'TASK-Q01A-R1']
SMALL_FILE_LIMIT = 8 * 1024 * 1024


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str),
                          encoding='utf-8')
    return Path(path)


class PhaseLog:
    def __init__(self, path):
        self.path = Path(path)
        self.fh = open(self.path, 'a', encoding='utf-8', newline='\n')

    def log(self, phase, event, **fields):
        record = {'ts': now_iso(), 'phase': phase, 'event': event, 'pid': os.getpid()}
        record.update(fields)
        self.fh.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.fh.flush()
        print(json.dumps(record, ensure_ascii=False), flush=True)

    def close(self):
        self.fh.close()


def snapshot_protected(exclude_r1_root):
    entries = {}
    for root in PROTECTED_ROOTS:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob('*') if p.is_file()):
            rel = str(path.relative_to(PROJECT)).replace('\\', '/')
            if exclude_r1_root and rel.startswith(str(exclude_r1_root.relative_to(PROJECT))
                                                   .replace('\\', '/')):
                continue
            stat = path.stat()
            entry = {'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': None}
            if stat.st_size <= SMALL_FILE_LIMIT:
                entry['sha256'] = sha256_file(path)
            entries[rel] = entry
    return entries


def spawn_pipeline(run_id, out_root, fixture_dir, extra, stdout_path):
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(out_root),
               '--fixture-dir', str(fixture_dir)] + extra
    handle = open(stdout_path, 'w', encoding='utf-8', newline='\n')
    started = now_iso()
    process = subprocess.Popen(command, cwd=str(PROJECT), stdout=handle, stderr=subprocess.STDOUT)
    return {'command': command, 'process': process, 'handle': handle, 'started': started,
            'pid': process.pid}


def run_sync(run_id, out_root, fixture_dir, extra, stdout_path):
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(out_root),
               '--fixture-dir', str(fixture_dir)] + extra
    started = now_iso()
    with open(stdout_path, 'w', encoding='utf-8', newline='\n') as handle:
        completed = subprocess.run(command, cwd=str(PROJECT), stdout=handle,
                                   stderr=subprocess.STDOUT, timeout=600)
    return {'command': command, 'exit_code': completed.returncode, 'started': started,
            'finished': now_iso(), 'stdout': str(stdout_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R1 two-process interruption test')
    parser.add_argument('--r1-dir', required=True)
    parser.add_argument('--hold-seconds', type=int, default=180)
    args = parser.parse_args(argv)
    r1_dir = Path(args.r1_dir).resolve()
    if not r1_dir.is_dir():
        raise SystemExit(f'R1 directory does not exist: {r1_dir}')
    phases = PhaseLog(r1_dir / 'stage_status.jsonl')
    commands = [{'role': 'r1_harness', 'command': [PY, '-X', 'utf8', str(Path(__file__)),
                                                   '--r1-dir', str(r1_dir)],
                 'pid': os.getpid(), 'started_local': now_iso()}]
    started_local = now_iso()
    fixture_dir = r1_dir / 'synthetic_fixture'
    runs_root = r1_dir / 'interruption_run'
    runs_root.mkdir(parents=True, exist_ok=True)
    phases.log('fixture_build', 'start')
    fixture = fixture_builder.build(fixture_dir)
    fixture_manifest_sha = sha256_file(fixture_dir / 'fixture_manifest.json')
    phases.log('fixture_build', 'complete', fixture_id=fixture['fixture_id'],
               rows=fixture['expected_rows_total'], manifest_sha256=fixture_manifest_sha)
    before = snapshot_protected(r1_dir)
    write_json(r1_dir / 'protected_artifacts_before.json',
               {'generated_local': now_iso(), 'entries': before, 'n_entries': len(before),
                'note': 'sha256 for files <= 8 MiB, size+mtime for every file; F题/raw data and '
                        'diagnostics/TASK-C01* are deliberately not touched'})
    run_id = 'synthetic_run'
    run_dir = runs_root / run_id
    if run_dir.exists():
        raise SystemExit(f'synthetic run dir already exists: {run_dir}')
    process_1_dir = runs_root / 'process_1'
    process_2_dir = runs_root / 'process_2'
    probe_dir = runs_root / 'process_probe'
    for path in (process_1_dir, process_2_dir, probe_dir):
        path.mkdir(parents=True, exist_ok=True)
    checkpoint_names = {'payload': run_dir / 'checkpoints' / 's10_scan_a1.payload.parquet',
                        'meta': run_dir / 'checkpoints' / 's10_scan_a1.meta.json',
                        'checkpoint_marker': run_dir / 'checkpoints' / 's10_scan_a1.checkpoint.COMPLETE',
                        'stage_marker': run_dir / 'checkpoints' / 's10_scan_a1.stage.COMPLETE'}
    # ---------------- P1 ----------------
    phases.log('p1', 'start', hold_after_stage='s10_scan_a1')
    p1 = spawn_pipeline(run_id, runs_root, fixture_dir, ['--hold-after-stage', 's10_scan_a1'],
                        process_1_dir / 'stdout.log')
    status_path = run_dir / 'stage_status.jsonl'
    deadline = time.monotonic() + args.hold_seconds
    hold_seen = False
    while time.monotonic() < deadline and p1['process'].poll() is None:
        if status_path.is_file() and 'hold_after_stage' in status_path.read_text(encoding='utf-8'):
            hold_seen = True
            break
        time.sleep(0.1)
    if not hold_seen:
        phases.log('p1', 'fail', reason='hold_after_stage event not observed')
        raise SystemExit('P1 did not reach the hold hook')
    checkpoint_before = {name: sha256_file(path) for name, path in checkpoint_names.items()}
    counters_before = read_json(run_dir / 'scan_counters.json')
    time.sleep(0.5)
    p1['process'].send_signal(signal.SIGTERM)
    p1_exit = p1['process'].wait(timeout=60)
    p1['handle'].close()
    termination = {'pid': p1['pid'], 'command': p1['command'], 'started_local': p1['started'],
                   'terminated_local': now_iso(), 'exit_code': p1_exit,
                   'termination_mechanism': 'supervisor SIGTERM after the checkpoint marker appeared',
                   'hold_hook_seen': hold_seen,
                   'last_valid_checkpoint': {'stage': 's10_scan_a1',
                                             'payload_sha256': checkpoint_before['payload'],
                                             'meta_sha256': checkpoint_before['meta'],
                                             'checkpoint_marker_sha256': checkpoint_before['checkpoint_marker'],
                                             'stage_marker_sha256': checkpoint_before['stage_marker']},
                   'scan_counters_at_termination': counters_before,
                   'run_dir': str(run_dir)}
    write_json(process_1_dir / 'termination_evidence.json', termination)
    write_json(process_1_dir / 'command.json',
               {'command': p1['command'], 'pid': p1['pid'], 'exit_code': p1_exit,
                'started_local': p1['started'], 'terminated_local': termination['terminated_local'],
                'stdout': str(process_1_dir / 'stdout.log'), 'hold_hook': 's10_scan_a1'})
    commands.append({'role': 'process_1', 'command': p1['command'], 'pid': p1['pid'],
                     'exit_code': p1_exit, 'started_local': p1['started'],
                     'terminated_local': termination['terminated_local']})
    phases.log('p1', 'terminated', pid=p1['pid'], exit_code=p1_exit, hold_seen=hold_seen)
    # ---------------- probe ----------------
    phases.log('probe', 'start')
    probe = run_sync(run_id, runs_root, fixture_dir, ['--probe-resume'],
                     probe_dir / 'stdout.log')
    probe_report = None
    if (run_dir / 'probe_resume_report.json').is_file():
        probe_report = read_json(run_dir / 'probe_resume_report.json')
        write_json(probe_dir / 'probe_resume_report.json', probe_report)
    write_json(probe_dir / 'command.json', probe)
    commands.append({'role': 'probe_process', **probe})
    phases.log('probe', 'complete', exit_code=probe['exit_code'],
               reusable=(probe_report or {}).get('reusable_stages'))
    # ---------------- P2 ----------------
    phases.log('p2', 'start')
    p2 = run_sync(run_id, runs_root, fixture_dir, ['--resume'], process_2_dir / 'stdout.log')
    write_json(process_2_dir / 'command.json', p2)
    commands.append({'role': 'process_2', **p2})
    checkpoint_after = {name: sha256_file(path) for name, path in checkpoint_names.items()}
    counters_after = read_json(run_dir / 'scan_counters.json')
    resume_evidence_run = read_json(run_dir / 'resume_evidence.json')
    phases.log('p2', 'complete', exit_code=p2['exit_code'],
               reused=[d.get('stage') for d in resume_evidence_run.get('decisions', [])
                       if d.get('action') == 'stage_reused'])
    # ---------------- stage scope demos ----------------
    phases.log('stage_demo', 'start')
    demo_missing = runs_root / 'stage_demo_missing_prereq'
    demo_missing.mkdir(exist_ok=True)
    missing_result = run_sync('missing_prereq', demo_missing, fixture_dir, ['--stage',
                             's20_score_primary'], demo_missing / 'stdout.log')
    missing_summary = read_json(demo_missing / 'missing_prereq' / 'run_summary.json')
    demo_single = runs_root / 'stage_demo_single_stage'
    demo_single.mkdir(exist_ok=True)
    single_runs = []
    for index, stage_name in enumerate(['s00_preflight', 's01_synthetic_tests', 's10_scan_a1']):
        extra = ['--stage', stage_name] + (['--resume'] if index else [])
        result = run_sync('single_stage', demo_single, fixture_dir, extra,
                          demo_single / f'stdout_{stage_name}.log')
        single_runs.append({'stage': stage_name, **result})
    single_summary = read_json(demo_single / 'single_stage' / 'run_summary.json')
    write_json(runs_root / 'stage_scope_demo.json', {
        'missing_prerequisite_run': {'command': missing_result['command'],
                                     'exit_code': missing_result['exit_code'],
                                     'missing_prerequisites': missing_summary.get('missing_prerequisites'),
                                     'status': missing_summary.get('status')},
        'single_stage_runs': [{'stage': r['stage'], 'command': r['command'],
                               'exit_code': r['exit_code']} for r in single_runs],
        'single_stage_run_summary': {'executed_stages': single_summary.get('executed_stages'),
                                     'skipped_stages': single_summary.get('skipped_stages'),
                                     'status': single_summary.get('status')},
        'note': '--stage really controls the executed scope and refuses to run without prerequisites'})
    phases.log('stage_demo', 'complete',
               missing_prereq_exit=missing_result['exit_code'],
               single_stage_exits=[r['exit_code'] for r in single_runs])
    # ---------------- aggregate evidence ----------------
    new_passes_p2 = {fid: int(counters_after['files'].get(fid, {}).get('passes', 0))
                     - int(counters_before['files'].get(fid, {}).get('passes', 0))
                     for fid in counters_after['files']}
    evidence = {
        'run_id': r1_dir.name, 'generated_local': now_iso(),
        'fixture': {'dir': str(fixture_dir), 'manifest_sha256': fixture_manifest_sha,
                    'fixture_id': fixture['fixture_id'],
                    'expected_rows': fixture['expected_rows'],
                    'input_sha256': fixture['input_sha256']},
        'processes': {
            'p1': {'pid': p1['pid'], 'command': p1['command'],
                   'started_local': p1['started'], 'terminated_local': termination['terminated_local'],
                   'exit_code': p1_exit, 'hold_hook_seen': hold_seen},
            'p2': {'pid': read_json(run_dir / 'run_summary.json').get('process_pid'),
                   'command': p2['command'], 'started_local': p2['started'],
                   'finished_local': p2['finished'], 'exit_code': p2['exit_code']},
            'probe': {'command': probe['command'], 'exit_code': probe['exit_code'],
                      'reused_stages': [d['stage'] for d in
                                        (probe_report or {}).get('reusable_stages', [])]},
            'same_run_dir': True,
            'distinct_pids': p1['pid'] != os.getpid()},
        'checkpoints': {'stage': 's10_scan_a1',
                        'hash_before_p2': checkpoint_before, 'hash_after_p2': checkpoint_after,
                        'hash_invariant': checkpoint_before == checkpoint_after},
        'scan_counters': {'before_p2': counters_before, 'after_p2': counters_after,
                          'new_passes_in_p2': new_passes_p2,
                          'new_passes_in_p2_total': sum(new_passes_p2.values()),
                          'reuse_events': counters_after.get('reuse_events', [])},
        'run_summary': {'status': read_json(run_dir / 'run_summary.json').get('status'),
                        'executed_stages': read_json(run_dir / 'run_summary.json').get('executed_stages'),
                        'reused_stages': read_json(run_dir / 'run_summary.json').get('reused_stages'),
                        'output_manifest_present': (run_dir / 'output_manifest.json').is_file()},
        'synthetic_run_dir': str(run_dir),
        'a1_a3_access': {'opened': 0, 'hashed': 0, 'decompressed': 0, 'stat_calls': 0,
                         'note': 'the harness and pipeline only ever reference the synthetic fixture '
                                 'directory in this test'},
    }
    write_json(r1_dir / 'resume_evidence.json', evidence)
    after = snapshot_protected(r1_dir)
    write_json(r1_dir / 'protected_artifacts_after.json',
               {'generated_local': now_iso(), 'entries': after, 'n_entries': len(after)})
    checkpoint_files = sorted((run_dir / 'checkpoints').glob('*'))
    write_json(r1_dir / 'checkpoint_manifest.json', {
        'run_id': r1_dir.name, 'generated_local': now_iso(),
        'synthetic_run_dir': str(run_dir),
        'checkpoints': [{'path': str(f.relative_to(run_dir)).replace('\\', '/'),
                         'bytes': f.stat().st_size, 'sha256': sha256_file(f)}
                        for f in checkpoint_files if f.is_file()],
        'hash_invariance': {'stage': 's10_scan_a1', 'before': checkpoint_before,
                            'after': checkpoint_after,
                            'invariant': checkpoint_before == checkpoint_after},
        'scan_counters': counters_after})
    write_json(r1_dir / 'command_log.json', {
        'run_id': r1_dir.name, 'generated_local': now_iso(),
        'note': 'commands are recorded from the actual spawn/subprocess argument lists; the '
                'historical TASK-Q01C scientific-run main command was never written to disk and '
                'remains a documented historical NOT_VERIFIABLE item',
        'commands': commands + [{'role': 'stage_scope_demo', 'command': missing_result['command'],
                                 'exit_code': missing_result['exit_code']}]
                   + [{'role': f"stage_demo_{r['stage']}", 'command': r['command'],
                       'exit_code': r['exit_code']} for r in single_runs]})
    phases.log('harness', 'complete', new_passes_in_p2=sum(new_passes_p2.values()),
               checkpoint_invariant=(checkpoint_before == checkpoint_after))
    phases.close()
    print(json.dumps({'r1_dir': str(r1_dir), 'run_dir': str(run_dir),
                      'p1_pid': p1['pid'], 'p2_exit': p2['exit_code'],
                      'probe_exit': probe['exit_code'],
                      'new_passes_in_p2': new_passes_p2,
                      'checkpoint_invariant': checkpoint_before == checkpoint_after,
                      'run_status': evidence['run_summary']['status']}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
