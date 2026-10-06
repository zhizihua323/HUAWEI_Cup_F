"""TASK-Q01C-R1 independent verification of the recovery/log repair evidence.

Reads only saved artefacts: the synthetic interruption run, the R1 evidence files,
the frozen TASK-Q01C scientific run and the previous runs. It never imports the
pipeline module and never touches A1-A3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
FORMAL_RUN = SOLUTION / 'outputs' / 'quality_q01c' / '20260924T215718+08'
CST = timezone(timedelta(hours=8))
SMALL_LIMIT = 8 * 1024 * 1024
CHECKS = []
STAGES = ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2', 's12_scan_a3',
          's20_score_primary', 's30_sensitivity', 's40_summarize', 's50_verify', 's60_finalize']
CHECKPOINT_STAGES = ['s10_scan_a1', 's11_scan_a2', 's12_scan_a3', 's20_score_primary',
                     's30_sensitivity', 's40_summarize']
TERMINAL = ('complete', 'failed', 'gate_failed')
CODE_FILES = ['solution/src/quality_q01c.py', 'solution/src/quality_q01c_selftest.py',
              'solution/src/quality_q01c_verify.py', 'solution/tests/test_quality_q01c.py',
              'solution/tests/q01c_r1_fixture.py', 'solution/tests/q01c_r1_two_process.py',
              'solution/tests/q01c_r1_extension_isolation.py', 'solution/tests/q01c_r1_verify.py']


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


def check(check_id, description, status, actual, expected, evidence, note=''):
    CHECKS.append({'check_id': check_id, 'description': description, 'status': status,
                   'actual': actual, 'expected': expected, 'evidence': evidence, 'note': note})
    print(f'[r1-verify] {check_id}: {status}', flush=True)


def payload():
    n_fail = sum(1 for c in CHECKS if c['status'] == 'FAIL')
    n_nv = sum(1 for c in CHECKS if c['status'] == 'NOT_VERIFIABLE')
    n_nc = sum(1 for c in CHECKS if c['status'] == 'NOT_CHECKED')
    return {'summary': {'n_checks': len(CHECKS),
                        'n_pass': sum(1 for c in CHECKS if c['status'] == 'PASS'),
                        'n_fail': n_fail, 'n_not_checked': n_nc, 'n_not_verifiable': n_nv},
            'checks': CHECKS, 'status': 'PASS' if not n_fail else 'FAIL'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R1 independent verification')
    parser.add_argument('--r1-dir', required=True)
    args = parser.parse_args(argv)
    r1_dir = Path(args.r1_dir).resolve()
    evidence = read_json(r1_dir / 'resume_evidence.json')
    command_log = read_json(r1_dir / 'command_log.json')
    checkpoint_manifest = read_json(r1_dir / 'checkpoint_manifest.json')
    before = read_json(r1_dir / 'protected_artifacts_before.json')['entries']
    after = read_json(r1_dir / 'protected_artifacts_after.json')['entries']
    run_dir = Path(evidence['synthetic_run_dir'])
    run_summary = read_json(run_dir / 'run_summary.json')
    run_checks = read_json(run_dir / 'checks.json')
    status_records = [json.loads(line) for line in
                      (run_dir / 'stage_status.jsonl').read_text(encoding='utf-8').splitlines()
                      if line.strip()]
    processes = evidence['processes']
    p1_pid = processes['p1']['pid']
    p2_pid = processes['p2']['pid']
    check('R01_distinct_processes',
          'P1 and P2 executed in two distinct OS processes sharing one run directory',
          'PASS' if (p1_pid and p2_pid and p1_pid != p2_pid
                     and processes.get('same_run_dir') is True) else 'FAIL',
          {'p1_pid': p1_pid, 'p2_pid': p2_pid, 'harness_pid': os.getpid(),
           'same_run_dir': processes.get('same_run_dir')},
          {'p1_pid != p2_pid': True}, 'resume_evidence.json / termination_evidence.json')
    termination = read_json(r1_dir / 'interruption_run' / 'process_1' / 'termination_evidence.json')
    check('R02_p1_external_termination',
          'P1 was terminated by the supervisor after its first checkpoint marker appeared',
          'PASS' if (termination.get('hold_hook_seen') and termination.get('exit_code') is not None
                     and termination.get('last_valid_checkpoint', {}).get('payload_sha256')) else 'FAIL',
          {'hold_hook_seen': termination.get('hold_hook_seen'),
           'exit_code': termination.get('exit_code'),
           'last_valid_checkpoint': termination.get('last_valid_checkpoint')},
          {'hold_hook_seen': True}, 'interruption_run/process_1/termination_evidence.json')
    counters = evidence['scan_counters']
    new_passes = counters['new_passes_in_p2']
    a1_new_passes = int(new_passes.get('A1', -1))
    later_new_passes = {k: v for k, v in new_passes.items() if k != 'A1'}
    check('R03_no_rescan_of_completed_stage',
          'P2 added zero scan passes for the stage that P1 had already checkpointed; the two later '
          'files are scanned exactly once by P2 (they were never scanned by P1)',
          'PASS' if (a1_new_passes == 0
                     and counters['before_p2']['files'].get('A1', {}).get('passes') == 1
                     and counters['after_p2']['files'].get('A1', {}).get('passes') == 1
                     and all(int(v) == 1 for v in later_new_passes.values())
                     and len(later_new_passes) == 2) else 'FAIL',
          {'new_passes_in_p2': new_passes, 'a1_new_passes': a1_new_passes,
           'p1_scan_pid': counters['before_p2']['files'].get('A1', {}).get('last_scan_pid'),
           'before': {k: v.get('passes') for k, v in counters['before_p2']['files'].items()},
           'after': {k: v.get('passes') for k, v in counters['after_p2']['files'].items()},
           'reuse_events': len(counters.get('reuse_events', []))},
          {'A1 new passes in P2': 0, 'A2/A3 first scanned by P2': 1},
          'scan_counters.json (before/after P2); per-file semantics')
    invariance = evidence['checkpoints']
    check('R04_checkpoint_hash_invariant',
          'the P1 checkpoint payload/metadata/markers keep identical hashes across P2',
          'PASS' if invariance['hash_invariant'] else 'FAIL',
          {'before': invariance['hash_before_p2'], 'after': invariance['hash_after_p2']},
          {'identical': True}, 'checkpoint_manifest.json / resume_evidence.json')
    marker_ok = True
    marker_details = []
    for stage in CHECKPOINT_STAGES:
        payload_path = run_dir / 'checkpoints' / f'{stage}.payload.parquet'
        meta_path = run_dir / 'checkpoints' / f'{stage}.meta.json'
        checkpoint_path = run_dir / 'checkpoints' / f'{stage}.checkpoint.COMPLETE'
        stage_path = run_dir / 'checkpoints' / f'{stage}.stage.COMPLETE'
        entry = {'stage': stage, 'files_present': all(p.is_file() for p in
                                                     [payload_path, meta_path, checkpoint_path,
                                                      stage_path]),
                 'distinct_marker_names': checkpoint_path.name != stage_path.name}
        if entry['files_present']:
            meta = read_json(meta_path)
            marker = read_json(checkpoint_path)
            stage_marker = read_json(stage_path)
            entry.update({'payload_sha_matches': meta.get('payload_sha256') == sha256_file(payload_path),
                          'marker_binds_meta': marker.get('checkpoint_meta_sha256') == sha256_file(meta_path),
                          'checkpoint_kind': marker.get('kind'),
                          'stage_kind': stage_marker.get('kind'),
                          'stage': meta.get('stage'),
                          'input_sha256': bool(meta.get('input_sha256')),
                          'config_sha256': bool(meta.get('config_sha256')),
                          'code_fingerprint': bool(meta.get('code_fingerprint')),
                          'rows': meta.get('rows')})
            entry['ok'] = bool(entry['payload_sha_matches'] and entry['marker_binds_meta']
                               and entry['checkpoint_kind'] == 'checkpoint'
                               and entry['stage_kind'] == 'stage' and entry['stage'] == stage
                               and entry['input_sha256'] and entry['config_sha256']
                               and entry['code_fingerprint'] and entry['distinct_marker_names'])
        else:
            entry['ok'] = False
        marker_ok = marker_ok and entry['ok']
        marker_details.append(entry)
    check('R05_checkpoint_protocol',
          'v2 checkpoint marker and stage marker are separate files with a valid hash chain '
          '(including S20/S30/S40)',
          'PASS' if marker_ok else 'FAIL', {'details': marker_details}, {'all_ok': True},
          'independent re-hash of checkpoints/')
    started = {stage: any(r['stage'] == stage and r['event'] == 'start' for r in status_records)
               for stage in STAGES}
    terminal = {stage: [r['event'] for r in status_records
                        if r['stage'] == stage and r['event'] in TERMINAL] for stage in STAGES}
    check('R06_stage_event_completeness',
          'every stage of the synthetic run has a start event and exactly one terminal event',
          'PASS' if all(started.values()) and all(len(v) == 1 for v in terminal.values()) else 'FAIL',
          {'started': started, 'terminal': terminal}, {'all stages single terminal': True},
          'synthetic run stage_status.jsonl')
    stage_seconds = run_summary.get('stage_seconds', {})
    executed = run_summary.get('executed_stages', [])
    reused = run_summary.get('reused_stages', {})
    skipped = run_summary.get('skipped_stages', {})
    covered = [s for s in executed if s in stage_seconds]
    accounted = set(executed) | set(reused) | set(skipped)
    check('R07_stage_seconds_and_skips',
          'stage_seconds covers every executed stage; every stage is accounted for as executed, '
          'reused from a validated checkpoint, or explicitly SKIPPED',
          'PASS' if (len(covered) == len(executed)
                     and accounted >= set(STAGES) - {'s60_finalize'}
                     and all(isinstance(stage_seconds.get(s), dict)
                             and stage_seconds[s].get('status') == 'SKIPPED'
                             for s in skipped)) else 'FAIL',
          {'executed': executed, 'executed_with_seconds': covered, 'reused': sorted(reused),
           'skipped': skipped, 'stage_seconds_keys': list(stage_seconds)},
          {'executed covered; executed+reused+skipped == all stages': True},
          'synthetic run run_summary.json')
    roles = {c.get('role') for c in command_log.get('commands', [])}
    check('R08_command_log',
          'actual commands recorded for the harness, P1, P2, probe and stage demos',
          'PASS' if {'r1_harness', 'process_1', 'process_2', 'probe_process'} <= roles else 'FAIL',
          {'roles': sorted(roles)}, {'required roles': ['process_1', 'process_2', 'probe_process',
                                                       'r1_harness']},
          'command_log.json')
    check('R09_no_real_input_access',
          'the synthetic run and harness reference only fixture inputs (A1-A3 access counters are 0)',
          'PASS' if (evidence['a1_a3_access']['opened'] == 0
                     and evidence['a1_a3_access']['hashed'] == 0
                     and evidence['a1_a3_access']['decompressed'] == 0
                     and evidence['a1_a3_access']['stat_calls'] == 0
                     and read_json(run_dir / 'input_manifest.json')['mode'] == 'fixture') else 'FAIL',
          evidence['a1_a3_access'], {'all zero': True}, 'resume_evidence.json / input_manifest.json')
    fixture_checks = read_json(run_dir / 'checks.json')['summary']
    check('R10_fixture_run_checks',
          'the synthetic run finished with its own independent fixture verification at 0 FAIL',
          'PASS' if (fixture_checks['n_fail'] == 0 and fixture_checks['n_not_checked'] == 0
                     and run_summary['status'] == 'COMPLETE_PENDING_REVIEW') else 'FAIL',
          {'fixture_checks': fixture_checks, 'status': run_summary['status']},
          {'n_fail': 0, 'status': 'COMPLETE_PENDING_REVIEW'}, 'synthetic run checks.json')
    manifest_path = run_dir / 'output_manifest.json'
    manifest = read_json(manifest_path)
    mismatches = []
    for item in manifest['files']:
        target = run_dir / item['path']
        if not target.is_file() or sha256_file(target) != item['sha256']:
            mismatches.append(item['path'])
    check('R11_synthetic_manifest',
          'the synthetic run manifest is internally consistent after finalize',
          'PASS' if not mismatches else 'FAIL',
          {'files': manifest['n_files'], 'mismatches': mismatches[:5]},
          {'mismatches': []}, 'interruption_run/synthetic_run/output_manifest.json')
    isolation_path = r1_dir / 'extension_isolation_test.json'
    isolation = read_json(isolation_path) if isolation_path.is_file() else {}
    check('R12_extension_isolation',
          'extension-role mutation leaves the calibration parameter set bit-identical and the gate '
          'still hard-stops',
          'PASS' if (isolation.get('status') == 'PASS'
                     and isolation.get('calibration_parameters_identical_after_every_mutation')
                     and isolation.get('parameters_sourced_from_calibration_only')
                     and isolation.get('gate_failure_hard_stop')) else 'FAIL',
          {'status': isolation.get('status'),
           'identical': isolation.get('calibration_parameters_identical_after_every_mutation'),
           'provenance': isolation.get('parameters_sourced_from_calibration_only'),
           'hard_stop': isolation.get('gate_failure_hard_stop'),
           'role_counts': isolation.get('role_row_counts')},
          {'status': 'PASS'}, 'extension_isolation_test.json')
    demo = read_json(r1_dir / 'interruption_run' / 'stage_scope_demo.json')
    check('R13_stage_scope_behaviour',
          '--stage refuses to run without prerequisites and executes only the selected stage',
          'PASS' if (demo['missing_prerequisite_run']['exit_code'] == 6
                     and demo['missing_prerequisite_run']['missing_prerequisites']
                     and all(r['exit_code'] == 0 for r in demo['single_stage_runs'])
                     and demo['single_stage_runs'][0]['executed_stages'] == ['s00_preflight']
                     and demo['single_stage_runs'][1]['executed_stages'] == ['s01_synthetic_tests']
                     and 's00_preflight' in (demo['single_stage_runs'][1]['reused_stages'] or {})
                     and demo['single_stage_runs'][2]['executed_stages'] == ['s10_scan_a1']
                     and {'s00_preflight', 's01_synthetic_tests'} <=
                     set(demo['single_stage_runs'][2]['reused_stages'] or {})
                     and demo['single_stage_runs'][0]['skipped_stages']) else 'FAIL',
          {'missing_prereq': demo['missing_prerequisite_run'],
           'single_stage_runs': demo['single_stage_runs']},
          {'missing_prereq exit 6, single stage scope limited': True},
          'interruption_run/stage_scope_demo.json')
    probe = evidence['processes']['probe']
    check('R14_probe_behaviour',
          '--probe-resume produced a read-only eligibility report naming the reusable stages',
          'PASS' if (probe['exit_code'] == 0
                     and {'s00_preflight', 's01_synthetic_tests', 's10_scan_a1'} <=
                     set(probe['reused_stages'])) else 'FAIL',
          {'exit_code': probe['exit_code'], 'reused_stages': probe['reused_stages']},
          {'reused includes s00/s01/s10': True}, 'interruption_run/process_probe/')
    formal_manifest = read_json(FORMAL_RUN / 'output_manifest.json')
    formal_mismatch = []
    for item in formal_manifest['files']:
        target = FORMAL_RUN / item['path']
        if not target.is_file() or sha256_file(target) != item['sha256']:
            formal_mismatch.append(item['path'])
    formal_summary = read_json(FORMAL_RUN / 'run_summary.json')
    formal_checks = read_json(FORMAL_RUN / 'checks.json')['summary']
    check('R15_formal_run_manifest',
          'the frozen TASK-Q01C run still matches its own 56-entry manifest',
          'PASS' if (len(formal_manifest['files']) == 56 and not formal_mismatch) else 'FAIL',
          {'n_files': len(formal_manifest['files']), 'mismatches': formal_mismatch[:5],
           'status': formal_summary.get('status'), 'checks': formal_checks},
          {'n_files': 56, 'mismatches': [], 'status': 'COMPLETE_PENDING_REVIEW',
           'checks': {'n_fail': 0}},
          'solution/outputs/quality_q01c/20260924T215718+08/')
    changed = []
    added = []
    removed = []
    for rel, entry_before in before.items():
        entry_after = after.get(rel)
        if entry_after is None:
            removed.append(rel)
        elif (entry_before['bytes'] != entry_after['bytes']
              or abs(entry_before['mtime'] - entry_after['mtime']) > 1e-6
              or (entry_before.get('sha256') and entry_before['sha256'] != entry_after.get('sha256'))):
            changed.append(rel)
    for rel in after:
        if rel not in before:
            added.append(rel)
    check('R16_protected_runs_unchanged',
          'the formal run, the seven earlier runs, old quality outputs and Q01A/R1 evidence are '
          'byte-identical before and after R1',
          'PASS' if not changed and not removed and not added else 'FAIL',
          {'changed': changed[:5], 'removed': removed[:5], 'added': added[:5],
           'n_files_compared': len(before), 'hash_scope': 'sha256 for files <= 8 MiB; size+mtime for all'},
          {'changed': [], 'removed': [], 'added': []},
          'protected_artifacts_before.json vs protected_artifacts_after.json')
    run_status = payload()
    verification = {'run_id': r1_dir.name, 'task': 'TASK-Q01C-R1', 'generated_local': now_iso(),
                    'summary': run_status['summary'], 'checks': run_status['checks'],
                    'independent_of_pipeline_module': True,
                    'key_metrics': {'p1_pid': p1_pid, 'p2_pid': p2_pid,
                                    'new_passes_in_p2_total': int(counters['new_passes_in_p2_total']),
                                    'checkpoint_hash_invariant': invariance['hash_invariant'],
                                    'synthetic_run_status': run_summary['status'],
                                    'formal_run_files_matching': len(formal_manifest['files'])
                                                                - len(formal_mismatch),
                                    'formal_run_files_total': len(formal_manifest['files'])}}
    (r1_dir / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2,
                                                         allow_nan=False), encoding='utf-8')
    (r1_dir / 'checks.json').write_text(json.dumps({'run_id': r1_dir.name, 'task': 'TASK-Q01C-R1',
                                                    'generated_local': now_iso(), **run_status},
                                                   ensure_ascii=False, indent=2, allow_nan=False),
                                        encoding='utf-8')
    print('[r1-verify] summary: ' + json.dumps(run_status['summary'], ensure_ascii=False), flush=True)
    return 0 if run_status['summary']['n_fail'] == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
