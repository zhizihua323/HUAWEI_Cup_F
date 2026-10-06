"""TASK-Q01C-R1 synthetic fixture generator.

Builds a small, fully synthetic attachment set with the same 22 fields, the same
stable-hash split rule and the same file labels as the real attachments, so that
the Q01C recovery/replay path can be exercised end to end without ever touching
A1-A3. Field lists are declared here explicitly and cross-checked against the
pipeline constants (drift guard).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
SRC = SOLUTION / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import quality_q01c as pipeline  # noqa: E402  (constants only)

RULES = ['rps_doc_frac_no_alph_words', 'rps_doc_mean_word_length',
         'rps_doc_frac_unique_words', 'rps_doc_unigram_entropy', 'rps_doc_word_count',
         'rps_lines_ending_with_terminal_punctution_mark',
         'rps_lines_numerical_chars_fraction', 'rps_lines_uppercase_letter_fraction',
         'rps_doc_num_sentences', 'rps_doc_frac_chars_top_2gram',
         'rps_doc_frac_chars_top_3gram']
DSIR = ['dsir_books', 'dsir_wiki', 'dsir_math']
PRRC = ['modernbert_professionalism', 'modernbert_readability', 'modernbert_reasoning',
        'modernbert_cleanliness']
QURATER = ['qurater_writing_style', 'qurater_required_expertise', 'qurater_facts_trivia',
           'qurater_educational_value']
FIELDS = RULES + DSIR + ['fineweb_edu', 'ad_en', 'fluency_en', 'qurater'] + PRRC
MODEL = ['fineweb_edu', 'ad_en', 'fluency_en'] + QURATER + PRRC
SEED = 20260924
DOMAINS_FILE1 = ['commoncrawl', 'wikipedia', 'github']
MISSING_CASES = [
    {'file_id': 'A1', 'domain': 'commoncrawl', 'feature': 'modernbert_professionalism',
     'list_field': 'modernbert_professionalism', 'role_hint': 'non_calibration'},
    {'file_id': 'A3_github', 'domain': 'github', 'feature': 'modernbert_professionalism',
     'list_field': 'modernbert_professionalism', 'role_hint': 'extension_new'},
]


def split_remainder(key_json):
    digest = hashlib.sha256((str(SEED) + key_json).encode('utf-8')).hexdigest()
    return int(digest[:16], 16) % 5


def key_json_for(identifier, sub_path):
    return json.dumps((str(identifier), str(sub_path)), ensure_ascii=False, separators=(',', ':'))


def scalar_value(field, index):
    value = (index % 17) / 17.0
    if field == 'rps_doc_word_count':
        return 120.0 + 37.0 * (index % 53)
    if field == 'rps_doc_num_sentences':
        return 5.0 + (index % 41)
    if field == 'rps_doc_mean_word_length':
        return 3.5 + (index % 23) / 3.0
    if field == 'rps_doc_unigram_entropy':
        return 3.0 + 4.0 * value
    if field in ('dsir_books', 'dsir_wiki', 'dsir_math'):
        return -60000.0 + 5000.0 * (index % 25)
    return value


def make_row(domain, index, identifier, sub_path, missing_list_field=None, with_source_domain=True):
    row = {'id': identifier, 'sub_path': sub_path}
    if with_source_domain:
        row['_source_domain'] = domain
    for field in RULES + DSIR:
        row[field] = scalar_value(field, index)
    row['fineweb_edu'] = [round(0.2 + 0.05 * (index % 60), 4)]
    row['ad_en'] = [0.9, 0.1] if index % 7 == 0 else [0.05, 0.95]
    row['fluency_en'] = [0.1, 0.9] if index % 5 else [0.8, 0.2]
    row['qurater'] = [round(0.5 * ((index + offset) % 13) - 3.0, 4) for offset in range(4)]
    for offset, feature in enumerate(PRRC):
        if feature == missing_list_field:
            row[feature] = [float('nan')] * 6
        else:
            row[feature] = [round(0.2 * ((index + offset + level) % 7), 4) for level in range(6)]
    return row


def write_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, allow_nan=True) + '\n')


def build(out_dir):
    out_dir = Path(out_dir)
    inputs = out_dir / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    if [RULES, DSIR, PRRC, QURATER] != [pipeline.RULES, pipeline.DSIR, pipeline.PRRC,
                                         pipeline.QURATER]:
        raise SystemExit('fixture field specification drifted from the pipeline constants')
    if MODEL != pipeline.MODEL:
        raise SystemExit('fixture model feature order drifted from the pipeline constants')
    rows_file1 = []
    per_domain = 200
    calibration_counts = {}
    for domain in DOMAINS_FILE1:
        for index in range(per_domain):
            identifier = f'{domain}-{index:04d}'
            sub_path = f'{domain}/part-{index % 4}.txt'
            missing = None
            for case in MISSING_CASES:
                if (case['file_id'] == 'A1' and case['domain'] == domain
                        and index == 11 and case['role_hint'] == 'non_calibration'):
                    missing = case['list_field']
            row = make_row(domain, index, identifier, sub_path, missing)
            rows_file1.append(row)
            remainder = split_remainder(key_json_for(identifier, sub_path))
            if remainder != 0:
                calibration_counts[domain] = calibration_counts.get(domain, 0) + 1
    for domain, count in calibration_counts.items():
        if count < 110:
            raise SystemExit(f'fixture calibration count too small for {domain}: {count}')
    rows_file2 = [make_row('arxiv', 1000 + index, f'arxiv-{index:04d}', f'arxiv/part-{index % 3}.txt',
                           with_source_domain=False) for index in range(30)]
    rows_file3 = []
    for index in range(30):
        identifier = f'github-ext-{index:04d}'
        sub_path = f'github/part-{index % 3}.txt'
        missing = 'modernbert_professionalism' if index == 7 else None
        rows_file3.append(make_row('github', 2000 + index, identifier, sub_path, missing,
                                   with_source_domain=False))
    files = [('f1_a1.jsonl', rows_file1), ('f2_arxiv.jsonl', rows_file2), ('f3_github.jsonl', rows_file3)]
    for name, rows in files:
        write_jsonl(inputs / name, rows)
    missing_rows = len(rows_file1) and 1 + 1  # one in file 1, one in file 3
    manifest = {
        'fixture_id': 'q01c_r1_fixture_v1',
        'synthetic': True,
        'protocol_version': pipeline.PROTOCOL_VERSION,
        'description': 'synthetic run used by TASK-Q01C-R1 to prove cross-process checkpoint reuse; '
                       'contains no real attachment data',
        'files': [
            {'file_id': 'A1', 'path': 'inputs/f1_a1.jsonl', 'fallback_domain': None,
             'stage': 's10_scan_a1'},
            {'file_id': 'A2_arxiv', 'path': 'inputs/f2_arxiv.jsonl', 'fallback_domain': 'arxiv',
             'stage': 's11_scan_a2'},
            {'file_id': 'A3_github', 'path': 'inputs/f3_github.jsonl', 'fallback_domain': 'github',
             'stage': 's12_scan_a3'}],
        'expected_rows': {'A1': len(rows_file1), 'A2_arxiv': len(rows_file2),
                          'A3_github': len(rows_file3)},
        'expected_rows_total': len(rows_file1) + len(rows_file2) + len(rows_file3),
        'expected_q_missing': 2,
        'expected_q_missing_physical': 2,
        'expected_q_valid': len(rows_file1) + len(rows_file2) + len(rows_file3) - 2,
        'expected_q_valid_physical': len(rows_file1) + len(rows_file2) + len(rows_file3) - 2,
        'expected_imputed_rows': 2,
        'expected_calibration_domain_counts': calibration_counts,
        'missing_cases': MISSING_CASES,
        'input_sha256': {name: hashlib.sha256((inputs / name).read_bytes()).hexdigest()
                         for name, _rows in files},
        'generator': 'solution/tests/q01c_r1_fixture.py'}
    (out_dir / 'fixture_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='build the Q01C-R1 synthetic fixture')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args(argv)
    manifest = build(args.out_dir)
    print(json.dumps({'fixture_id': manifest['fixture_id'],
                      'rows': manifest['expected_rows'],
                      'input_sha256': manifest['input_sha256']}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
