# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""A1--A3 streaming audit and a deliberately simple quality-score baseline.

AI-assisted: OpenAI Codex (OpenAI), 2026-09-24. Exact model version and
release date have not been verified. Original attachments are never modified.

Run: D:\\anaconda\\python.exe solution/src/quality_audit.py
The eight official semantic sources were retrieved into
outputs/quality/semantic_sources; their URLs and hashes are in manifest.json.
Only A1 calibration rows determine continuous normalization. Equal domain
weights avoid treating the number of downloaded records as domain importance.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import lzma
from pathlib import Path
import time

import numpy as np
import pandas as pd

from common import DATA, SEED, configure_stdout, output_dir, save_json, write_report

RULES = [
    'rps_doc_frac_no_alph_words', 'rps_doc_mean_word_length',
    'rps_doc_frac_unique_words', 'rps_doc_unigram_entropy', 'rps_doc_word_count',
    'rps_lines_ending_with_terminal_punctution_mark',
    'rps_lines_numerical_chars_fraction', 'rps_lines_uppercase_letter_fraction',
    'rps_doc_num_sentences', 'rps_doc_frac_chars_top_2gram',
    'rps_doc_frac_chars_top_3gram',
]
DSIR = ['dsir_books', 'dsir_wiki', 'dsir_math']
PRRC = ['modernbert_professionalism', 'modernbert_readability',
        'modernbert_reasoning', 'modernbert_cleanliness']
LIST_LENGTHS = {'fineweb_edu': 1, 'ad_en': 2, 'fluency_en': 2,
                'qurater': 4, **{p: 6 for p in PRRC}}
FIELDS = RULES + DSIR + list(LIST_LENGTHS)
QURATER = ['qurater_writing_style', 'qurater_required_expertise',
           'qurater_facts_trivia', 'qurater_educational_value']
MODEL = ['fineweb_edu', 'ad_en', 'fluency_en'] + QURATER + PRRC
FEATURES = RULES + DSIR + MODEL
GROUPS = {
    'usability': ['ad_en', 'fluency_en', 'modernbert_readability',
                  'modernbert_cleanliness', 'qurater_writing_style'],
    'knowledge': ['modernbert_professionalism', 'qurater_required_expertise',
                  'qurater_facts_trivia'],
    'education_reasoning': ['modernbert_reasoning', 'fineweb_edu',
                           'qurater_educational_value'],
}
HF = 'https://huggingface.co/datasets/opendatalab/SlimPajama-Meta-rater/blob/main/README.md'
CODE = ('https://github.com/opendatalab/Meta-rater/blob/'
        '633d1fc308f423c11f0c975c1869c16cbf302c44/pipeline/step2_select_data.py')


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def empty_stats():
    return {'present': 0, 'null': 0, 'types': Counter(), 'lengths': Counter(),
            'non_numeric': 0, 'nan': 0, 'pos_inf': 0, 'neg_inf': 0,
            'finite_elements': 0, 'negative_elements': 0, 'zero_elements': 0,
            'min': float('inf'), 'max': float('-inf'),
            'valid_list_rows': 0, 'list_negative_rows': 0,
            'list_all_in_0_1_rows': 0, 'list_sum_approx_1_rows': 0,
            'list_sum_min': float('inf'), 'list_sum_max': float('-inf'),
            'argmax_counts': Counter(), 'argmax_tie_rows': 0}


def audit_value(value, stats):
    """Describe raw values; do not treat logits as probabilities."""
    stats['present'] += 1
    stats['types'][type(value).__name__] += 1
    if value is None:
        stats['null'] += 1
        return
    values = value if isinstance(value, list) else [value]
    if isinstance(value, list):
        stats['lengths'][len(value)] += 1
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in values):
        stats['non_numeric'] += 1
        return
    a = np.asarray(values, dtype=float)
    stats['nan'] += int(np.isnan(a).sum())
    stats['pos_inf'] += int(np.isposinf(a).sum())
    stats['neg_inf'] += int(np.isneginf(a).sum())
    finite = a[np.isfinite(a)]
    if finite.size:
        stats['finite_elements'] += len(finite)
        stats['negative_elements'] += int((finite < 0).sum())
        stats['zero_elements'] += int((finite == 0).sum())
        stats['min'] = min(stats['min'], float(finite.min()))
        stats['max'] = max(stats['max'], float(finite.max()))
    if isinstance(value, list) and a.size and np.isfinite(a).all():
        stats['valid_list_rows'] += 1
        stats['list_negative_rows'] += int((a < 0).any())
        stats['list_all_in_0_1_rows'] += int(((a >= 0) & (a <= 1)).all())
        total = float(a.sum())
        stats['list_sum_approx_1_rows'] += int(abs(total - 1) < 1e-6)
        stats['list_sum_min'] = min(stats['list_sum_min'], total)
        stats['list_sum_max'] = max(stats['list_sum_max'], total)
        stats['argmax_counts'][int(a.argmax())] += 1
        stats['argmax_tie_rows'] += int((a == a.max()).sum() > 1)


def clean_stats(stats, n):
    result = dict(stats)
    result['absent'] = n - result['present']
    for name, value in result.items():
        if isinstance(value, Counter):
            result[name] = {str(k): v for k, v in sorted(value.items())}
        if isinstance(value, float) and not np.isfinite(value):
            result[name] = None
    return result


def get_features(obj):
    result = {}
    for field in RULES + DSIR:
        value = obj.get(field)
        result[field] = float(value) if isinstance(value, (int, float)) else np.nan
    for field, expected in LIST_LENGTHS.items():
        value = obj.get(field)
        valid = isinstance(value, list) and len(value) == expected
        if valid:
            valid = all(isinstance(x, (int, float)) and np.isfinite(x) for x in value)
        if field == 'qurater':
            result.update({col: float(value[i]) if valid else np.nan
                           for i, col in enumerate(QURATER)})
        elif field == 'fineweb_edu':
            result[field] = float(value[0]) if valid else np.nan
        else:
            # Official README and pipeline: class index, not logit mean/softmax.
            result[field] = float(np.argmax(value)) if valid else np.nan
    return result


def quality_fingerprint(obj):
    normalized = {}
    for f in FIELDS:
        v = obj.get(f)
        normalized[f] = ([float(x) for x in v] if isinstance(v, list)
                         else float(v) if isinstance(v, (int, float)) else v)
    return stable_hash(json.dumps(normalized, sort_keys=True, separators=(',', ':')))


def stream_audit(out):
    """Read compressed files once; no raw content is held in memory."""
    base = DATA / 'A_data_value'
    specs = [
        ('A1', base / 'slimpajama_quality_signal_sample.jsonl.xz', None),
        ('A2_arxiv', base / 'slimpajama_quality_extended' /
         'arxiv_part-6777d8857c6e-000486.jsonl.xz', 'arxiv'),
        ('A3_github', base / 'slimpajama_quality_extended' /
         'github_part-6777d8857c6e-000275.jsonl.xz', 'github'),
    ]
    rows, audits, seen, conflicts, domain_collisions = [], [], {}, [], []
    a1_keys, keysets = set(), {}
    for file_id, path, fallback_domain in specs:
        print(f'Reading {file_id}: {path.name}', flush=True)
        stats = {f: empty_stats() for f in FIELDS}
        domains, subpaths, all_keys = Counter(), Counter(), Counter()
        content_rows = content_empty = source_domain_missing = 0
        invalid, n, duplicate_in_file, overlap_a1, differing = [], 0, 0, 0, 0
        file_seen = set()
        for line_no, line in enumerate(lzma.open(path, 'rt', encoding='utf-8'), 1):
            try:
                obj = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                invalid.append({'line': line_no, 'error': str(exc)})
                continue
            n += 1
            all_keys.update(obj.keys())
            for f in FIELDS:
                if f in obj:
                    audit_value(obj[f], stats[f])
            domain = obj.get('_source_domain') or fallback_domain or 'unknown'
            domains[domain] += 1
            if not obj.get('_source_domain'):
                source_domain_missing += 1
            subpath = obj.get('sub_path', '')
            subpaths[subpath] += 1
            key = (str(obj.get('id', '')), str(subpath))
            key_json = json.dumps(key, ensure_ascii=False, separators=(',', ':'))
            fingerprint = quality_fingerprint(obj)
            previous = seen.get(key)
            duplicate = previous is not None
            conflict = duplicate and previous[1] != fingerprint
            if key in file_seen:
                duplicate_in_file += 1
            file_seen.add(key)
            in_a1 = file_id != 'A1' and key in a1_keys
            overlap_a1 += int(in_a1)
            differing += int(conflict)
            if conflict:
                conflicts.append({'key': key, 'file': file_id, 'line': line_no,
                                  'first_file': previous[0]})
            if duplicate and previous[2] != domain:
                domain_collisions.append({'key': key, 'first_domain': previous[2],
                                          'domain': domain})
            if not duplicate:
                seen[key] = (file_id, fingerprint, domain)
            if file_id == 'A1':
                a1_keys.add(key)
            content = obj.get('content')
            content_present = isinstance(content, str)
            content_rows += int(content_present)
            content_empty += int(content_present and not content)
            # Stable split is keyed by document, so duplicate copies cannot cross it.
            split = int(stable_hash(str(SEED) + key_json)[:16], 16) % 5
            row = {
                'file_id': file_id, 'source_line': line_no, 'id': obj.get('id'),
                'sub_path': subpath, 'domain': domain,
                'key_sha256': stable_hash(key_json), 'quality_sha256': fingerprint,
                'is_unique_first': not duplicate, 'overlap_a1': in_a1,
                'quality_conflict': conflict,
                'evaluation_role': ('A1_holdout' if split == 0 else 'A1_calibration')
                if file_id == 'A1' else 'extension_overlap_A1' if in_a1
                else 'extension_new_records',
                'content_present': content_present,
                'content_characters': len(content) if content_present else None,
                'content_sha256': stable_hash(content) if content_present else None,
            }
            row.update(get_features(obj))
            rows.append(row)
            if n % 50000 == 0:
                print(f'  {file_id}: {n:,} records', flush=True)
        keysets[file_id] = file_seen
        audits.append({
            'file_id': file_id, 'file': str(path.relative_to(DATA)),
            'bytes': path.stat().st_size, 'sha256': sha_file(path), 'rows': n,
            'invalid_json_lines': invalid, 'domains': dict(domains),
            'raw_sub_path_counts': dict(subpaths), 'present_keys': dict(all_keys),
            'content_present_rows': content_rows, 'empty_content_rows': content_empty,
            'missing_source_domain_rows': source_domain_missing,
            'unique_id_sub_path_keys_in_file': len(file_seen),
            'within_file_duplicate_rows': duplicate_in_file,
            'overlapping_a1_rows': overlap_a1, 'quality_conflicting_rows': differing,
            'fields': {f: clean_stats(s, n) for f, s in stats.items()},
        })
        print(f'Completed {file_id}: {n:,} rows, A1 overlap {overlap_a1:,}', flush=True)
    df = pd.DataFrame(rows)
    pairwise = {f'{a}__{b}': len(keysets[a] & keysets[b])
                for i, a in enumerate(keysets) for b in list(keysets)[i + 1:]}
    a1 = df[df.file_id.eq('A1')]
    text_nonnull = a1.content_sha256.dropna()
    audit = {
        'run_date': '2026-09-24', 'seed': SEED, 'files': audits,
        'total_records': len(df), 'unique_id_sub_path_keys': len(seen),
        'duplicate_occurrences': int((~df.is_unique_first).sum()),
        'pairwise_key_intersections': pairwise, 'quality_conflicts': conflicts,
        'domain_collisions': domain_collisions,
        'a1_duplicate_content_occurrences': int(text_nonnull.duplicated().sum()),
        'a1_content_is_not_used_to_fit_scores': True,
        'raw_quality_fields': len(FIELDS), 'expanded_scalar_features': len(FEATURES),
        'joint_key': ['id', 'sub_path'],
        'domain_inference': 'A1 _source_domain; extensions from documented filename. sub_path is audited independently.',
    }
    save_json(out / 'audit.json', audit)
    return df, audit


def weighted_quantile(values, weights, quantiles):
    good = np.isfinite(values) & np.isfinite(weights)
    values, weights = values[good], weights[good]
    order = np.argsort(values, kind='stable')
    values, weights = values[order], weights[order]
    positions = (np.cumsum(weights) - weights / 2) / weights.sum()
    return np.interp(quantiles, positions, values)


def score_quality(df, out):
    """Three equal groups. Fit robust transformations only on A1 calibration."""
    calibration = df.is_unique_first & df.evaluation_role.eq('A1_calibration')
    train = df.loc[calibration]
    domain_counts = train.domain.value_counts()
    weights = train.domain.map(lambda d: 1 / (len(domain_counts) * domain_counts[d])).to_numpy()
    normalized = pd.DataFrame(index=df.index)
    params = {'calibration_rows': int(calibration.sum()),
              'calibration_domain_counts': domain_counts.to_dict(),
              'domain_weight': 'Each domain has 1/7 total calibration weight',
              'groups': GROUPS, 'group_weight': 1 / len(GROUPS),
              'excluded_primary_score_features': RULES + DSIR,
              'reason_for_exclusion': 'No universal monotonic quality direction or target-domain utility has been established.',
              'continuous_quantiles': [0.01, 0.99], 'transforms': {}}
    for feature in MODEL:
        if feature in PRRC:
            low, high, method = 0.0, 5.0, 'official_ordinal_range'
        elif feature in ['ad_en', 'fluency_en']:
            low, high, method = 0.0, 1.0, 'official_binary_class_index'
        else:
            low, high = weighted_quantile(train[feature].to_numpy(), weights, [0.01, 0.99])
            method = 'A1_calibration_equal_domain_weight_1_99_percentile'
        assert high > low, (feature, low, high)
        normalized[feature] = ((df[feature] - low) / (high - low)).clip(0, 1)
        params['transforms'][feature] = {'low': float(low), 'high': float(high),
                                          'method': method, 'direction': 'higher'}
        df['normalized_' + feature] = normalized[feature]
    for group, features in GROUPS.items():
        # No silent fill: every constituent must be present for this baseline.
        df['group_' + group] = normalized[features].mean(axis=1, skipna=False)
    group_cols = ['group_' + g for g in GROUPS]
    df['Q_baseline'] = df[group_cols].mean(axis=1, skipna=False)
    # This is rater disagreement, not ground-truth error or resolution success.
    df['rater_disagreement_range'] = df[group_cols].max(axis=1) - df[group_cols].min(axis=1)
    df['rater_disagreement_std'] = df[group_cols].std(axis=1, ddof=0)
    df['Q_equal_indicator_sensitivity'] = normalized[MODEL].mean(axis=1, skipna=False)
    df['Q_without_knowledge_sensitivity'] = df[
        ['group_usability', 'group_education_reasoning']].mean(axis=1, skipna=False)
    save_json(out / 'normalization.json', params)
    return df, params


def summarize(df, out):
    summaries = []
    slices = {'A1_calibration': df[df.evaluation_role.eq('A1_calibration') & df.is_unique_first],
              'A1_holdout': df[df.evaluation_role.eq('A1_holdout') & df.is_unique_first],
              'A1_all_unique': df[df.file_id.eq('A1') & df.is_unique_first],
              'extension_overlap_A1': df[df.overlap_a1],
              'extension_new_records': df[df.evaluation_role.eq('extension_new_records') & df.is_unique_first],
              'all_unique': df[df.is_unique_first]}
    for scope, part in slices.items():
        for domain, group in part.groupby('domain', observed=True):
            q = group.Q_baseline
            row = {'scope': scope, 'domain': domain, 'n': len(group),
                   'Q_mean': q.mean(), 'Q_std': q.std(),
                   'Q_p10': q.quantile(.1), 'Q_median': q.median(), 'Q_p90': q.quantile(.9),
                   'rater_disagreement_mean': group.rater_disagreement_range.mean(),
                   'rater_disagreement_gt_0_5_fraction': (group.rater_disagreement_range > .5).mean(),
                   'equal_indicator_Q_mean': group.Q_equal_indicator_sensitivity.mean(),
                   'without_knowledge_Q_mean': group.Q_without_knowledge_sensitivity.mean()}
            row.update({c + '_mean': group[c].mean() for c in df if c.startswith('group_')})
            summaries.append(row)
    summary = pd.DataFrame(summaries)
    summary.to_csv(out / 'domain_summary.csv', index=False, encoding='utf-8-sig')
    feature_summary = (df[df.is_unique_first].groupby(['file_id', 'domain'], observed=True)[FEATURES]
                       .agg(['count', 'mean', 'std', 'min', 'max']))
    feature_summary.columns = ['__'.join(c) for c in feature_summary.columns]
    feature_summary.to_csv(out / 'feature_summary.csv', encoding='utf-8-sig')
    # Distribution shift is descriptive: extension IDs are new, but each domain
    # extension is from the SAME downloaded source shard, not a fresh domain sample.
    shift = []
    for domain in ['arxiv', 'github']:
        aa = slices['A1_all_unique'].query('domain == @domain')
        bb = slices['extension_new_records'].query('domain == @domain')
        for feature in MODEL + ['Q_baseline']:
            x, y = aa[feature], bb[feature]
            sd = np.sqrt((x.var() + y.var()) / 2)
            shift.append({'domain': domain, 'feature': feature,
                          'a1_n': len(x), 'extension_new_n': len(y),
                          'a1_mean': x.mean(), 'extension_new_mean': y.mean(),
                          'standardized_mean_difference': (y.mean() - x.mean()) / sd if sd > 0 else 0})
    pd.DataFrame(shift).to_csv(out / 'extension_shift.csv', index=False, encoding='utf-8-sig')
    return summary


def unresolved_indicator_diagnostics(df, out):
    """Retain every unresolved feature; associations are not direction evidence."""
    from scipy.stats import spearmanr
    notes = {
        'rps_doc_frac_no_alph_words': ('domain_conditional_negative', '自然语言文本中高值可能表示噪声；代码与公式不能沿用同一方向。'),
        'rps_doc_mean_word_length': ('moderate_or_domain_conditional', '过短、过长可能异常；代码标识符和专业词汇改变合理范围。'),
        'rps_doc_frac_unique_words': ('moderate_or_domain_conditional', '低值可能重复；极高值也可能碎片或噪声，受篇幅影响。'),
        'rps_doc_unigram_entropy': ('moderate_or_task_conditional', '高熵代表多样性，也可能随机噪声；需要与领域及篇幅联合判断。'),
        'rps_doc_word_count': ('saturating_or_length_control', '篇幅不是质量，优先作为长度控制变量或饱和适度型指标。'),
        'rps_lines_ending_with_terminal_punctution_mark': ('domain_conditional_positive', '散文语句完整性代理；代码和数学公式行不应据此扣分。'),
        'rps_lines_numerical_chars_fraction': ('task_conditional', '数理代码与正文的合理数字密度不同，普适方向未知。'),
        'rps_lines_uppercase_letter_fraction': ('moderate_or_domain_conditional', '极高值可能噪声；缩写、专名和代码也会升高。'),
        'rps_doc_num_sentences': ('saturating_or_length_control', '反映篇幅与句切分器，不能简单越多越优。'),
        'rps_doc_frac_chars_top_2gram': ('domain_conditional_negative', '高重复可能退化；代码语法和公式的合法重复应区别处理。'),
        'rps_doc_frac_chars_top_3gram': ('domain_conditional_negative', '高重复可能退化；需控制领域与文档长度。'),
        'dsir_books': ('target_domain_relevance', '面向Books的相似性/重要性，并非普适质量。'),
        'dsir_wiki': ('target_domain_relevance', '面向Wikipedia的相似性/重要性，并非普适质量。'),
        'dsir_math': ('target_domain_relevance', '面向AutoMathText的相似性/重要性，并非普适质量。'),
    }
    a1 = df[df.file_id.eq('A1') & df.is_unique_first]
    correlations = []
    def pair_row(scope, domain, f, x, y):
        good = np.isfinite(x) & np.isfinite(y)
        n = int(good.sum())
        rho = float(spearmanr(x[good], y[good]).statistic) if n > 2 and len(np.unique(x[good])) > 1 else np.nan
        return {'scope': scope, 'domain': domain, 'feature': f, 'n': n,
                'spearman_rho_to_Q': rho}
    for scope, part in [('A1_calibration', a1[a1.evaluation_role.eq('A1_calibration')]),
                        ('A1_holdout', a1[a1.evaluation_role.eq('A1_holdout')]),
                        ('extension_new_records', df[df.is_unique_first & df.evaluation_role.eq('extension_new_records')])]:
        for domain, sub in part.groupby('domain'):
            for f in RULES + DSIR:
                correlations.append(pair_row(scope, domain, f, sub[f].to_numpy(), sub.Q_baseline.to_numpy()))
    means = a1.groupby('domain')[RULES + DSIR + ['Q_baseline']].mean()
    for f in RULES + DSIR:
        correlations.append(pair_row('A1_between_domain_means', 'seven_domain_means', f,
                                     means[f].to_numpy(), means.Q_baseline.to_numpy()))
        correlations.append(pair_row('A1_pooled_records', 'pooled', f, a1[f].to_numpy(), a1.Q_baseline.to_numpy()))
    assoc = pd.DataFrame(correlations)
    assoc.to_csv(out / 'unresolved_indicator_correlations.csv', index=False, encoding='utf-8-sig')
    directions = []
    for f in RULES + DSIR:
        within = assoc[(assoc.feature == f) & (assoc.scope == 'A1_calibration')].spearman_rho_to_Q
        directions.append({'feature': f, 'included_in_primary_Q': False,
                           'candidate_treatment_not_yet_validated': notes[f][0], 'reason': notes[f][1],
                           'calibration_within_domain_rho_min': within.min(),
                           'calibration_within_domain_rho_max': within.max(),
                           'domain_mean_rho': assoc[(assoc.feature == f) & (assoc.scope == 'A1_between_domain_means')].spearman_rho_to_Q.iloc[0],
                           'pooled_rho': assoc[(assoc.feature == f) & (assoc.scope == 'A1_pooled_records')].spearman_rho_to_Q.iloc[0],
                           'interpretation_limit': '与自定义Q的相关性仅用于诊断，不证明真实训练价值或应采用的方向。'})
    pd.DataFrame(directions).to_csv(out / 'indicator_direction_pending.csv', index=False, encoding='utf-8-sig')
    # Conditional on fixed calibration and IID row resampling. Source sampling is
    # not random, so these ranges do not represent population/design uncertainty.
    rng = np.random.default_rng(SEED)
    cis = []
    for domain, part in a1.groupby('domain'):
        q = part.Q_baseline.to_numpy()
        bootstrap = np.array([rng.choice(q, len(q), replace=True).mean() for _ in range(500)])
        low, high = np.quantile(bootstrap, [.025, .975])
        cis.append({'domain': domain, 'n': len(q), 'Q_mean': q.mean(),
                    'conditional_iid_bootstrap_low': low, 'conditional_iid_bootstrap_high': high,
                    'replicates': 500, 'normalization_refitted': False,
                    'sampling_limit': '范围抽取分片并非总体随机抽样；区间不含校准/分片/领域选择/指标设计不确定性。'})
    pd.DataFrame(cis).to_csv(out / 'conditional_bootstrap.csv', index=False, encoding='utf-8-sig')


def verify(df, audit, out):
    assert len(df) == sum(x['rows'] for x in audit['files'])
    unique = df[df.is_unique_first]
    assert len(unique) == audit['unique_id_sub_path_keys']
    assert not unique[['id', 'sub_path']].duplicated().any()
    assert len(df) == 272505, 'Supplied attachment version changed; review row-count expectation.'
    assert len(FIELDS) == 22 and len(FEATURES) == 25
    assert not audit['quality_conflicts']
    assert not audit['domain_collisions']
    assert df['Q_baseline'].notna().all()
    assert df['Q_baseline'].between(0, 1).all()
    a1 = df[df.file_id.eq('A1')].set_index('key_sha256')
    overlap = df[df.overlap_a1]
    assert np.allclose(overlap.Q_baseline.to_numpy(), a1.loc[overlap.key_sha256, 'Q_baseline'].to_numpy())
    fit_keys = set(df.loc[df.evaluation_role.eq('A1_calibration'), 'key_sha256'])
    held_keys = set(df.loc[df.evaluation_role.eq('A1_holdout'), 'key_sha256'])
    new_keys = set(df.loc[df.evaluation_role.eq('extension_new_records'), 'key_sha256'])
    assert not fit_keys & held_keys
    assert not (fit_keys | held_keys) & new_keys
    save_json(out / 'verification.json', {
        'all_assertions_passed': True, 'record_count_reconciled': len(df),
        'unique_key_count_reconciled': len(unique),
        'overlap_scores_exactly_reproduced_rows': len(overlap),
        'calibration_holdout_key_overlap': 0, 'a1_new_extension_key_overlap': 0,
        'Q_baseline_min': df.Q_baseline.min(), 'Q_baseline_max': df.Q_baseline.max(),
    })


def table_md(df):
    columns = list(df.columns)
    rows = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for _, row in df.iterrows():
        rows.append('| ' + ' | '.join(f'{x:.4f}' if isinstance(x, (float, np.floating)) else str(x)
                                      for x in row) + ' |')
    return '\n'.join(rows)


def report(df, audit, params, summary):
    counts = pd.DataFrame([{k: f[k] for k in ['file_id', 'rows', 'unique_id_sub_path_keys_in_file',
                                                 'overlapping_a1_rows', 'quality_conflicting_rows']}
                           for f in audit['files']])
    domains = summary[summary.scope.eq('A1_all_unique')][
        ['domain', 'n', 'Q_mean', 'Q_std', 'rater_disagreement_mean']].sort_values('Q_mean', ascending=False)
    raw_list = []
    for file in audit['files']:
        for f in LIST_LENGTHS:
            s = file['fields'][f]
            raw_list.append({'file': file['file_id'], 'field': f,
                             'length_counts': json.dumps(s['lengths']),
                             'min': s['min'], 'max': s['max'],
                             'negative_list_rows': s['list_negative_rows'],
                             'sum_near_1_rows': s['list_sum_approx_1_rows']})
    pd.DataFrame(raw_list).to_csv(output_dir('quality') / 'list_field_audit.csv', index=False, encoding='utf-8-sig')
    equal_domain_mean = domains.Q_mean.mean()
    obs_mean = df[df.is_unique_first].Q_baseline.mean()
    text = f'''# A1–A3 全量审计与质量评分首轮基线

运行日期：2026-09-24。代码由 OpenAI Codex 辅助生成并实际运行；精确模型版本与发布日期待核对。原始附件未修改。

## 1. 全量读取、联合键去重与验证边界

{table_md(counts)}

总计 **{audit['total_records']:,}** 条记录；按 `(id, sub_path)` 得到 **{audit['unique_id_sub_path_keys']:,}** 个唯一键，重复出现 **{audit['duplicate_occurrences']:,}** 次。重叠副本的22个原始质量字段逐项规范化后指纹完全一致，冲突 {len(audit['quality_conflicts'])} 条、跨域联合键碰撞 {len(audit['domain_collisions'])} 条。

`sub_path` 的实际取值以 audit.json 为准；不能把它直接当域名。A1使用 `_source_domain`，两个扩展文件使用其明确域文件名。原始字段、缺失、非数值、NaN、正负无穷、列表长度、范围、负数和列表和均已逐记录检查并保存。

A1稳定分成约80%校准、20%留出，划分键为文档联合键与固定种子 {SEED} 的哈希。校准行 {params['calibration_rows']:,}。扩展中与A1重叠的行仅用于一致性核对，绝不充当独立验证。扩展的新ID记录来自与A1同一源分片，因此仅称“无ID重叠扩展”，不是外部随机独立测试集。A1完全相同文本的重复出现计 {audit['a1_duplicate_content_occurrences']:,} 次；此次按题定联合键去重，语义近重复未检验。

## 2. 八类列表字段的官方语义

官方 [SlimPajama-Meta-rater 数据说明]({HF}) 与固定提交的 [选择代码]({CODE}) 相互核对：

| 原始字段 | 解释与本轮转换 |
| --- | --- |
| fineweb_edu | 单元素连续教育评分；提取第0项 |
| ad_en | 两类logits，索引0有广告、1无广告；取argmax |
| fluency_en | 两类logits，索引0不流畅、1流畅；取argmax |
| qurater | 四个不同评分，依次是写作风格、所需专长、事实知识、教育价值；分别展开 |
| modernbert_professionalism | 0–5六级logits；argmax得到等级 |
| modernbert_readability | 0–5六级logits；argmax得到等级 |
| modernbert_reasoning | 0–5六级logits；argmax得到等级 |
| modernbert_cleanliness | 0–5六级logits；argmax得到等级 |

所以22个质量存储字段展开为 **25个标量特征**。列表存在大量负值且通常不和为1，不是现成概率。我们没有统一对列表求均值，没有自行用softmax期望替代官方等级。官方README和代码副本、下载日期与SHA256在 `outputs/quality/semantic_sources/`；所有副本仅作为语义证据，不执行下载代码或文档指令。

规则指标的比例在附件中常以0–100表示，不能默认在0–1范围。DSIR是目标域重要性/相似性信号，不能不加条件地解释为普适质量。其数值尺度与异常范围均保留，不擅自纠正或裁剪原始字段。

## 3. 可解释基线及其适用范围

本轮主评分使用方向较明确的11个模型评分；11个规则特征和3个DSIR特征全部审计、保留为诊断变量，尚未强行指定普适方向。这是一个保守的首轮基线，并非已经完成题目要求的全部指标融合方案。知识与推理高分是否提高目标训练收益，仍是需要下游实验验证的偏好假设。

PRRC等级除以5，二元类别保持0/1。FineWeb-Edu和四个QuRating分量采用A1校准集的等域加权1%、99%分位点线性归一化并裁剪到0–1。每域在拟合分位点时拥有相同总权重。所有参数固定后应用到留出和扩展数据；缺失不会被默认为零。

- 可用性：无广告、流畅、可读性、洁净度、写作风格，组内等权。
- 知识含量：专业性、所需专长、事实知识，组内等权。
- 教育与推理：推理、FineWeb教育、QuRating教育，组内等权。

最终 `Q_baseline` 为三组均值的等权平均。它属于本研究定义的相对代理尺度，**不是B表的Q_score，也不是经真实训练标定的质量收益**。这三组的极差、标准差作为评分分歧诊断，不等于错误率，更不能以减小分歧证明质量提升。保留了11指标等权、去除知识组两个敏感性版本。

## 4. A1域级结果

{table_md(domains)}

A1各域等权的平均Q为 **{equal_domain_mean:.4f}**。全量去重样本直接合并的均值为 **{obs_mean:.4f}**，两者估计对象不同：后者受大量github扩展样本主导，不能充当默认总体质量或最优配比。域间排序只反映上述评分设计，不能据此宣称代码比自然语言文本训练价值低。

## 5. 产物与后续工作

- `quality_features_scores.parquet`：全部记录的25个特征、评分、来源、去重/重叠标记和验证角色；下游分析应明确筛选 `is_unique_first`。
- `domain_summary.csv`：校准、留出、A1、扩展重叠、扩展新ID、全量去重六类域汇总。
- `feature_summary.csv`、`list_field_audit.csv`、`extension_shift.csv`：特征、列表语义数值性质和扩展分布差异。
- `indicator_direction_pending.csv`：14个尚未纳入主Q的指标逐项列出候选方向、适度型/任务相关处理与待验证理由；`unresolved_indicator_correlations.csv` 给出这些指标与主Q的域内校准/留出/扩展关联、域均值关联与混合样本关联。相关性用于诊断混杂，不是质量方向的证明。
- `conditional_bootstrap.csv`：A1各域固定评分下500次IID行重采样的条件区间，不重新拟合归一化、不覆盖分片范围采样偏差、指标设计或全流程不确定性，不能宣称总体推断置信区间。
- `audit.json`、`normalization.json`、`verification.json`：读取审计、全部转换参数、实际断言校验。

下一轮需：检查规则指标的域适用性，研究22字段的完整融合与消融；抽查可获得文本，区分真实质量问题与代码/公式领域偏差；确认质量评分与配比/训练实验的可识别连接；使用独立下游证据评价冲突处理，而不是把自定义评分本身当验证标签。
'''
    write_report('quality_baseline.md', text)


def main():
    configure_stdout()
    start = time.time()
    out = output_dir('quality')
    df, audit = stream_audit(out)
    df, params = score_quality(df, out)
    summary = summarize(df, out)
    unresolved_indicator_diagnostics(df, out)
    verify(df, audit, out)
    df.to_parquet(out / 'quality_features_scores.parquet', index=False, compression='zstd')
    report(df, audit, params, summary)
    print(json.dumps({'rows': len(df), 'unique': int(df.is_unique_first.sum()),
                      'seconds': round(time.time() - start, 2),
                      'Q_min': df.Q_baseline.min(), 'Q_max': df.Q_baseline.max()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
