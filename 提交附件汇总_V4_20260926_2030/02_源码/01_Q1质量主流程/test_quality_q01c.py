# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""Standalone runner for the TASK-Q01C synthetic tests.

Writes its own test run directory (never the formal output directory) and exits
non-zero when any synthetic test fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
if str(SOLUTION / 'src') not in sys.path:
    sys.path.insert(0, str(SOLUTION / 'src'))

import quality_q01c_selftest as selftest  # noqa: E402

CST = timezone(timedelta(hours=8))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C synthetic test runner')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--out-root', default=str(SOLUTION / 'outputs' / 'quality_q01c_tests'))
    args = parser.parse_args(argv)
    out_dir = Path(args.out_root) / args.run_id
    if out_dir.exists():
        print(f'test run directory exists, refusing to overwrite: {out_dir}', flush=True)
        return 3
    out_dir.mkdir(parents=True)
    report = selftest.run_all_tests()
    report.update({'test_run_id': args.run_id,
                   'generated_local': datetime.now(CST).isoformat(timespec='seconds'),
                   'synthetic_only': True,
                   'note': 'artificial counts; never mixed into real statistics'})
    (out_dir / 'synthetic_tests.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Q01C synthetic tests', '',
             f"- status: {report['status']}", f"- tests: {report['n_tests']}",
             f"- failed: {report['n_failed']}", '']
    for item in report['tests']:
        lines.append(f"- [{item['status']}] {item['test']}")
    (out_dir / 'synthetic_tests.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'n_tests': report['n_tests'],
                      'n_failed': report['n_failed'], 'out_dir': str(out_dir)}, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
