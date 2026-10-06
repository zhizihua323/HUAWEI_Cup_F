#!/usr/bin/env python
"""Independent verifier for TASK-G1 stage-1. This module does not import the executor."""
from __future__ import annotations
import argparse, hashlib, json, lzma, math, re, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ACTIVE = {'c4', 'commoncrawl', 'wikipedia'}
SCOPES = ['A1_sample', 'A2_extension', 'A3_extension', 'extension_overlap', 'extension_new', 'all_unique']
AUTHORS = ['readability_1to5', 'completeness_1to5', 'contamination_0to2', 'overall_quality_1to5', 'review_notes_optional']

def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def masks(df):
    return {'A1_sample': (df.file_id == 'A1') & df.is_unique_first,
            'A2_extension': df.file_id == 'A2_arxiv',
            'A3_extension': df.file_id == 'A3_github',
            'extension_overlap': df.overlap_a1,
            'extension_new': (df.evaluation_role == 'extension_new_records') & df.is_unique_first,
            'all_unique': df.is_unique_first}

def redact_text(text: str):
    out = text.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '')
    out = re.sub(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL_REDACTED]', out)
    out = re.sub(r'(?i)\bhttps?://[^\s<>"\']+', '[URL_REDACTED]', out)
    out = re.sub(r'(?i)\bwww\.[^\s<>"\']+', '[URL_REDACTED]', out)
    return out

def item(name, passed, details):
    return {'check': name, 'status': 'PASS' if passed else 'FAIL', 'details': details}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    args = ap.parse_args()
    rd = Path(args.run_dir).resolve()
    inputs = json.loads((rd / 'input_manifest.json').read_text(encoding='utf-8'))
    entries = {e['path']: e for e in inputs['inputs']}
    root = rd.parents[2]
    checks = []
    expected_hashes = {}
    # Recompute every declared input hash independently.
    hash_fail = []
    for rel, e in entries.items():
        p = root / rel
        got = sha_file(p)
        expected_hashes[rel] = got
        if got != e['sha256'] or p.stat().st_size != e['bytes']:
            hash_fail.append({'path': rel, 'expected': e['sha256'], 'got': got})
    checks.append(item('declared_input_hashes_match', not hash_fail, hash_fail))

    qp = root / 'solution/outputs/quality_q01c/20260924T215718+08/quality_features_scores.parquet'
    cols = ['key_sha256', 'file_id', 'is_unique_first', 'overlap_a1', 'evaluation_role', 'domain', 'Q_valid', 'Q_baseline', 'rater_disagreement_range', 'rater_disagreement_std']
    df = pd.read_parquet(qp, columns=cols)
    m = masks(df)
    counts = {s: {'physical': int(m[s].sum()), 'unique': int(df.loc[m[s], 'key_sha256'].nunique()),
                  'q_valid': int((df.loc[m[s], 'Q_valid'] & df.loc[m[s], 'Q_baseline'].notna()).sum())} for s in SCOPES}
    expected_counts = {
        'A1_sample': (51230, 51230, 51212), 'A2_extension': (17523, 17523, 17523),
        'A3_extension': (203752, 203752, 203752), 'extension_overlap': (11419, 11419, 11419),
        'extension_new': (209856, 209856, 209855), 'all_unique': (261086, 261086, 261067)}
    checks.append(item('independent_scope_denominators', all((counts[s]['physical'], counts[s]['unique'], counts[s]['q_valid']) == expected_counts[s] for s in SCOPES), {'actual': counts, 'expected': expected_counts}))
    overlap_q = set(df.loc[m['extension_overlap'], 'key_sha256'])
    ext_path = root / 'diagnostics/TASK-T03E/20260925T020032+08/phase_b_frozen_validation/extension_overlap_validation.csv'
    overlap_t = set(pd.read_csv(ext_path).key_sha256.astype(str))
    checks.append(item('overlap_keys_match_T03E', len(overlap_q) == 11419 and overlap_q == overlap_t, {'q01c': len(overlap_q), 't03e': len(overlap_t), 'intersection': len(overlap_q & overlap_t)}))
    checks.append(item('Q_invalid_19_preserved', int((~df.Q_valid).sum()) == 19 and int((~df.loc[df.is_unique_first, 'Q_valid']).sum()) == 19, {'physical': int((~df.Q_valid).sum()), 'unique': int((~df.loc[df.is_unique_first, 'Q_valid']).sum())}))
    qcode = (root / 'solution/outputs/quality_q01c/20260924T215718+08/code_snapshot/quality_q01c.py').read_text(encoding='utf-8')
    threshold = float(re.search(r'boolean_defined\s*=\s*ranges\s*>\s*([0-9.]+)', qcode).group(1))
    checks.append(item('high_conflict_threshold_from_frozen_code', threshold == 0.5, {'threshold': threshold}))

    den = pd.read_csv(rd / 'scope_denominators.csv')
    den_ok = set(den.scope) == set(SCOPES)
    for _, r in den.iterrows():
        c = counts[r.scope]
        den_ok = den_ok and int(r.physical_rows) == c['physical'] and int(r.unique_keys) == c['unique'] and int(r.Q_valid) == c['q_valid']
    checks.append(item('executor_scope_denominators_match_independent_recount', den_ok, {'file': den[['scope','physical_rows','unique_keys','Q_valid','Q_missing']].to_dict(orient='records')}))

    seal = json.loads((rd / 'sampling_seal.json').read_text(encoding='utf-8'))
    blind = pd.read_csv(rd / 'manual_text_review_blind.csv', dtype={'review_id': str})
    keydf = pd.read_csv(rd / 'manual_review_key.csv', dtype={'review_id': str})
    seal_ids = [r['review_id'] for r in seal['records']]
    expected_cols = ['review_id', 'text_redacted'] + AUTHORS
    forbidden = [c for c in blind.columns if any(t in c.lower() for t in ['q_baseline','conflict','group_','key_sha256','domain'])]
    checks.append(item('blind_schema_exact_no_leakage', list(blind.columns) == expected_cols and not forbidden, {'columns': list(blind.columns), 'forbidden': forbidden}))
    checks.append(item('blind_sample_size', 48 <= len(blind) <= 60 and len(blind) == len(seal_ids), {'n': len(blind), 'seal_n': len(seal_ids)}))
    checks.append(item('review_ids_unique_and_sealed', list(blind.review_id) == seal_ids and blind.review_id.is_unique and keydf.review_id.is_unique, {'blind': len(blind), 'key': len(keydf)}))
    checks.append(item('author_columns_blank', int(blind[AUTHORS].notna().sum().sum()) == 0, {'nonblank': int(blind[AUTHORS].notna().sum().sum())}))
    dc = Counter(seal['domain_counts'])
    checks.append(item('domain_coverage_and_cap', len(dc) >= 6 and max(dc.values()) <= math.floor(0.2 * len(blind)), {'domain_counts': dict(dc), 'cap': math.floor(0.2 * len(blind))}))
    checks.append(item('quota_targets_sealed', all(v['target'] == v['selected'] for v in seal['quota_report'].values()), seal['quota_report']))
    checks.append(item('seal_precedes_blind_and_no_completed_ratings', (rd / 'sampling_seal.json').stat().st_mtime <= (rd / 'manual_text_review_blind.csv').stat().st_mtime and not (rd / 'manual_text_review_completed.csv').exists(), {'seal_mtime': (rd/'sampling_seal.json').stat().st_mtime, 'blind_mtime': (rd/'manual_text_review_blind.csv').stat().st_mtime, 'completed_exists': (rd/'manual_text_review_completed.csv').exists()}))

    selected = {r['key_sha256']: r for r in seal['records']}
    blind_by_id = {r.review_id: r for r in blind.itertuples(index=False)}
    reconstructed = {}
    source = root / seal['text_source']
    with lzma.open(source, 'rt', encoding='utf-8') as f:
        for line in f:
            x = json.loads(line)
            key = sha_text(json.dumps((str(x.get('id','')), str(x.get('sub_path',''))), ensure_ascii=False, separators=(',', ':')))
            if key in selected:
                text = x.get('content')
                reconstructed[key] = text
    text_fail = []
    for key, rec in selected.items():
        if key not in reconstructed:
            text_fail.append({'key': key, 'reason': 'missing_source_text'}); continue
        original = reconstructed[key]
        redacted = redact_text(original)
        if sha_text(original) != rec['original_text_sha256'] or sha_text(redacted) != rec['redacted_text_sha256']:
            text_fail.append({'key': key, 'reason': 'hash_mismatch'})
        if blind_by_id[rec['review_id']].text_redacted != redacted:
            text_fail.append({'key': key, 'reason': 'blind_text_mismatch'})
    checks.append(item('blind_text_reconstructs_from_frozen_A1_source', not text_fail, text_fail[:10]))
    checks.append(item('manual_review_key_has_no_rating_columns', not any(c in keydf.columns for c in AUTHORS), {'columns': list(keydf.columns)}))

    audit = pd.read_csv(rd / 'text_join_audit.csv')
    selected_audit = audit[audit.candidate_id.eq('Q01C_A1_raw_source')]
    a18_audit = audit[audit.candidate_id.eq('A18_regmix_domain_sample')]
    checks.append(item('text_join_audit_records_direct_A1_and_A18_boundary',
                       len(selected_audit) == 1 and selected_audit.iloc[0].join_status == 'SELECTED_ONE_TO_ONE' and
                       len(a18_audit) == 1 and a18_audit.iloc[0].join_status == 'TEXT_JOINABLE_NOT_SELECTED',
                       {'selected': selected_audit.to_dict(orient='records'), 'a18': a18_audit.to_dict(orient='records')}))

    before = json.loads((rd / 'protected_before.json').read_text(encoding='utf-8'))
    after = json.loads((rd / 'protected_after.json').read_text(encoding='utf-8'))
    checks.append(item('Q01C_T03E_00_05_paper_hashes_unchanged', before == after, {'groups_equal': {k: before.get(k) == after.get(k) for k in before}}))

    required = ['run_summary.json','environment.json','input_manifest.json','command_log.json','stage_status.jsonl',
                'scope_denominators.csv','conflict_stability_summary.csv','conflict_by_domain.csv',
                'overlap_new_comparison.csv','distribution_distances.csv','bootstrap_stability.csv',
                'text_join_audit.csv','sampling_seal.json','manual_text_review_blind.csv',
                'manual_review_key.csv','manual_review_instructions.md','handoff.md','code/g1_gap_closure.py','code/verify_g1.py']
    # run_summary, command_log, handoff are intentionally written after verification; check only pre-verification artifacts.
    pre = [p for p in required if p not in {'run_summary.json','command_log.json','handoff.md'}]
    missing = [p for p in pre if not (rd / p).exists()]
    checks.append(item('required_preverification_artifacts_present', not missing, {'missing': missing, 'not_yet_expected': ['checks.json','verification.json','run_summary.json','command_log.json','handoff.md','output_manifest.json']}))

    summary = {'total': len(checks), 'pass': sum(c['status'] == 'PASS' for c in checks),
               'fail': sum(c['status'] == 'FAIL' for c in checks)}
    payload = {'run_id': rd.name, 'generated_local': __import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds'),
               'status': 'PASS' if summary['fail'] == 0 else 'FAIL', 'summary': summary,
               'verifier_imports_executor': False, 'checks': checks,
               'independent_recounts': counts, 'high_conflict_threshold': threshold,
               'expected_input_hashes': expected_hashes,
               'note': 'Verifier ran before output_manifest.json by design.'}
    (rd / 'verification.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': payload['status'], 'checks': summary}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
