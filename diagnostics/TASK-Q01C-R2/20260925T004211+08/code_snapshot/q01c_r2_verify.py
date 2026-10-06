"""TASK-Q01C-R2 independent verification (no import of the production module)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
FORMAL_RUN = SOLUTION / 'outputs' / 'quality_q01c' / '20260924T215718+08'
R1_RUN = PROJECT / 'diagnostics' / 'TASK-Q01C-R1' / '20260924T225550+08'
CST = timezone(timedelta(hours=8))
SMALL_LIMIT = 8 * 1024 * 1024
STAGES = ['s00_preflight', 's01_synthetic_tests', 's10_scan_a1', 's11_scan_a2', 's12_scan_a3',
          's20_score_primary', 's30_sensitivity', 's40_summarize', 's50_verify', 's60_finalize']
CHECKPOINT_STAGES = ['s10_scan_a1', 's11_scan_a2', 's12_scan_a3', 's20_score_primary',
                     's30_sensitivity', 's40_summarize']
TERMINAL = ('complete', 'failed', 'gate_failed')
CHECKS = []


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


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def check(check_id, description, status, actual, expected, evidence, note=''):
    CHECKS.append({'check_id': check_id, 'description': description, 'status': status,
                   'actual': actual, 'expected': expected, 'evidence': evidence, 'note': note})
    print('[r2-verify] ' + check_id + ': ' + status, flush=True)


def payload():
    n_fail = sum(1 for c in CHECKS if c['status'] == 'FAIL')
    return {'summary': {'n_checks': len(CHECKS),
                        'n_pass': sum(1 for c in CHECKS if c['status'] == 'PASS'),
                        'n_fail': n_fail,
                        'n_not_checked': sum(1 for c in CHECKS if c['status'] == 'NOT_CHECKED'),
                        'n_not_verifiable': sum(1 for c in CHECKS
                                                if c['status'] == 'NOT_VERIFIABLE')},
            'checks': CHECKS, 'status': 'PASS' if not n_fail else 'FAIL'}


def stage_events(run_dir):
    path = run_dir / 'stage_status.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def identity_of(run_dir, stage):
    meta_path = run_dir / 'checkpoints' / (stage + '.meta.json')
    meta = read_json(meta_path)
    identity = {'stage': stage, 'protocol_version': meta.get('protocol_version'),
                'checkpoint_protocol': meta.get('checkpoint_protocol'),
                'payload_sha256': meta.get('payload_sha256'), 'meta_sha256': sha256_file(meta_path),
                'rows': meta.get('rows'), 'input_sha256': meta.get('input_sha256')}
    return hashlib.sha256(compact(identity).encode('utf-8')).hexdigest(), identity


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R2 independent verification')
    parser.add_argument('--r2-dir', required=True)
    args = parser.parse_args(argv)
    r2_dir = Path(args.r2_dir).resolve()
    evidence = read_json(r2_dir / 'resume_evidence.json')
    rejections = read_json(r2_dir / 'rejection_tests' / 'rejection_summary.json')
    run_dir = Path(evidence['synthetic_run_dir'])
    run_summary = read_json(run_dir / 'run_summary.json')
    events = stage_events(run_dir)
    processes = evidence['processes']
    check('R01_distinct_processes',
          'mid-stage P1/P2 run in two distinct OS processes on one run directory',
          'PASS' if processes['p1']['pid'] and processes['p2']['pid']
          and processes['p1']['pid'] != processes['p2']['pid'] and processes['distinct_pids'] else 'FAIL',
          {'p1_pid': processes['p1']['pid'], 'p2_pid': processes['p2']['pid']},
          {'distinct': True}, 'resume_evidence.json / stage_status.jsonl')
    check('R02_p1_external_termination',
          'P1 was externally terminated after the S30 checkpoint marker was complete',
          'PASS' if processes['p1']['hold_hook_seen'] and processes['p1']['exit_code'] is not None
          and processes['p1']['hold_after_stage'] == 's30_sensitivity' else 'FAIL',
          {'hold': processes['p1']['hold_after_stage'], 'exit_code': processes['p1']['exit_code']},
          {'hold_after_stage': 's30_sensitivity'}, 'interruption evidence')
    new_computations = evidence['stage_compute_counters']['new_computations_in_p2']
    check('R03_zero_recomputation_midstage',
          'P2 added zero computations for every checkpoint completed by P1 (s10..s30)',
          'PASS' if all(int(v) == 0 for v in new_computations.values())
          and len(new_computations) >= 5 else 'FAIL',
          {'new_computations': new_computations}, {'all zero': True}, 'stage_compute_counters.json')
    check('R04_checkpoint_hash_invariant',
          'payload/meta/marker hashes of every completed checkpoint are identical before and after P2',
          'PASS' if evidence['checkpoints']['hash_invariant'] else 'FAIL',
          {'stages': evidence['checkpoints']['stages']}, {'invariant': True},
          'checkpoint_manifest.json')
    source = (SOLUTION / 'src' / 'quality_q01c.py').read_text(encoding='utf-8')
    flows = {'main_loop': 'report = validate_stage(ctx, name,' in source,
             'stage_prerequisites': 'report = validate_stage(ctx, dependency,' in source,
             'probe_resume': 'report = validate_stage(ctx, stage,' in source}
    probe_report = processes['probe']['report'] or {}
    check('R05_unified_validation_entry',
          'the three CLI flows call the single stage reuse validation entry and the probe reports '
          'the same structured verdict schema',
          'PASS' if all(flows.values()) and probe_report.get('verdict_counts') else 'FAIL',
          {'flows': flows, 'probe_verdict_counts': probe_report.get('verdict_counts'),
           'validation_schema_version': probe_report.get('validation_schema_version')},
          {'all three flows call validate_stage': True}, 'quality_q01c.py static check + probe report')
    rejection_ok = True
    rejection_details = {}
    for case, item in rejections['cases'].items():
        reason_json = json.dumps(item['probe_invalid_stages'])
        case_ok = (item['resume']['exit_code'] != 0 and item['probe']['exit_code'] != 0
                   and item['zero_recomputation'] and item['checkpoint_files_unchanged']
                   and item['s30_invalid'] and item['expected_failed_check'] in reason_json
                   and item['probe_vs_resume_consistent'])
        rejection_ok = rejection_ok and case_ok
        rejection_details[case] = {'resume_exit': item['resume']['exit_code'],
                                   'probe_exit': item['probe']['exit_code'],
                                   'zero_recomputation': item['zero_recomputation'],
                                   'files_unchanged': item['checkpoint_files_unchanged'],
                                   'expected_failed_check': item['expected_failed_check'],
                                   'probe_invalid_reason': item['probe_invalid_stages']}
    check('R06_three_rejection_paths',
          'payload / config / code-fingerprint damage each hard-stops through the normal --resume CLI '
          'with zero recomputation and no overwrite',
          'PASS' if rejection_ok else 'FAIL', rejection_details, {'all three cases hard stop': True},
          'rejection_summary.json')
    chain_ok = True
    chain_details = []
    for stage in CHECKPOINT_STAGES:
        base = run_dir / 'checkpoints' / stage
        payload_path = Path(str(base) + '.payload.parquet')
        meta_path = Path(str(base) + '.meta.json')
        cp_marker = Path(str(base) + '.checkpoint.COMPLETE')
        stage_marker = Path(str(base) + '.stage.COMPLETE')
        entry = {'stage': stage, 'files': all(p.is_file() for p in
                                              (payload_path, meta_path, cp_marker, stage_marker))}
        if entry['files']:
            meta = read_json(meta_path)
            marker = read_json(cp_marker)
            stage_payload = read_json(stage_marker)
            bound = stage_payload.get('outputs') or {}
            entry.update({'payload_sha': meta.get('payload_sha256') == sha256_file(payload_path),
                          'marker_binds_meta': marker.get('checkpoint_meta_sha256') == sha256_file(meta_path),
                          'stage_kind': stage_payload.get('kind'),
                          'stage_binds_global_parquet': any(
                              str(rel).endswith('quality_features_scores.parquet') for rel in bound),
                          'stage_outputs_hash_match': all(
                              (run_dir / rel).is_file() and sha256_file(run_dir / rel) == expected
                              for rel, expected in bound.items()),
                          'checkpoint_identity_recorded': stage_payload.get('checkpoint_identity')
                          == identity_of(run_dir, stage)[0] if stage != 's40_summarize' else True})
            entry['ok'] = (entry['payload_sha'] and entry['marker_binds_meta']
                           and entry['stage_kind'] == 'stage'
                           and not entry['stage_binds_global_parquet']
                           and entry['stage_outputs_hash_match'])
        else:
            entry['ok'] = False
        chain_ok = chain_ok and entry['ok']
        chain_details.append(entry)
    check('R07_marker_chain_and_stage_scope',
          'every checkpoint re-hashes cleanly and stage markers bind only stage-local immutable outputs',
          'PASS' if chain_ok else 'FAIL', {'details': chain_details}, {'all_ok': True},
          'independent re-hash of checkpoints/')
    s20_identity = identity_of(run_dir, 's20_score_primary')[0]
    chain_identity = hashlib.sha256(compact([identity_of(run_dir, s)[1] for s in
                                             ['s10_scan_a1', 's11_scan_a2',
                                              's12_scan_a3']]).encode('utf-8')).hexdigest()
    s30_meta = read_json(run_dir / 'checkpoints' / 's30_sensitivity.meta.json')
    s40_meta = read_json(run_dir / 'checkpoints' / 's40_summarize.meta.json')
    s20_meta = read_json(run_dir / 'checkpoints' / 's20_score_primary.meta.json')
    binding_ok = (s20_meta.get('input_sha256') == chain_identity
                  and s30_meta.get('input_sha256') == s20_identity
                  and s40_meta.get('input_sha256') == identity_of(run_dir, 's30_sensitivity')[0])
    check('R08_immutable_input_bindings',
          'S20 binds the validated S10/S11/S12 chain; S30 binds S20; S40 binds S30 (independently recomputed)',
          'PASS' if binding_ok else 'FAIL',
          {'s20_binding_matches_chain': s20_meta.get('input_sha256') == chain_identity,
           's30_binding_matches_s20': s30_meta.get('input_sha256') == s20_identity,
           's40_binding_matches_s30': s40_meta.get('input_sha256')
           == identity_of(run_dir, 's30_sensitivity')[0]},
          {'all bindings match': True}, 'checkpoint metadata vs independent identity recomputation')
    seconds = run_summary.get('stage_seconds', {})
    executed = run_summary.get('executed_stages', [])
    terminals = run_summary.get('stage_terminal_events', {})
    exit_codes = run_summary.get('stage_exit_codes', {})
    s60_events = [event['event'] for event in events if event.get('stage') == 's60_finalize']
    s60_terminal = [event for event in s60_events if event in TERMINAL]
    verifier_source = Path(__file__).read_text(encoding='utf-8')
    exclusion_fragments = [['STAGES', ' - {'], ['s60', '_finalize', "'}"],
                           ['not in', ' s50_verify']]
    exclusion_patterns = [''.join(fragments) for fragments in exclusion_fragments
                          if ''.join(fragments) in verifier_source]
    check('R09_s60_closure',
          'S60 appears in stage_seconds / executed_stages / terminal events / exit codes with a unique '
          'terminal and the verifier contains no S60 exclusion',
          'PASS' if (isinstance(seconds.get('s60_finalize'), (int, float))
                     and seconds['s60_finalize'] >= 0 and 's60_finalize' in executed
                     and len(terminals.get('s60_finalize', [])) == 1
                     and exit_codes.get('s60_finalize') == 0 and s60_events.count('start') >= 1
                     and len(s60_terminal) == 1 and not exclusion_patterns) else 'FAIL',
          {'stage_seconds': seconds.get('s60_finalize'), 'in_executed': 's60_finalize' in executed,
           'terminal': terminals.get('s60_finalize'), 'exit_code': exit_codes.get('s60_finalize'),
           'status_events': s60_events, 'exclusion_patterns': exclusion_patterns},
          {'unique terminal, non-negative duration, exit 0, no exclusion': True},
          'synthetic run run_summary.json / stage_status.jsonl / verifier source')
    manifest = read_json(run_dir / 'output_manifest.json')
    manifest_mismatch = [item['path'] for item in manifest['files']
                         if not (run_dir / item['path']).is_file()
                         or sha256_file(run_dir / item['path']) != item['sha256']]
    manifest_mtime = (run_dir / 'output_manifest.json').stat().st_mtime
    after_writes = [item['path'] for item in manifest['files']
                    if item['path'] != 'output_manifest.json'
                    and (run_dir / item['path']).stat().st_mtime > manifest_mtime + 1e-6]
    check('R10_manifest_closure',
          'the finished run manifest matches every file and nothing was written after it',
          'PASS' if not manifest_mismatch and not after_writes else 'FAIL',
          {'files': manifest['n_files'], 'mismatches': manifest_mismatch,
           'written_after_manifest': after_writes}, {'none': True},
          'synthetic run output_manifest.json')
    formal_manifest = read_json(FORMAL_RUN / 'output_manifest.json')
    formal_mismatch = [item['path'] for item in formal_manifest['files']
                       if not (FORMAL_RUN / item['path']).is_file()
                       or sha256_file(FORMAL_RUN / item['path']) != item['sha256']]
    r1_manifest = read_json(R1_RUN / 'output_manifest.json')
    r1_mismatch = [item['path'] for item in r1_manifest['files']
                   if not (R1_RUN / item['path']).is_file()
                   or sha256_file(R1_RUN / item['path']) != item['sha256']]
    before = read_json(r2_dir / 'protected_artifacts_before.json')['entries']
    after = read_json(r2_dir / 'protected_artifacts_after.json')['entries'] if (
        r2_dir / 'protected_artifacts_after.json').is_file() else {}
    changed = [rel for rel, entry in before.items()
               if rel in after and (entry['bytes'] != after[rel]['bytes']
                                    or abs(entry['mtime'] - after[rel]['mtime']) > 1e-6
                                    or (entry.get('sha256') and entry['sha256'] != after[rel].get('sha256')))]
    check('R11_regression_protection',
          'formal Q01C run 56/56, R1 run manifest, previous runs and old quality outputs unchanged',
          'PASS' if (len(formal_manifest['files']) == 56 and not formal_mismatch
                     and len(r1_manifest['files']) == 138 and not r1_mismatch
                     and not changed) else 'FAIL',
          {'formal_files': len(formal_manifest['files']), 'formal_mismatch': formal_mismatch[:5],
           'r1_files': len(r1_manifest['files']), 'r1_mismatch': r1_mismatch[:5],
           'snapshot_changed': changed[:5]}, {'all unchanged': True},
          'output manifests + protected_artifacts snapshots')
    snapshot_dir = r2_dir / 'code_snapshot'
    snapshot_mismatch = []
    for path in sorted(p for p in snapshot_dir.glob('*.py') if p.is_file()):
        matches = list((SOLUTION / 'src').glob(path.name)) + list((SOLUTION / 'tests').glob(path.name))
        if matches and sha256_file(matches[0]) != sha256_file(path):
            snapshot_mismatch.append(path.name)
    check('R12_code_snapshot_consistency',
          'the R2 code snapshot is byte-identical to the executed sources',
          'PASS' if not snapshot_mismatch else 'FAIL',
          {'snapshot_files': len(list(snapshot_dir.glob('*.py'))), 'mismatches': snapshot_mismatch},
          {'mismatches': []}, 'code_snapshot/ vs solution src/tests')
    real_hits = []
    path_token = 'real_' + 'attachments'
    access_tokens = ['open(', 'sha256_file(', 'stat(', 'read_bytes', 'is_file()']
    for script in sorted((SOLUTION / 'tests').glob('q01c_r2_*.py')):
        text = script.read_text(encoding='utf-8')
        for number, line in enumerate(text.splitlines(), 1):
            if path_token in line and any(token in line for token in access_tokens):
                real_hits.append(script.name + ':' + str(number) + ': ' + line.strip()[:80])
    input_manifest = read_json(run_dir / 'input_manifest.json')
    check('R13_no_real_input_access',
          'no R2 dynamic path references a real attachment; the synthetic run is fixture-only',
          'PASS' if not real_hits and input_manifest.get('mode') == 'fixture' else 'FAIL',
          {'dynamic_real_path_hits': real_hits, 'fixture_mode': input_manifest.get('mode'),
           'declared_access': evidence['a1_a3_access']},
          {'no real path references; declared access counters 0': True},
          'static scan + synthetic run input_manifest.json')
    report = payload()
    verification = {'run_id': r2_dir.name, 'task': 'TASK-Q01C-R2', 'generated_local': now_iso(),
                    'summary': report['summary'], 'checks': report['checks'],
                    'independent_of_pipeline_module': True,
                    'key_metrics': {'p1_pid': processes['p1']['pid'], 'p2_pid': processes['p2']['pid'],
                                    'new_computations_in_p2': new_computations,
                                    'checkpoint_hash_invariant': evidence['checkpoints']['hash_invariant'],
                                    'rejection_cases': {case: item['resume']['exit_code']
                                                        for case, item in rejections['cases'].items()},
                                    's60_duration_s': seconds.get('s60_finalize'),
                                    'formal_run_files_matching': len(formal_manifest['files'])
                                                                - len(formal_mismatch),
                                    'r1_files_matching': len(r1_manifest['files']) - len(r1_mismatch)}}
    (r2_dir / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2,
                                                         allow_nan=False), encoding='utf-8')
    (r2_dir / 'checks.json').write_text(json.dumps({'run_id': r2_dir.name, 'task': 'TASK-Q01C-R2',
                                                    'generated_local': now_iso(), **report},
                                                   ensure_ascii=False, indent=2, allow_nan=False),
                                        encoding='utf-8')
    print('[r2-verify] summary: ' + json.dumps(report['summary'], ensure_ascii=False), flush=True)
    return 0 if report['summary']['n_fail'] == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
