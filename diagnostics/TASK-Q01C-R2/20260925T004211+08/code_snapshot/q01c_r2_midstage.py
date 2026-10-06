"""TASK-Q01C-R2 mid-stage (S30) cross-process interruption/resume supervisor."""
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
for path in (str(SRC), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import q01c_r2_fixture as fixture_builder  # noqa: E402

PIPELINE = SRC / 'quality_q01c.py'
CST = timezone(timedelta(hours=8))
PY = sys.executable
SMALL_LIMIT = 8 * 1024 * 1024
PROTECTED_ROOTS = [SOLUTION / 'outputs' / 'quality', SOLUTION / 'outputs' / 'quality_q01c',
                   SOLUTION / 'reports', PROJECT / 'diagnostics' / 'TASK-Q01A',
                   PROJECT / 'diagnostics' / 'TASK-Q01A-R1']
CHECKPOINT_STAGES = ['s10_scan_a1', 's11_scan_a2', 's12_scan_a3', 's20_score_primary',
                     's30_sensitivity']


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


def snapshot_protected():
    entries = {}
    for root in PROTECTED_ROOTS:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob('*') if p.is_file()):
            rel = str(path.relative_to(PROJECT)).replace('\\', '/')
            stat = path.stat()
            entry = {'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': None}
            if stat.st_size <= SMALL_LIMIT:
                entry['sha256'] = sha256_file(path)
            entries[rel] = entry
    return entries


def checkpoint_state(run_dir, stages):
    state = {}
    for stage in stages:
        base = run_dir / 'checkpoints' / stage
        files = {'payload': Path(str(base) + '.payload.parquet'),
                 'meta': Path(str(base) + '.meta.json'),
                 'checkpoint_marker': Path(str(base) + '.checkpoint.COMPLETE'),
                 'stage_marker': Path(str(base) + '.stage.COMPLETE')}
        state[stage] = {name: (sha256_file(path) if path.is_file() else None)
                        for name, path in files.items()}
    return state


def spawn_pipeline(run_id, out_root, fixture_dir, extra, stdout_path):
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(out_root),
               '--fixture-dir', str(fixture_dir)] + extra
    handle = open(stdout_path, 'w', encoding='utf-8', newline='\n')
    process = subprocess.Popen(command, cwd=str(PROJECT), stdout=handle, stderr=subprocess.STDOUT)
    return {'command': command, 'process': process, 'handle': handle, 'started': now_iso(),
            'pid': process.pid}


def run_sync(run_id, out_root, fixture_dir, extra, stdout_path):
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(out_root),
               '--fixture-dir', str(fixture_dir)] + extra
    started = now_iso()
    with open(stdout_path, 'w', encoding='utf-8', newline='\n') as handle:
        completed = subprocess.run(command, cwd=str(PROJECT), stdout=handle,
                                   stderr=subprocess.STDOUT, timeout=900)
    return {'command': command, 'exit_code': completed.returncode, 'started_local': started,
            'finished_local': now_iso(), 'stdout': str(stdout_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R2 mid-stage cross-process test')
    parser.add_argument('--r2-dir', required=True)
    parser.add_argument('--hold-seconds', type=int, default=180)
    args = parser.parse_args(argv)
    r2_dir = Path(args.r2_dir).resolve()
    if not r2_dir.is_dir():
        raise SystemExit(f'R2 directory missing: {r2_dir}')
    phases = PhaseLog(r2_dir / 'stage_status.jsonl')
    phases.log('harness', 'start', note='R2 mid-stage cross-process supervisor')
    commands = [{'role': 'r2_harness', 'command': [PY, '-X', 'utf8', str(Path(__file__).resolve()),
                                                   '--r2-dir', str(r2_dir)],
                 'pid': os.getpid(), 'started_local': now_iso()}]
    fixture_dir = r2_dir / 'synthetic_fixture'
    phases.log('fixture_build', 'start')
    fixture = fixture_builder.main(['--out-dir', str(fixture_dir)]) if False else None
    import q01c_r2_fixture as fb
    fb.main(['--out-dir', str(fixture_dir)])
    fixture_manifest = read_json(fixture_dir / 'fixture_manifest.json')
    phases.log('fixture_build', 'complete', fixture_id=fixture_manifest['fixture_id'],
               rows=fixture_manifest['expected_rows_total'])
    before = snapshot_protected()
    write_json(r2_dir / 'protected_artifacts_before.json',
               {'generated_local': now_iso(), 'entries': before, 'n_entries': len(before),
                'note': 'sha256 for files <= 8 MiB, size+mtime for all; F题/raw data and '
                        'diagnostics/TASK-C01* are never referenced'})
    root = r2_dir / 'midstage_interruption'
    process_1_dir = root / 'process_1'
    process_2_dir = root / 'process_2'
    for path in (process_1_dir, process_2_dir):
        path.mkdir(parents=True, exist_ok=True)
    run_id = 'midstage_run'
    run_dir = root / run_id
    phases.log('p1', 'start', hold_after_stage='s30_sensitivity')
    p1 = spawn_pipeline(run_id, root, fixture_dir, ['--hold-after-stage', 's30_sensitivity'],
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
        raise SystemExit('P1 did not reach the S30 hold hook')
    time.sleep(0.4)
    checkpoint_before = checkpoint_state(run_dir, CHECKPOINT_STAGES)
    counters_before = read_json(run_dir / 'stage_compute_counters.json')
    scan_before = read_json(run_dir / 'scan_counters.json')
    p1['process'].send_signal(signal.SIGTERM)
    p1_exit = p1['process'].wait(timeout=60)
    p1['handle'].close()
    termination = {'pid': p1['pid'], 'command': p1['command'], 'started_local': p1['started'],
                   'terminated_local': now_iso(), 'exit_code': p1_exit,
                   'termination_mechanism': 'supervisor SIGTERM after the S30 checkpoint marker',
                   'hold_hook_seen': hold_seen, 'last_valid_checkpoint_stage': 's30_sensitivity',
                   'checkpoint_hashes_at_termination': checkpoint_before,
                   'stage_compute_counters_at_termination': counters_before,
                   'run_dir': str(run_dir)}
    write_json(process_1_dir / 'termination_evidence.json', termination)
    write_json(process_1_dir / 'command.json',
               {'command': p1['command'], 'pid': p1['pid'], 'exit_code': p1_exit,
                'started_local': p1['started'], 'terminated_local': termination['terminated_local'],
                'stdout': str(process_1_dir / 'stdout.log')})
    commands.append({'role': 'midstage_process_1', 'command': p1['command'], 'pid': p1['pid'],
                     'exit_code': p1_exit, 'started_local': p1['started'],
                     'terminated_local': termination['terminated_local']})
    phases.log('p1', 'terminated', pid=p1['pid'], exit_code=p1_exit, hold_seen=hold_seen)
    phases.log('probe', 'start')
    probe = run_sync(run_id, root, fixture_dir, ['--probe-resume'], process_1_dir / 'probe_stdout.log')
    commands.append({'role': 'midstage_probe', **probe})
    phases.log('probe', 'complete', exit_code=probe['exit_code'])
    phases.log('p2', 'start')
    p2 = run_sync(run_id, root, fixture_dir, ['--resume'], process_2_dir / 'stdout.log')
    write_json(process_2_dir / 'command.json', {**p2, 'pid': read_json(
        run_dir / 'run_summary.json').get('process_pid')})
    commands.append({'role': 'midstage_process_2', **p2})
    checkpoint_after = checkpoint_state(run_dir, CHECKPOINT_STAGES)
    counters_after = read_json(run_dir / 'stage_compute_counters.json')
    scan_after = read_json(run_dir / 'scan_counters.json')
    run_summary = read_json(run_dir / 'run_summary.json')
    resume_evidence_run = read_json(run_dir / 'resume_evidence.json')
    new_computations = {stage: int(counters_after['stages'].get(stage, {}).get('computations', 0))
                        - int(counters_before['stages'].get(stage, {}).get('computations', 0))
                        for stage in CHECKPOINT_STAGES}
    phases.log('p2', 'complete', exit_code=p2['exit_code'], new_computations=new_computations,
               status=run_summary.get('status'))
    evidence = {
        'run_id': r2_dir.name, 'generated_local': now_iso(),
        'fixture': {'id': fixture_manifest['fixture_id'],
                    'rows': fixture_manifest['expected_rows_total'],
                    'manifest_sha256': sha256_file(fixture_dir / 'fixture_manifest.json')},
        'synthetic_run_dir': str(run_dir),
        'processes': {
            'p1': {'pid': p1['pid'], 'command': p1['command'], 'started_local': p1['started'],
                   'terminated_local': termination['terminated_local'], 'exit_code': p1_exit,
                   'hold_hook_seen': hold_seen, 'hold_after_stage': 's30_sensitivity'},
            'p2': {'pid': run_summary.get('process_pid'), 'command': p2['command'],
                   'started_local': p2['started_local'], 'finished_local': p2['finished_local'],
                   'exit_code': p2['exit_code']},
            'probe': {'command': probe['command'], 'exit_code': probe['exit_code'],
                      'report': read_json(run_dir / 'probe_resume_report.json')
                      if (run_dir / 'probe_resume_report.json').is_file() else None},
            'distinct_pids': p1['pid'] != run_summary.get('process_pid')},
        'checkpoints': {'stages': CHECKPOINT_STAGES, 'hashes_before_p2': checkpoint_before,
                        'hashes_after_p2': checkpoint_after,
                        'hash_invariant': checkpoint_before == checkpoint_after},
        'stage_compute_counters': {'before_p2': counters_before, 'after_p2': counters_after,
                                   'new_computations_in_p2': new_computations,
                                   'new_computations_total': sum(new_computations.values())},
        'scan_counters': {'before_p2': scan_before, 'after_p2': scan_after},
        'run_summary': {'status': run_summary.get('status'),
                        'executed_stages': run_summary.get('executed_stages'),
                        'reused_stages': run_summary.get('reused_stages'),
                        'stage_seconds': run_summary.get('stage_seconds'),
                        'stage_terminal_events': run_summary.get('stage_terminal_events'),
                        'stage_exit_codes': run_summary.get('stage_exit_codes'),
                        'output_manifest_present': (run_dir / 'output_manifest.json').is_file()},
        'resume_decisions': resume_evidence_run.get('decisions', []),
        'a1_a3_access': {'opened': 0, 'read': 0, 'stat': 0, 'hash': 0, 'decompress': 0, 'scan': 0,
                         'basis': 'fixture path isolation and code/command audit; the real '
                                  'attachments are never referenced by any R2 process'}}
    write_json(r2_dir / 'resume_evidence.json', evidence)
    write_json(r2_dir / 'checkpoint_manifest.json', {
        'run_id': r2_dir.name, 'generated_local': now_iso(), 'synthetic_run_dir': str(run_dir),
        'checkpoints': [{'stage': stage, **{name: value for name, value in hashes.items()}}
                        for stage, hashes in checkpoint_after.items()],
        'hash_invariance': {'before': checkpoint_before, 'after': checkpoint_after,
                            'invariant': checkpoint_before == checkpoint_after}})
    write_json(r2_dir / 'command_log.json', {
        'run_id': r2_dir.name, 'generated_local': now_iso(),
        'note': 'commands recorded from the actual spawn/subprocess argument lists; the historical '
                'TASK-Q01C scientific-run main command was never persisted (NOT_VERIFIABLE)',
        'commands': commands})
    phases.log('harness', 'complete', new_computations_total=sum(new_computations.values()),
               checkpoint_invariant=checkpoint_before == checkpoint_after)
    phases.close()
    print(json.dumps({'r2_dir': str(r2_dir), 'run_dir': str(run_dir), 'p1_pid': p1['pid'],
                      'p2_pid': run_summary.get('process_pid'), 'p1_exit': p1_exit,
                      'p2_exit': p2['exit_code'], 'new_computations': new_computations,
                      'hash_invariant': checkpoint_before == checkpoint_after,
                      'run_status': run_summary.get('status')}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
