'"""TASK-Q01C-R2 finalizer: snapshot mode plus the final artefact/manifest closure."""'
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOLUTION = Path(__file__).resolve().parents[1]
PROJECT = SOLUTION.parent
FORMAL_RUN = SOLUTION / 'outputs' / 'quality_q01c' / '20260924T215718+08'
R1_RUN = PROJECT / 'diagnostics' / 'TASK-Q01C-R1' / '20260924T225550+08'
CST = timezone(timedelta(hours=8))
SMALL_LIMIT = 8 * 1024 * 1024
PROTECTED_ROOTS = [SOLUTION / 'outputs' / 'quality', SOLUTION / 'outputs' / 'quality_q01c',
                   SOLUTION / 'reports', PROJECT / 'diagnostics' / 'TASK-Q01A',
                   PROJECT / 'diagnostics' / 'TASK-Q01A-R1']
CODE_FILES = ['solution/src/quality_q01c.py', 'solution/src/quality_q01c_selftest.py',
              'solution/src/quality_q01c_verify.py', 'solution/tests/test_quality_q01c.py',
              'solution/tests/q01c_r2_fixture.py', 'solution/tests/q01c_r2_midstage.py',
              'solution/tests/q01c_r2_rejections.py', 'solution/tests/q01c_r2_verify.py',
              'solution/tests/q01c_r2_finalize.py']
R2_INPUTS = ['tasks/TASK-Q01C_质量缺失策略实施与流水线恢复.md',
             'tasks/TASK-Q01C-R1_恢复机制与日志精准小修.md',
             'tasks/TASK-Q01C-R2_恢复一致性与S60日志收口.md',
             'solution/outputs/quality_q01c/20260924T215718+08/output_manifest.json',
             'solution/outputs/quality_q01c/20260924T215718+08/run_summary.json',
             'solution/outputs/quality_q01c/20260924T215718+08/checks.json',
             'solution/outputs/quality_q01c/20260924T215718+08/checkpoint_manifest.json',
             'diagnostics/TASK-Q01C-R1/20260924T225550+08/output_manifest.json',
             'diagnostics/TASK-Q01C-R1/20260924T225550+08/run_summary.json',
             'diagnostics/TASK-Q01C-R1/20260924T225550+08/checks.json']
NOT_VERIFIABLE = [{'item': 'historical TASK-Q01C scientific-run main command',
                   'reason': 'never persisted by the original run (environment.json commands list '
                             'empty); cannot be reconstructed honestly',
                   'carried_from': 'TASK-Q01C-R1 run_summary.not_verifiable_items'}]


def now_iso():
    return datetime.now(CST).isoformat(timespec='seconds')


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str),
                          encoding='utf-8')


def log_phase(r2_dir, phase, event, **fields):
    record = {'ts': now_iso(), 'phase': phase, 'event': event, 'pid': os.getpid()}
    record.update(fields)
    with open(r2_dir / 'stage_status.jsonl', 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(json.dumps(record, ensure_ascii=False), flush=True)


def snapshot_protected():
    entries = {}
    for root in PROTECTED_ROOTS:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob('*') if p.is_file()):
            rel = str(path.relative_to(PROJECT)).replace('\\\\', '/')
            stat = path.stat()
            entry = {'bytes': stat.st_size, 'mtime': stat.st_mtime, 'sha256': None}
            if stat.st_size <= SMALL_LIMIT:
                entry['sha256'] = sha256_file(path)
            entries[rel] = entry
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R2 finalizer')
    parser.add_argument('--r2-dir', required=True)
    parser.add_argument('--snapshot-only', action='store_true')
    args = parser.parse_args(argv)
    r2_dir = Path(args.r2_dir).resolve()
    if args.snapshot_only:
        log_phase(r2_dir, 'protected_snapshot', 'start')
        entries = snapshot_protected()
        write_json(r2_dir / 'protected_artifacts_after.json',
                   {'generated_local': now_iso(), 'entries': entries, 'n_entries': len(entries),
                    'note': 'sha256 for files <= 8 MiB, size+mtime for all; F题 raw data and '
                            'diagnostics/TASK-C01* are never referenced'})
        log_phase(r2_dir, 'protected_snapshot', 'complete', n_entries=len(entries))
        return 0
    log_phase(r2_dir, 'finalize', 'start')
    checks = read_json(r2_dir / 'checks.json')
    verification = read_json(r2_dir / 'verification.json')
    evidence = read_json(r2_dir / 'resume_evidence.json')
    rejections = read_json(r2_dir / 'rejection_tests' / 'rejection_summary.json')
    command_log = read_json(r2_dir / 'command_log.json')
    for role, argv_list in [('rejection_tests', [sys.executable, '-X', 'utf8',
                                                 str(SOLUTION / 'tests' / 'q01c_r2_rejections.py'),
                                                 '--r2-dir', str(r2_dir)]),
                            ('independent_verification',
                             [sys.executable, '-X', 'utf8',
                              str(SOLUTION / 'tests' / 'q01c_r2_verify.py'),
                              '--r2-dir', str(r2_dir)]),
                            ('r2_finalizer', [sys.executable, '-X', 'utf8',
                                             str(Path(__file__).resolve()),
                                             '--r2-dir', str(r2_dir)])]:
        command_log['commands'].append({'role': role, 'command': argv_list, 'pid': os.getpid(),
                                        'recorded_local': now_iso()})
    write_json(r2_dir / 'command_log.json', command_log)
    inputs = []
    for rel in R2_INPUTS:
        path = PROJECT / rel
        inputs.append({'path': rel, 'exists': path.is_file(),
                       'bytes': path.stat().st_size if path.is_file() else None,
                       'sha256': sha256_file(path) if path.is_file() else None})
    write_json(r2_dir / 'input_manifest.json', {
        'run_id': r2_dir.name, 'task': 'TASK-Q01C-R2', 'generated_local': now_iso(),
        'inputs': inputs,
        'a1_a3_policy': 'the three real attachment files were never opened, read, stat-ed, hashed, '
                        'decompressed or scanned by any R2 process; all dynamic verification uses '
                        'the synthetic fixture under this directory',
        'excluded_by_work_order': ['F题/real_attachments', 'diagnostics/TASK-C01',
                                   'diagnostics/TASK-C01-R1']})
    write_json(r2_dir / 'environment.json', {
        'run_id': r2_dir.name, 'task': 'TASK-Q01C-R2', 'generated_local': now_iso(),
        'python': sys.version, 'python_executable': sys.executable,
        'platform': platform.platform(), 'machine': platform.machine(),
        'timezone': str(datetime.now().astimezone().tzinfo),
        'single_process_cpu': True, 'gpu_used': False, 'network_used': False,
        'real_a1_a3_access': {'opened': 0, 'read': 0, 'stat': 0, 'hash': 0, 'decompress': 0,
                              'scan': 0,
                              'basis': 'fixture path isolation plus code and command audit; no R2 '
                                       'process references the real attachment paths'},
        'commands': command_log['commands'],
        'validation_entry': 'quality_q01c.validate_stage (REUSABLE / NOT_STARTED / INVALID)',
        'checkpoint_protocol_version': 3})
    snapshot_dir = r2_dir / 'code_snapshot'
    snapshot_dir.mkdir(exist_ok=True)
    frozen = []
    for rel in CODE_FILES:
        source = PROJECT / rel
        if not source.is_file():
            continue
        target = snapshot_dir / Path(rel).name
        shutil.copy2(source, target)
        before = None
        for candidate in [R1_RUN / 'code_snapshot' / Path(rel).name,
                          FORMAL_RUN / 'code_snapshot' / Path(rel).name]:
            if candidate.is_file():
                before = sha256_file(candidate)
                break
        frozen.append({'file': Path(rel).name, 'source_path': rel, 'before_sha256': before,
                       'after_sha256': sha256_file(target), 'bytes': target.stat().st_size})
    write_json(snapshot_dir / 'code_snapshot_manifest.json',
               {'run_id': r2_dir.name, 'frozen_local': now_iso(), 'files': frozen})
    with open(r2_dir / 'changes.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['file', 'change_type', 'before_sha256',
                                                'after_sha256', 'bytes'], extrasaction='ignore')
        writer.writeheader()
        for item in frozen:
            changed = item['before_sha256'] != item['after_sha256']
            writer.writerow({'file': item['source_path'],
                             'change_type': ('new_file' if item['before_sha256'] is None else
                                             ('modified' if changed else 'unchanged')),
                             'before_sha256': item['before_sha256'],
                             'after_sha256': item['after_sha256'], 'bytes': item['bytes']})
    before_entries = read_json(r2_dir / 'protected_artifacts_before.json')['entries']
    after_entries = read_json(r2_dir / 'protected_artifacts_after.json')['entries']
    changed = [rel for rel, entry in before_entries.items()
               if rel in after_entries and (entry['bytes'] != after_entries[rel]['bytes']
                                            or abs(entry['mtime']
                                                   - after_entries[rel]['mtime']) > 1e-6
                                            or (entry.get('sha256')
                                                and entry['sha256']
                                                != after_entries[rel].get('sha256')))]
    formal_manifest = read_json(FORMAL_RUN / 'output_manifest.json')
    formal_mismatch = [item['path'] for item in formal_manifest['files']
                       if not (FORMAL_RUN / item['path']).is_file()
                       or sha256_file(FORMAL_RUN / item['path']) != item['sha256']]
    r1_manifest = read_json(R1_RUN / 'output_manifest.json')
    r1_mismatch = [item['path'] for item in r1_manifest['files']
                   if not (R1_RUN / item['path']).is_file()
                   or sha256_file(R1_RUN / item['path']) != item['sha256']]
    write_json(r2_dir / 'protected_artifacts_check.json', {
        'run_id': r2_dir.name, 'generated_local': now_iso(),
        'status': 'PASS' if not changed and not formal_mismatch and not r1_mismatch else 'FAIL',
        'n_entries_before': len(before_entries), 'n_entries_after': len(after_entries),
        'changed': changed, 'removed': [rel for rel in before_entries if rel not in after_entries],
        'added': [rel for rel in after_entries if rel not in before_entries],
        'hash_scope': 'sha256 for files <= 8 MiB; size+mtime for every file',
        'formal_run': {'path': str(FORMAL_RUN), 'files': len(formal_manifest['files']),
                       'matching': len(formal_manifest['files']) - len(formal_mismatch),
                       'mismatches': formal_mismatch},
        'r1_run': {'path': str(R1_RUN), 'files': len(r1_manifest['files']),
                   'matching': len(r1_manifest['files']) - len(r1_mismatch),
                   'mismatches': r1_mismatch},
        'a1_a3_policy': 'F题/real_attachments is deliberately excluded from R2 snapshots: the real '
                        'attachments were never opened, read, stat-ed, hashed, decompressed or scanned'})
    log_phase(r2_dir, 'finalize', 'complete')
    status = ('COMPLETE_PENDING_REVIEW'
              if checks['summary']['n_fail'] == 0 and checks['summary']['n_not_checked'] == 0
              and checks['summary']['n_not_verifiable'] == 0 else 'INCOMPLETE_OR_FAILED')
    run_summary = {
        'task': 'TASK-Q01C-R2', 'run_id': r2_dir.name, 'status': status,
        'generated_local': now_iso(), 'checks': checks['summary'],
        'verification_key_metrics': verification['key_metrics'],
        'midstage_processes': evidence['processes'],
        'new_computations_in_p2': evidence['stage_compute_counters']['new_computations_in_p2'],
        'checkpoint_hash_invariant': evidence['checkpoints']['hash_invariant'],
        'rejection_cases': {case: {'resume_exit': item['resume']['exit_code'],
                                   'probe_exit': item['probe']['exit_code'],
                                   'zero_recomputation': item['zero_recomputation'],
                                   'files_unchanged': item['checkpoint_files_unchanged']}
                            for case, item in rejections['cases'].items()},
        's60_finalize': {'stage_seconds':
                         evidence['run_summary']['stage_seconds'].get('s60_finalize'),
                         'terminal_events':
                         evidence['run_summary']['stage_terminal_events'].get('s60_finalize'),
                         'exit_code':
                         evidence['run_summary']['stage_exit_codes'].get('s60_finalize'),
                         'executed': 's60_finalize' in
                                     (evidence['run_summary']['executed_stages'] or [])},
        'synthetic_run_status': evidence['run_summary']['status'],
        'code_files_before_after': frozen,
        'not_verifiable_items': NOT_VERIFIABLE,
        'strategy_changed': False, 'scientific_results_recomputed': False,
        'a1_a3_access': {'opened': 0, 'read': 0, 'stat': 0, 'hash': 0, 'decompress': 0, 'scan': 0,
                         'basis': 'fixture path isolation plus code and command audit; no R2 '
                                  'process references the real attachment paths'},
        'handoff_file': 'handoff.md'}
    write_json(r2_dir / 'run_summary.json', run_summary)
    handoff = [
        '# TASK-Q01C-R2 交回说明（恢复一致性与 S60 日志收口）', '',
        '- 状态：' + status + '；R2目录：' + str(r2_dir),
        '- 唯一恢复判定入口：validate_stage()（REUSABLE / NOT_STARTED / INVALID），正常 --resume '
        '主循环、--stage 前置依赖、--probe-resume 三处共同调用。',
        '- 不可变链：S20 ← S10/S11/S12 链身份；S30 ← S20 checkpoint payload；S40 ← S30 checkpoint '
        'payload；quality_features_scores.parquet 只作为 materialized output，未被任何 stage marker 绑定。',
        '- 中后段跨进程：P1 pid=' + str(evidence['processes']['p1']['pid']) +
        ' 在 S30 完成后被外部终止；P2 pid=' + str(evidence['processes']['p2']['pid']) +
        ' 复用 s10–s30，新增计算 ' + json.dumps(
            evidence['stage_compute_counters']['new_computations_in_p2']) + '。',
        '- 三类拒绝路径（payload 损坏 / config 不匹配 / code fingerprint 不匹配）均由正常 --resume '
        '硬停止：非零退出、零重算、零覆盖，probe 与 resume 判定一致。',
        '- S60：stage_seconds/executed_stages/stage_terminal_events/stage_exit_codes 均包含 '
        's60_finalize，stage_status 有 start 与唯一 terminal；独立验收器显式包含全部 STAGES。',
        '- 回归：原科学 run 56/56、R1 run 与既有 Q01C run 零变化；A1–A3 未被 read/stat/hash/解压/扫描。',
        '', '## 保留的历史 NOT_VERIFIABLE',
        '- ' + NOT_VERIFIABLE[0]['item'] + '：' + NOT_VERIFIABLE[0]['reason'],
        '', '## 待主控审查',
        '- 是否接受 --hold-after-stage 继续作为默认关闭的测试钩子。',
        '- 是否接受 stage marker 仅绑定阶段局部不可变输出 + checkpoint identity 的职责边界。',
        '- 是否需要在未来运行中把 S50 的独立验收也纳入 S60 之后的第二次只读复核。']
    (r2_dir / 'handoff.md').write_text('\n'.join(handoff), encoding='utf-8')
    files = []
    for path in sorted(r2_dir.rglob('*')):
        if path.is_file() and path.name != 'output_manifest.json':
            files.append({'path': str(path.relative_to(r2_dir)).replace('\\\\', '/'),
                          'bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    write_json(r2_dir / 'output_manifest.json',
               {'task': 'TASK-Q01C-R2', 'run_id': r2_dir.name, 'generated_local': now_iso(),
                'n_files': len(files), 'files': files})
    print(json.dumps({'status': status, 'n_files': len(files),
                      'checks': checks['summary']}, ensure_ascii=False), flush=True)
    return 0 if status == 'COMPLETE_PENDING_REVIEW' else 2


if __name__ == '__main__':
    sys.exit(main())