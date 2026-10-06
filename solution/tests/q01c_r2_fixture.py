"""TASK-Q01C-R2 synthetic fixture wrapper (no real attachment access)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import q01c_r1_fixture as base_fixture  # noqa: E402  (fixture definition is shared, synthetic only)


def main(argv=None):
    parser = argparse.ArgumentParser(description='build the Q01C-R2 synthetic fixture')
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args(argv)
    manifest = base_fixture.build(args.out_dir)
    manifest['r2_wrapper'] = 'solution/tests/q01c_r2_fixture.py'
    Path(args.out_dir, 'fixture_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'fixture_id': manifest['fixture_id'], 'rows': manifest['expected_rows'],
                      'expected_q_valid': manifest['expected_q_valid'],
                      'expected_q_missing': manifest['expected_q_missing']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
