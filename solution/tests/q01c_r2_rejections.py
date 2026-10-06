"""TASK-Q01C-R2 three rejection paths (payload hash / config / code fingerprint).

Each case starts from its own isolated copy of a synthetic S30-interrupted run and
is exercised through the normal --resume CLI plus --probe-resume. The test proves
INVALID verdicts, non-zero exit, zero recomputation and zero overwrite of the
damaged evidence. No real attachment or real Q computation is involved.
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
for path in (str(SRC), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import q01c_r2_fixture as fixture_builder  # noqa: E402

PIPELINE = SRC / 'quality_q01c.py'
CST = timezone(timedelta(hours=8))
PY = sys.executable
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


def run_cli(run_id, out_root, fixture_dir, extra, stdout_path):
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(out_root),
               '--fixture-dir', str(fixture_dir)] + extra
    started = now_iso()
    with open(stdout_path, 'w', encoding='utf-8', newline='\n') as handle:
        completed = subprocess.run(command, cwd=str(PROJECT), stdout=handle,
                                   stderr=subprocess.STDOUT, timeout=900)
    return {'command': command, 'exit_code': completed.returncode, 'started_local': started,
            'finished_local': now_iso(), 'stdout': str(stdout_path)}


def checkpoint_state(run_dir):
    state = {}
    for stage in CHECKPOINT_STAGES:
        base = run_dir / 'checkpoints' / stage
        files = {'payload': Path(str(base) + '.payload.parquet'),
                 'meta': Path(str(base) + '.meta.json'),
                 'checkpoint_marker': Path(str(base) + '.checkpoint.COMPLETE'),
                 'stage_marker': Path(str(base) + '.stage.COMPLETE')}
        state[stage] = {name: (sha256_file(path) if path.is_file() else None)
                        for name, path in files.items()}
    return state


def counters(run_dir):
    return read_json(run_dir / 'stage_compute_counters.json')


def build_interrupted_base(root, fixture_dir, hold_seconds=180):
    root.mkdir(parents=True, exist_ok=True)
    run_id = 'base_run'
    run_dir = root / run_id
    command = [PY, '-X', 'utf8', str(PIPELINE), '--run-id', run_id, '--out-root', str(root),
               '--fixture-dir', str(fixture_dir), '--hold-after-stage', 's30_sensitivity']
    handle = open(root / 'base_stdout.log', 'w', encoding='utf-8', newline='\n')
    process = subprocess.Popen(command, cwd=str(PROJECT), stdout=handle, stderr=subprocess.STDOUT)
    status_path = run_dir / 'stage_status.jsonl'
    deadline = time.monotonic() + hold_seconds
    hold_seen = False
    while time.monotonic() < deadline and process.poll() is None:
        if status_path.is_file() and 'hold_after_stage' in status_path.read_text(encoding='utf-8'):
            hold_seen = True
            break
        time.sleep(0.1)
    if not hold_seen:
        process.kill()
        raise SystemExit('base run never reached the hold hook')
    time.sleep(0.3)
    process.send_signal(signal.SIGTERM)
    exit_code = process.wait(timeout=60)
    handle.close()
    return {'run_dir': run_dir, 'pid': process.pid, 'exit_code': exit_code, 'hold_seen': hold_seen,
            'command': command}


def inject(case, run_dir):
    checkpoint = run_dir / 'checkpoints'
    if case == 'payload_hash':
        payload = checkpoint / 's30_sensitivity.payload.parquet'
        data = bytearray(payload.read_bytes())
        index = len(data) // 2
        data[index] = data[index] ^ 0x01
        payload.write_bytes(bytes(data))
        return {'injected': 'payload byte flipped', 'file': str(payload.relative_to(run_dir))}
    if case == 'config_mismatch':
        config = run_dir / 'run_config.json'
        payload = read_json(config)
        payload['r2_rejection_probe'] = 'config mismatch injection'
        write_json(config, payload)
        return {'injected': 'run_config.json mutated', 'file': 'run_config.json'}
    if case == 'code_fingerprint':
        meta_path = checkpoint / 's30_sensitivity.meta.json'
        marker_path = checkpoint / 's30_sensitivity.checkpoint.COMPLETE'
        meta = read_json(meta_path)
        meta['code_fingerprint'] = '0' * 64
        write_json(meta_path, meta)
        marker = read_json(marker_path)
        marker['checkpoint_meta_sha256'] = sha256_file(meta_path)
        write_json(marker_path, marker)
        return {'injected': 'meta code_fingerprint rewritten and marker re-bound to the new meta',
                'file': 'checkpoints/s30_sensitivity.meta.json'}
    raise SystemExit(f'unknown case {case}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R2 rejection path tests')
    parser.add_argument('--r2-dir', required=True)
    args = parser.parse_args(argv)
    r2_dir = Path(args.r2_dir).resolve()
    fixture_dir = r2_dir / 'synthetic_fixture'
    if not (fixture_dir / 'fixture_manifest.json').is_file():
        fixture_builder.main(['--out-dir', str(fixture_dir)])
    root = r2_dir / 'rejection_tests'
    base = build_interrupted_base(root / 'base', fixture_dir)
    base_state = checkpoint_state(base['run_dir'])
    base_counters = counters(base['run_dir'])
    results = {}
    for case in ['payload_hash', 'config_mismatch', 'code_fingerprint']:
        case_dir = root / case
        case_dir.mkdir(parents=True, exist_ok=True)
        run_root = case_dir
        run_root.mkdir(exist_ok=True)
        copy_dir = run_root / 'run'
        shutil.copytree('\\\\?\\' + str(base['run_dir']), '\\\\?\\' + str(copy_dir))
        injection = inject(case, copy_dir)
        state_before = checkpoint_state(copy_dir)
        counters_before = counters(copy_dir)
        resume = run_cli('run', run_root, fixture_dir, ['--resume'],
                         case_dir / 'resume_stdout.log')
        state_after = checkpoint_state(copy_dir)
        counters_after = counters(copy_dir)
        probe = run_cli('run', run_root, fixture_dir, ['--probe-resume'],
                        case_dir / 'probe_stdout.log')
        probe_report = read_json(copy_dir / 'probe_resume_report.json')
        invalid_stages = {item['stage']: item['reason'] for item in probe_report['invalid_stages']}
        expected_check = {'payload_hash': 'payload_sha256', 'config_mismatch': 'config_sha256',
                          'code_fingerprint': 'code_fingerprint'}[case]
        results[case] = {
            'case': case, 'injection': injection, 'run_dir': str(copy_dir),
            'resume': resume, 'probe': probe,
            'resume_verdict_events': [line for line in
                                      (copy_dir / 'stage_status.jsonl').read_text(
                                          encoding='utf-8').splitlines()
                                      if '"stage_invalid"' in line or
                                      '"stage_reuse_validation"' in line][-4:],
            'probe_invalid_stages': invalid_stages,
            'expected_failed_check': expected_check,
            'checkpoint_state_before': state_before, 'checkpoint_state_after': state_after,
            'checkpoint_files_unchanged': state_before == state_after,
            'counters_before': counters_before, 'counters_after': counters_after,
            'new_computations': {stage: int(counters_after['stages'].get(stage, {}).get(
                'computations', 0)) - int(counters_before['stages'].get(stage, {}).get(
                'computations', 0)) for stage in CHECKPOINT_STAGES},
            'probe_vs_resume_consistent': bool(invalid_stages) and
                                          expected_check in json.dumps(invalid_stages),
            's30_invalid': any(stage == 's30_sensitivity' for stage in invalid_stages)}
        results[case]['zero_recomputation'] = all(
            value == 0 for value in results[case]['new_computations'].values())
    write_json(r2_dir / 'rejection_tests' / 'rejection_summary.json',
               {'generated_local': now_iso(), 'base_run': {'pid': base['pid'],
                                                           'exit_code': base['exit_code'],
                                                           'hold_seen': base['hold_seen'],
                                                           'command': base['command']},
                'base_checkpoint_state': base_state, 'base_counters': base_counters,
                'cases': results})
    print(json.dumps({case: {'resume_exit': results[case]['resume']['exit_code'],
                             'probe_exit': results[case]['probe']['exit_code'],
                             'zero_recomputation': results[case]['zero_recomputation'],
                             'files_unchanged': results[case]['checkpoint_files_unchanged'],
                             's30_invalid': results[case]['s30_invalid']}
                      for case in results}, ensure_ascii=False), flush=True)
    return 0 if all(results[c]['resume']['exit_code'] != 0
                    and results[c]['probe']['exit_code'] != 0
                    and results[c]['zero_recomputation']
                    and results[c]['checkpoint_files_unchanged']
                    and results[c]['s30_invalid'] for c in results) else 2


if __name__ == '__main__':
    sys.exit(main())
