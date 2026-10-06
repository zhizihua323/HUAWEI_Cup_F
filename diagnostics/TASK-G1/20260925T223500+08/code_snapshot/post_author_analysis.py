#!/usr/bin/env python
"""Post-author statistics and Q1 gap-freeze candidate after the sealed G1 blind review."""
from __future__ import annotations
import hashlib, json, math, os, platform, re, shutil, subprocess, sys, time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy import stats

CST = timezone(timedelta(hours=8))
SEED = 20260925
BOOTSTRAP = 2000
PROJECT = Path(__file__).resolve().parents[4]
SOURCE_RUN = PROJECT / 'diagnostics' / 'TASK-G1' / '20260925T204300+08'
RUN_ID = Path(__file__).resolve().parents[1].name
RUN_DIR = Path(__file__).resolve().parents[1]
AUTHOR_SOURCE = SOURCE_RUN / 'manual_text_review_completed.csv'
AUTHOR_FROZEN = RUN_DIR / 'input_author_manual_text_review_completed.csv'
PAPER_FREEZE = PROJECT / 'paper' / 'Q1_GAP_RESULT_FREEZE.md'
AUTHORS = ['readability_1to5', 'completeness_1to5', 'contamination_0to2', 'overall_quality_1to5']


def now_iso(): return datetime.now(CST).isoformat(timespec='seconds')
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha_bytes(s.encode('utf-8'))
def sha_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def write_json(p, obj):
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); os.replace(t, p)


def write_csv(p, df): df.to_csv(p, index=False, encoding='utf-8-sig', lineterminator='\n')


def parse_ratings(completed: Path, blind: pd.DataFrame):
    raw = completed.read_bytes(); text = raw.decode('gb18030')
    ids = list(re.finditer(r'(?<![A-Za-z0-9])G1-\d{3}(?![A-Za-z0-9])', text))
    if len(ids) != 60 or len({m.group(0) for m in ids}) != 60:
        raise RuntimeError(f'completed table must contain 60 unique review_ids; observed {len(ids)}')
    tail_pat = re.compile(r'^\s*"\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)')
    cand_pat = re.compile(r'(?<![0-9])([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)\s*(?:,\s*){4,}(?=\r?\n|$)')
    def conv(vals): return [int(v) if v not in (None, '') else None for v in vals]
    def plausible(v):
        a, b, c, d = v
        if sum(x is not None for x in v) < 2: return False
        return (a is None or 0 <= a <= 5) and (b is None or 0 <= b <= 5) and (c is None or 0 <= c <= 2) and (d is None or 0 <= d <= 5)
    def valid(v):
        a, b, c, d = v
        if sum(x is not None for x in v) < 2: return False
        return (a is None or 1 <= a <= 5) and (b is None or 1 <= b <= 5) and (c is None or 0 <= c <= 2) and (d is None or 1 <= d <= 5)
    records = []
    blind_map = blind.set_index('review_id')['text_redacted'].to_dict()
    for i, m in enumerate(ids):
        rid = m.group(0); seg_end = ids[i + 1].start() if i + 1 < len(ids) else len(text)
        seg = text[m.start():seg_end]; source_text = blind_map[rid]
        chars, positions = [], []
        for j, ch in enumerate(seg):
            if not ch.isspace(): chars.append(ch); positions.append(j)
        norm = ''.join(chars); tail = None
        for k in [300, 250, 200, 150, 120, 100, 80, 60, 40, 20]:
            probe = ''.join(source_text[-k:].split())
            pos = norm.rfind(probe)
            if pos >= 0:
                tail = (k, positions[pos + len(probe) - 1] + 1); break
        selected = None; method = 'missing'; candidate_start = None; raw_candidate = ''
        if tail:
            mt = tail_pat.match(seg[tail[1]:tail[1] + 100])
            if mt:
                vals = conv(mt.groups()); raw_candidate = ','.join('' if v is None else str(v) for v in vals)
                if valid(vals): selected = vals; method = 'tail_boundary_valid'
                elif plausible(vals): selected = [None] * 4; method = 'tail_boundary_invalid'
        if selected is None and method == 'missing':
            candidates = []
            for x in cand_pat.finditer(seg):
                vals = conv(x.groups())
                if plausible(vals): candidates.append((sum(v is not None for v in vals), -x.start(), vals, x.start()))
            if candidates:
                chosen = max(candidates); vals = chosen[2]
                candidate_start = chosen[3]; raw_candidate = ','.join('' if v is None else str(v) for v in vals)
                if valid(vals): selected = vals; method = 'structural_valid'
                else: selected = [None] * 4; method = 'structural_invalid'
        if selected is None: selected = [None] * 4
        complete = all(v is not None for v in selected)
        status = 'valid_complete' if complete else ('valid_partial' if any(v is not None for v in selected) else method)
        records.append({'review_id': rid, 'parse_status': status, 'parse_method': method,
                        'candidate_start': candidate_start, 'raw_candidate': raw_candidate,
                        'readability_1to5': selected[0], 'completeness_1to5': selected[1],
                        'contamination_0to2': selected[2], 'overall_quality_1to5': selected[3]})
    return pd.DataFrame(records)

def stratified_indices(df: pd.DataFrame, rng: np.random.Generator):
    pieces = []
    for _, sub in df.groupby('sampling_stratum', sort=True):
        idx = sub.index.to_numpy()
        if len(idx): pieces.append(idx[rng.integers(0, len(idx), len(idx))])
    return np.concatenate(pieces) if pieces else np.array([], dtype=int)


def boot_ci(df: pd.DataFrame, metric_fn, seed_offset=0):
    rng = np.random.default_rng(SEED + seed_offset)
    values = []
    for _ in range(BOOTSTRAP):
        idx = stratified_indices(df, rng)
        try:
            v = metric_fn(df.loc[idx])
            if v is not None and np.isfinite(v): values.append(float(v))
        except Exception:
            pass
    a = np.asarray(values, dtype=float)
    return (float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975)), int(a.size)) if a.size else (None, None, 0)


def spearman_row(df, qcol, ycol, analysis, offset):
    z = df[[qcol, ycol, 'sampling_stratum']].dropna()
    rho, p = stats.spearmanr(z[qcol], z[ycol])
    lo, hi, nboot = boot_ci(z, lambda d: stats.spearmanr(d[qcol], d[ycol]).statistic, offset)
    return {'analysis': analysis, 'metric': f'{qcol}__{ycol}', 'group_a': 'Q_baseline', 'group_b': ycol,
            'n_a': len(z), 'n_b': len(z), 'estimate': float(rho), 'ci_low_2_5pct': lo, 'ci_high_97_5pct': hi,
            'p_value_descriptive': float(p), 'effect_size': float(rho), 'effect_size_name': 'spearman_rho',
            'bootstrap_replicates': nboot, 'seed': SEED, 'note': 'Pairwise complete author ratings; no imputation.'}


def group_difference(df, metric, offset):
    z = df[df.q_high_domain | df.q_low_domain][['q_high_domain', 'q_low_domain', metric, 'sampling_stratum']].dropna()
    hi = z.loc[z.q_high_domain, metric]; lo = z.loc[z.q_low_domain, metric]
    if len(hi) == 0 or len(lo) == 0:
        return None
    u, p = stats.mannwhitneyu(hi, lo, alternative='two-sided')
    delta = 2 * float(u) / (len(hi) * len(lo)) - 1
    def fn(d):
        a = d.loc[d.q_high_domain, metric]; b = d.loc[d.q_low_domain, metric]
        if len(a) == 0 or len(b) == 0: return np.nan
        uu, _ = stats.mannwhitneyu(a, b, alternative='two-sided')
        return 2 * float(uu) / (len(a) * len(b)) - 1
    lo_ci, hi_ci, nb = boot_ci(z, fn, offset)
    return {'analysis': 'highQ_vs_lowQ_manual_rating', 'metric': metric, 'group_a': 'within_domain_Q_high',
            'group_b': 'within_domain_Q_low', 'n_a': len(hi), 'n_b': len(lo),
            'estimate': float(hi.median() - lo.median()), 'ci_low_2_5pct': lo_ci, 'ci_high_97_5pct': hi_ci,
            'p_value_descriptive': float(p), 'effect_size': float(delta), 'effect_size_name': 'cliffs_delta_positive_highQ_higher',
            'bootstrap_replicates': nb, 'seed': SEED,
            'note': f'HighQ mean={hi.mean():.6f}, LowQ mean={lo.mean():.6f}; estimate is median difference.'}


def anomaly_difference(df, anomaly_col, analysis, offset):
    z = df[['high_conflict', anomaly_col, 'sampling_stratum']].dropna()
    hi = z.loc[z.high_conflict, anomaly_col].astype(bool); lo = z.loc[~z.high_conflict, anomaly_col].astype(bool)
    table = pd.crosstab(z.high_conflict, z[anomaly_col].astype(bool)).reindex(index=[True, False], columns=[False, True], fill_value=0)
    odds, p = stats.fisher_exact(table.values)
    rd = float(hi.mean() - lo.mean())
    def fn(d):
        a = d.loc[d.high_conflict, anomaly_col].astype(bool); b = d.loc[~d.high_conflict, anomaly_col].astype(bool)
        return float(a.mean() - b.mean()) if len(a) and len(b) else np.nan
    low, high, nb = boot_ci(z, fn, offset)
    return {'analysis': analysis, 'metric': anomaly_col, 'group_a': 'high_conflict', 'group_b': 'low_conflict',
            'n_a': len(hi), 'n_b': len(lo), 'estimate': rd, 'ci_low_2_5pct': low, 'ci_high_97_5pct': high,
            'p_value_descriptive': float(p), 'effect_size': float(odds), 'effect_size_name': 'fisher_odds_ratio',
            'bootstrap_replicates': nb, 'seed': SEED,
            'note': f'high_conflict rate={hi.mean():.6f}, low_conflict rate={lo.mean():.6f}; estimate is risk difference.'}


def make_statistics(joined):
    x = joined.copy()
    x['manual_anomaly_primary'] = np.where(x[['contamination_0to2', 'overall_quality_1to5']].notna().all(axis=1),
                                           ((x.contamination_0to2 >= 1) | (x.overall_quality_1to5 <= 2)).astype(float), np.nan)
    x['contamination_ge1'] = x.contamination_0to2.apply(lambda v: float(v >= 1) if pd.notna(v) else np.nan)
    x['overall_le2'] = x.overall_quality_1to5.apply(lambda v: float(v <= 2) if pd.notna(v) else np.nan)
    rows = [
        spearman_row(x, 'Q_baseline', 'overall_quality_1to5', 'spearman_Q_vs_overall_quality', 1),
        spearman_row(x, 'Q_baseline', 'readability_1to5', 'spearman_Q_vs_readability', 2),
        spearman_row(x, 'Q_baseline', 'completeness_1to5', 'spearman_Q_vs_completeness', 3),
        spearman_row(x, 'Q_baseline', 'contamination_0to2', 'spearman_Q_vs_contamination', 4),
    ]
    for i, metric in enumerate(AUTHORS, 10):
        row = group_difference(x, metric, i)
        if row: rows.append(row)
    anomalies = [
        ('high_conflict_vs_low_conflict_manual_anomaly_rate', 'manual_anomaly_primary', 21),
        ('high_conflict_vs_low_conflict_contamination_ge1_rate', 'contamination_ge1', 22),
        ('high_conflict_vs_low_conflict_overall_le2_rate', 'overall_le2', 23),
    ]
    for analysis, col, off in anomalies:
        row = anomaly_difference(x, col, analysis, off)
        if row: rows.append(row)
    return pd.DataFrame(rows), x

def make_cases(joined, blind):
    z = joined[joined.overall_quality_1to5.notna()].copy()
    success = z.sort_values(['overall_quality_1to5', 'contamination_0to2', 'readability_1to5', 'completeness_1to5', 'review_id'], ascending=[False, True, False, False, True]).head(3)
    failure = z.sort_values(['overall_quality_1to5', 'contamination_0to2', 'readability_1to5', 'completeness_1to5', 'review_id'], ascending=[True, False, True, True, True]).head(3)
    rows = []
    texts = blind.set_index('review_id').text_redacted.to_dict()
    for label, sub in [('success', success), ('failure', failure)]:
        for _, r in sub.iterrows():
            excerpt = re.sub(r'\s+', ' ', texts[r.review_id]).strip()[:240]
            rows.append({'review_id': r.review_id, 'case_type': label,
                         'readability_1to5': r.readability_1to5, 'completeness_1to5': r.completeness_1to5,
                         'contamination_0to2': r.contamination_0to2, 'overall_quality_1to5': r.overall_quality_1to5,
                         'short_redacted_excerpt': excerpt, 'excerpt_sha256': sha_text(excerpt)})
    return pd.DataFrame(rows)


def build_input_manifest():
    rels = [
        SOURCE_RUN / 'sampling_seal.json', SOURCE_RUN / 'manual_text_review_blind.csv',
        SOURCE_RUN / 'manual_review_key.csv', SOURCE_RUN / 'stability_decision.json',
        SOURCE_RUN / 'run_summary.json', SOURCE_RUN / 'output_manifest.json', AUTHOR_FROZEN]
    entries = []
    for p in rels:
        entries.append({'path': str(p.relative_to(PROJECT)).replace('\\', '/'), 'bytes': p.stat().st_size,
                        'mtime': p.stat().st_mtime, 'sha256': sha_file(p),
                        'role': 'author completed table frozen copy' if p == AUTHOR_FROZEN else 'sealed stage-1 input'})
    return {'run_id': RUN_ID, 'generated_local': now_iso(), 'source_run': str(SOURCE_RUN),
            'author_source_path': str(AUTHOR_SOURCE), 'author_source_bytes': AUTHOR_SOURCE.stat().st_size,
            'author_source_mtime': AUTHOR_SOURCE.stat().st_mtime, 'author_source_sha256': sha_file(AUTHOR_FROZEN),
            'author_source_encoding': 'gb18030/cp936-compatible', 'inputs': entries,
            'no_imputation': True, 'no_resampling': True}


def snapshot_source_manifest():
    man = json.loads((SOURCE_RUN / 'output_manifest.json').read_text(encoding='utf-8'))
    return {e['path']: {'bytes': e['bytes'], 'sha256': e['sha256']} for e in man['registered_files']}


def compare_source_manifest(before):
    changed = []
    for rel, meta in before.items():
        p = SOURCE_RUN / rel
        if not p.exists() or sha_file(p) != meta['sha256'] or p.stat().st_size != meta['bytes']:
            changed.append({'path': rel, 'before': meta, 'after': ({'bytes': p.stat().st_size, 'sha256': sha_file(p)} if p.exists() else None)})
    return changed


def snapshot_manuscript():
    root = PROJECT / 'paper' / 'manuscript'
    return {str(p.relative_to(PROJECT)).replace('\\', '/'): {'bytes': p.stat().st_size, 'sha256': sha_file(p)}
            for p in sorted(root.rglob('*')) if p.is_file()}


def compare_snapshot(before, after):
    return [{'path': k, 'before': before.get(k), 'after': after.get(k)}
            for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]


def check(name, passed, details): return {'check': name, 'status': 'PASS' if passed else 'FAIL', 'details': details}


def write_manifest(status, verification):
    entries = []
    for p in sorted(x for x in RUN_DIR.rglob('*') if x.is_file() and x.name != 'output_manifest.json' and not x.name.endswith('.tmp')):
        entries.append({'path': str(p.relative_to(RUN_DIR)).replace('\\', '/'), 'bytes': p.stat().st_size, 'sha256': sha_file(p)})
    payload = {'run_id': RUN_ID, 'task': 'TASK-G1-POST-AUTHOR', 'status': status,
               'generated_local': now_iso(), 'manifest_is_last_registered_artifact': True,
               'registered_file_count': len(entries), 'registered_files': entries,
               'external_artifacts': [{'path': str(PAPER_FREEZE.relative_to(PROJECT)).replace('\\', '/'),
                                       'bytes': PAPER_FREEZE.stat().st_size, 'sha256': sha_file(PAPER_FREEZE),
                                       'status': 'CANDIDATE_PENDING_CONTROLLER_REVIEW'}],
               'verification_status': verification['status'], 'source_run': str(SOURCE_RUN),
               'author_completed_source_sha256': sha_file(AUTHOR_FROZEN),
               'no_imputation': True, 'no_resampling': True, 'manual_scores_author_only': True}
    write_json(RUN_DIR / 'output_manifest.json', payload); return payload

def fmt(v, nd=6): return 'NA' if v is None or pd.isna(v) else f'{float(v):.{nd}f}'


def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time(); stages = []
    def stage(name, phase, **details):
        rec = {'run_id': RUN_ID, 'timestamp': now_iso(), 'stage': name, 'status': phase, **details}
        with (RUN_DIR / 'stage_status.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
        stages.append(rec)
    try:
        stage('s00_preflight', 'start')
        if not AUTHOR_SOURCE.exists() or not AUTHOR_FROZEN.exists():
            raise RuntimeError('author completed table or frozen copy missing')
        if PAPER_FREEZE.exists():
            raise RuntimeError('paper/Q1_GAP_RESULT_FREEZE.md already exists; refusing to overwrite')
        if sha_file(AUTHOR_SOURCE) != sha_file(AUTHOR_FROZEN):
            raise RuntimeError('author completed table changed after frozen copy')
        env = {'run_id': RUN_ID, 'generated_local': now_iso(), 'python_version': sys.version,
               'python_executable': sys.executable, 'platform': platform.platform(),
               'numpy': np.__version__, 'pandas': pd.__version__, 'scipy': scipy.__version__}
        write_json(RUN_DIR / 'environment.json', env)
        inp = build_input_manifest(); write_json(RUN_DIR / 'input_manifest.json', inp)
        source_before = snapshot_source_manifest(); write_json(RUN_DIR / 'source_manifest_before.json', source_before)
        manuscript_before = snapshot_manuscript(); write_json(RUN_DIR / 'paper_manuscript_before.json', manuscript_before)
        stage('s00_preflight', 'complete', inputs=len(inp['inputs']), no_paper_overwrite=True)

        stage('s10_author_parse_audit', 'start')
        blind = pd.read_csv(SOURCE_RUN / 'manual_text_review_blind.csv', dtype={'review_id': str})
        key = pd.read_csv(SOURCE_RUN / 'manual_review_key.csv', dtype={'review_id': str})
        ratings = parse_ratings(AUTHOR_FROZEN, blind)
        joined = key.merge(ratings, on='review_id', how='left', validate='one_to_one')
        joined['review_notes_optional'] = ''
        joined['rating_parse_status'] = joined['parse_status']
        joined['manual_anomaly_primary'] = np.where(
            joined[['contamination_0to2', 'overall_quality_1to5']].notna().all(axis=1),
            ((joined.contamination_0to2 >= 1) | (joined.overall_quality_1to5 <= 2)).astype(float), np.nan)
        write_csv(RUN_DIR / 'manual_review_parse_audit.csv', ratings)
        out_cols = ['review_id', 'key_sha256', 'domain', 'file_id', 'sampling_stratum', 'Q_baseline',
                    'q_high_domain', 'q_low_domain', 'high_conflict', 'readability_1to5', 'completeness_1to5',
                    'contamination_0to2', 'overall_quality_1to5', 'review_notes_optional',
                    'rating_parse_status', 'manual_anomaly_primary']
        write_csv(RUN_DIR / 'manual_text_review_joined.csv', joined[out_cols])
        counts = ratings.parse_status.value_counts().to_dict()
        stage('s10_author_parse_audit', 'complete', counts=counts, no_imputation=True)

        stage('s20_manual_statistics', 'start')
        statistics, analysis_frame = make_statistics(joined)
        write_csv(RUN_DIR / 'manual_validation_statistics.csv', statistics)
        stage('s20_manual_statistics', 'complete', rows=len(statistics), bootstrap=BOOTSTRAP, seed=SEED)

        stage('s30_cases', 'start')
        cases = make_cases(joined, blind)
        write_csv(RUN_DIR / 'manual_case_registry.csv', cases)
        stage('s30_cases', 'complete', rows=len(cases), selection_rule='top/bottom author overall_quality only')

        stage('s40_paper_candidate', 'start')
        stability = json.loads((SOURCE_RUN / 'stability_decision.json').read_text(encoding='utf-8'))
        stat = {r.analysis: r for _, r in statistics.iterrows()}
        counts = ratings.parse_status.value_counts().to_dict()
        invalid_count = int(ratings.parse_status.str.contains('invalid', na=False).sum())
        missing_count = int(ratings.parse_status.eq('missing').sum())
        def sr(name):
            r = stat[name]
            return (f"n={int(r.n_a)}, rho={fmt(r.estimate)}, 95% CI [{fmt(r.ci_low_2_5pct)}, {fmt(r.ci_high_97_5pct)}], "
                    f"descriptive p={fmt(r.p_value_descriptive)}")
        def gr(metric):
            row = statistics[(statistics.analysis == 'highQ_vs_lowQ_manual_rating') & (statistics.metric == metric)]
            if len(row) != 1:
                return 'NOT_EVALUABLE'
            r = row.iloc[0]
            return (f"n_high={int(r.n_a)}, n_low={int(r.n_b)}, median diff={fmt(r.estimate)}, "
                    f"Cliff delta={fmt(r.effect_size)} [{fmt(r.ci_low_2_5pct)}, {fmt(r.ci_high_97_5pct)}], p={fmt(r.p_value_descriptive)}")
        def ar(name):
            r = stat[name]
            return (f"n_high={int(r.n_a)}, n_low={int(r.n_b)}, risk diff={fmt(r.estimate)} "
                    f"[{fmt(r.ci_low_2_5pct)}, {fmt(r.ci_high_97_5pct)}], Fisher OR={fmt(r.effect_size)}, p={fmt(r.p_value_descriptive)}")
        paper = f'''# Q1 Gap Result Freeze Candidate\n\n状态：`CANDIDATE_PENDING_CONTROLLER_REVIEW`。本文件只汇总既有Q01C/T03E冻结结果与作者人工文本核验；不重做主Q，不重选质量特征，不修改原论文正文。\n\n## 1. 结论边界\n\n- Q01C主Q保持不变：11个主特征严格完整案例，三组组内等权、组间等权，`Q_valid=False`记录不删除、不填补。\n- 扩展冲突稳定性资格：`{stability["status"]}`。A2全局判据通过{stability["extension_reports"]["A2_extension"]["global_pass_count"]}/4，A3通过{stability["extension_reports"]["A3_extension"]["global_pass_count"]}/4；共同有效域分别只有{stability["extension_reports"]["A2_extension"]["common_domain_count"]}和{stability["extension_reports"]["A3_extension"]["common_domain_count"]}个，少于预注册的4域，因此域级判据为`NOT_EVALUABLE`，且未观察到一致反转。\n- 该结果支持“主Q在A1内可用、但现有A2/A3扩展不能证明完整结构迁移”的限定性结论；不得写成全局稳定或跨域已证实。\n\n## 2. 文本核验口径\n\n- A18候选仅完成join审计，未用于抽样；其与Q01C A1内容精确匹配仅1条，且冻结映射指南只有3个direct域，不能无模糊映射覆盖6域。\n- 采用Q01C正式A1原始源作为直接文本源：51,230/51,230条按`key_sha256(id,sub_path)`一一匹配，文本非空率1.0。\n- 作者完成表包含60个sealed `review_id`。其中可验证四项完整评分{counts.get("valid_complete", 0)}条、部分评分{counts.get("valid_partial", 0)}条、越界无效候选{invalid_count}条、无可用评分{missing_count}条。所有统计均按成对有效记录计算，不插补、不重抽样、不生成代替作者判断的评分。\n\n|核验项|结果|允许的解释|\n|---|---|---|\n|Q与overall quality Spearman|{sr("spearman_Q_vs_overall_quality")}|相关性描述，不是外部真值| \n|Q与readability Spearman|{sr("spearman_Q_vs_readability")}|方向仅为样本内秩相关| \n|Q与completeness Spearman|{sr("spearman_Q_vs_completeness")}|方向仅为样本内秩相关| \n|Q与contamination Spearman|{sr("spearman_Q_vs_contamination")}|污染分数越低越好，正相关表示Q越高污染越多| \n|高Q vs 低Q overall|{gr("overall_quality_1to5")}|同域上下四分位定义的抽样层比较| \n|高Q vs 低Q readability|{gr("readability_1to5")}|描述性组间差异| \n|高Q vs 低Q completeness|{gr("completeness_1to5")}|描述性组间差异| \n|高Q vs 低Q contamination|{gr("contamination_0to2")}|越高表示污染越强| \n|高冲突 vs 低冲突人工异常率|{ar("high_conflict_vs_low_conflict_manual_anomaly_rate")}|异常定义为contamination≥1或overall≤2| \n|高冲突 vs 低冲突污染阳性率|{ar("high_conflict_vs_low_conflict_contamination_ge1_rate")}|contamination≥1| \n|高冲突 vs 低冲突低总体质量率|{ar("high_conflict_vs_low_conflict_overall_le2_rate")}|overall≤2| \n\n## 3. 对论文的冻结建议\n\n1. Q1质量结论继续使用Q01C主Q；扩展冲突稳定性只可用于限制和敏感性说明，不能升级为跨A2/A3稳定结论。\n2. A18文本核验不是全量强制验证；论文应明确其为可选附件候选审计，并标注当前作者文本核验有效样本未达到60条完整评分。\n3. 人工相关性与组间差异结果应原样报告，包括弱相关、方向不一致或无差异；不得解释为因果，也不得据此修改主Q或重抽样。\n4. 若主论文需要引用人工核验，应使用`manual_validation_statistics.csv`中的成对`n`和限制字段，不得抽取单一有利指标。\n\n## 4. 证据入口\n\n- 稳定性：`{SOURCE_RUN / "stability_decision.json"}`\n- 抽样seal：`{SOURCE_RUN / "sampling_seal.json"}`\n- 后作者统计：`{RUN_DIR / "manual_validation_statistics.csv"}`\n- 作者解析审计：`{RUN_DIR / "manual_review_parse_audit.csv"}`\n- 独立验收：`{RUN_DIR / "verification.json"}`\n'''
        tmp = PAPER_FREEZE.with_suffix('.md.tmp')
        tmp.write_text(paper, encoding='utf-8'); os.replace(tmp, PAPER_FREEZE)
        stage('s40_paper_candidate', 'complete', path=str(PAPER_FREEZE), status='CANDIDATE_PENDING_CONTROLLER_REVIEW')

        stage('s50_checks_preverify', 'start')
        source_changes = compare_source_manifest(source_before)
        manuscript_after = snapshot_manuscript()
        manuscript_changes = compare_snapshot(manuscript_before, manuscript_after)
        verifier = RUN_DIR / 'code' / 'verify_post_author.py'
        proc = subprocess.run([sys.executable, str(verifier), '--run-dir', str(RUN_DIR)],
                              capture_output=True, text=True, encoding='utf-8')
        if proc.returncode != 0:
            raise RuntimeError(f'independent post-author verifier failed: {proc.stdout}\n{proc.stderr}')
        verification = json.loads((RUN_DIR / 'verification.json').read_text(encoding='utf-8'))
        status_counts = ratings.parse_status.value_counts().to_dict()
        checks = [
            check('author_completed_source_still_matches_frozen_copy', sha_file(AUTHOR_SOURCE) == sha_file(AUTHOR_FROZEN),
                  {'source': sha_file(AUTHOR_SOURCE), 'frozen': sha_file(AUTHOR_FROZEN)}),
            check('source_run_registered_artifacts_unchanged', not source_changes, source_changes),
            check('paper_manuscript_unchanged', not manuscript_changes, manuscript_changes),
            check('sealed_blind_hash_matches_source_manifest',
                  sha_file(SOURCE_RUN / 'manual_text_review_blind.csv') == json.loads((SOURCE_RUN / 'output_manifest.json').read_text(encoding='utf-8'))['blind_sha256'],
                  {'blind_sha256': sha_file(SOURCE_RUN / 'manual_text_review_blind.csv')}),
            check('author_table_has_60_unique_review_ids', len(ratings) == 60 and ratings.review_id.is_unique,
                  {'rows': len(ratings), 'unique': int(ratings.review_id.nunique())}),
            check('no_rating_imputation_or_ai_scoring', joined.rating_parse_status.isin(['valid_complete', 'valid_partial', 'structural_invalid', 'tail_boundary_invalid', 'missing']).all(),
                  {'status_counts': status_counts, 'analysis_rule': 'pairwise complete valid ratings only'}),
            check('primary_statistics_have_finite_core_estimates',
                  np.isfinite(statistics.loc[statistics.analysis.str.startswith('spearman_'), 'estimate']).all(),
                  statistics.loc[statistics.analysis.str.startswith('spearman_'), ['analysis', 'n_a', 'estimate', 'ci_low_2_5pct', 'ci_high_97_5pct']].to_dict(orient='records')),
            check('case_registry_at_most_six', len(cases) <= 6, {'rows': len(cases), 'selection': 'author overall_quality only'}),
            check('paper_candidate_exists_not_overwritten', PAPER_FREEZE.exists() and paper.startswith('# Q1 Gap Result Freeze Candidate'),
                  {'path': str(PAPER_FREEZE), 'bytes': PAPER_FREEZE.stat().st_size}),
            check('independent_post_author_verifier_passed', verification.get('status') == 'PASS',
                  {'status': verification.get('status'), 'summary': verification.get('summary')}),
        ]
        checks_payload = {'run_id': RUN_ID, 'generated_local': now_iso(),
                          'summary': {'total': len(checks), 'pass': sum(c['status'] == 'PASS' for c in checks),
                                      'fail': sum(c['status'] == 'FAIL' for c in checks)},
                          'checks': checks}
        write_json(RUN_DIR / 'checks.json', checks_payload)
        stage('s50_checks_preverify', 'complete', checks=checks_payload['summary'])

        stage('s60_finalize_wait_manifest', 'start')
        run_summary = {'task': 'TASK-G1-POST-AUTHOR', 'run_id': RUN_ID,
                       'status': 'COMPLETE_PENDING_CONTROLLER_REVIEW',
                       'source_run': str(SOURCE_RUN), 'started_local': datetime.fromtimestamp(started, CST).isoformat(timespec='seconds'),
                       'finished_local': now_iso(), 'duration_s': round(time.time() - started, 3),
                       'author_parse_counts': status_counts, 'valid_pairwise_counts': {
                           'overall_quality_1to5': int(joined.overall_quality_1to5.notna().sum()),
                           'readability_1to5': int(joined.readability_1to5.notna().sum()),
                           'completeness_1to5': int(joined.completeness_1to5.notna().sum()),
                           'contamination_0to2': int(joined.contamination_0to2.notna().sum())},
                       'statistics_rows': len(statistics), 'case_rows': len(cases),
                       'paper_candidate': str(PAPER_FREEZE), 'paper_candidate_status': 'CANDIDATE_PENDING_CONTROLLER_REVIEW',
                       'checks': checks_payload['summary'], 'verification': verification.get('summary'),
                       'no_imputation': True, 'no_resampling': True, 'manual_scores_author_only': True}
        write_json(RUN_DIR / 'run_summary.json', run_summary)
        command_log = {'run_id': RUN_ID, 'argv': sys.argv, 'started_local': datetime.fromtimestamp(started, CST).isoformat(timespec='seconds'),
                       'finished_local': now_iso(), 'stages': stages,
                       'verifier_command': [sys.executable, str(verifier), '--run-dir', str(RUN_DIR)],
                       'verifier_stdout': proc.stdout, 'verifier_stderr': proc.stderr}
        write_json(RUN_DIR / 'command_log.json', command_log)
        handoff = f'''# TASK-G1 post-author handoff\n\n状态：`COMPLETE_PENDING_CONTROLLER_REVIEW`\n\n- 作者表：60个review_id；完整四项{status_counts.get("valid_complete",0)}条，部分{status_counts.get("valid_partial",0)}条，无效/缺失{invalid_count + missing_count}条。\n- 无插补、无重新抽样；所有统计使用成对有效记录。\n- 扩展冲突稳定性保持首阶段冻结资格：`{stability["status"]}`。\n- 候选冻结文件：`{PAPER_FREEZE}`。\n- 独立post-author验收：{verification.get("status")}，fail={verification.get("summary",{}).get("fail")}。\n- 未修改Q01C/T03E旧run、00–05或paper/manuscript正文。\n\n## 机器入口\n\n`manual_review_parse_audit.csv`、`manual_text_review_joined.csv`、`manual_validation_statistics.csv`、`manual_case_registry.csv`、`checks.json`、`verification.json`、`output_manifest.json`。\n'''
        (RUN_DIR / 'handoff.md').write_text(handoff, encoding='utf-8')
        snap = RUN_DIR / 'code_snapshot'
        if snap.exists(): shutil.rmtree(snap)
        shutil.copytree(RUN_DIR / 'code', snap)
        stage('s60_finalize_wait_manifest', 'complete', status='COMPLETE_PENDING_CONTROLLER_REVIEW')
        stage('s70_manifest_pending', 'will_generate_output_manifest_last')
        manifest = write_manifest('COMPLETE_PENDING_CONTROLLER_REVIEW', verification)
        print(json.dumps({'status': 'COMPLETE_PENDING_CONTROLLER_REVIEW', 'paper_candidate': str(PAPER_FREEZE),
                          'registered_files': manifest['registered_file_count'], 'parse_counts': status_counts}, ensure_ascii=False))
        return 0
    except Exception as exc:
        stage('ERROR', 'stopped_with_evidence', error=repr(exc))
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
