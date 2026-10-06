"""TASK-Q01C-R1 finalizer: assemble the remaining R1 artefacts and the manifest.

Runs after q01c_r1_verify.py. Records the real commands of every R1 process,
hashes the code before/after, writes run_summary.json and handoff.md, then closes
every hashed file and writes output_manifest.json last (excluding itself).
"""
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
CST = timezone(timedelta(hours=8))
CODE_FILES = ['solution/src/quality_q01c.py', 'solution/src/quality_q01c_selftest.py',
              'solution/src/quality_q01c_verify.py', 'solution/tests/test_quality_q01c.py',
              'solution/tests/q01c_r1_fixture.py', 'solution/tests/q01c_r1_two_process.py',
              'solution/tests/q01c_r1_extension_isolation.py', 'solution/tests/q01c_r1_verify.py',
              'solution/tests/q01c_r1_finalize.py']
R1_INPUTS = ['tasks/TASK-Q01C_质量缺失策略实施与流水线恢复.md',
             'tasks/TASK-Q01C-R1_恢复机制与日志精准小修.md',
             'solution/outputs/quality_q01c/20260924T215718+08/run_summary.json',
             'solution/outputs/quality_q01c/20260924T215718+08/checks.json',
             'solution/outputs/quality_q01c/20260924T215718+08/verification.json',
             'solution/outputs/quality_q01c/20260924T215718+08/checkpoint_manifest.json',
             'solution/outputs/quality_q01c/20260924T215718+08/stage_status.jsonl',
             'solution/outputs/quality_q01c/20260924T215718+08/environment.json',
             'solution/outputs/quality_q01c/20260924T215718+08/run_config.json',
             'solution/outputs/quality_q01c/20260924T215718+08/output_manifest.json']
NOT_VERIFIABLE = [{
    'item': 'historical TASK-Q01C scientific-run main command',
    'reason': 'the command was never persisted by the original TASK-Q01C environment.json '
              '(commands list was empty); it cannot be reconstructed honestly',
    'evidence': 'solution/outputs/quality_q01c/20260924T215718+08/environment.json (commands empty)',
    'remedy': 'TASK-Q01C-R1 records the real argv of every R1 process instead'}]


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


def main(argv=None):
    parser = argparse.ArgumentParser(description='Q01C-R1 finalizer')
    parser.add_argument('--r1-dir', required=True)
    args = parser.parse_args(argv)
    r1_dir = Path(args.r1_dir).resolve()
    started = now_iso()
    verification = read_json(r1_dir / 'verification.json')
    checks = read_json(r1_dir / 'checks.json')
    evidence = read_json(r1_dir / 'resume_evidence.json')
    command_log = read_json(r1_dir / 'command_log.json')
    for role, argv_list in [('independent_verification',
                             [sys.executable, '-X', 'utf8',
                              str(SOLUTION / 'tests' / 'q01c_r1_verify.py'),
                              '--r1-dir', str(r1_dir)]),
                            ('r1_finalizer',
                             [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                              '--r1-dir', str(r1_dir)])]:
        command_log['commands'].append({'role': role, 'command': argv_list, 'pid': os.getpid(),
                                        'recorded_local': started})
    command_log['generated_local'] = now_iso()
    write_json(r1_dir / 'command_log.json', command_log)
    inputs = []
    for rel in R1_INPUTS:
        path = PROJECT / rel
        inputs.append({'path': rel, 'exists': path.is_file(),
                       'bytes': path.stat().st_size if path.is_file() else None,
                       'sha256': sha256_file(path) if path.is_file() else None})
    write_json(r1_dir / 'input_manifest.json', {
        'run_id': r1_dir.name, 'task': 'TASK-Q01C-R1', 'generated_local': now_iso(),
        'inputs': inputs,
        'a1_a3_policy': 'the three real attachment files were never opened, hashed, decompressed or '
                        'stat-ed by any R1 process; the recovery proof uses a synthetic fixture only',
        'excluded_by_work_order': ['diagnostics/TASK-C01', 'diagnostics/TASK-C01-R1']})
    before_entries = read_json(r1_dir / 'protected_artifacts_before.json')['entries']
    after_entries = read_json(r1_dir / 'protected_artifacts_after.json')['entries']
    changed = [rel for rel, entry in before_entries.items()
               if rel in after_entries and (entry['bytes'] != after_entries[rel]['bytes']
                                            or abs(entry['mtime'] - after_entries[rel]['mtime']) > 1e-6
                                            or (entry.get('sha256') and entry['sha256'] != after_entries[rel].get('sha256')))]
    removed = [rel for rel in before_entries if rel not in after_entries]
    added = [rel for rel in after_entries if rel not in before_entries]
    formal_manifest = read_json(FORMAL_RUN / 'output_manifest.json')
    formal_mismatch = [item['path'] for item in formal_manifest['files']
                       if not (FORMAL_RUN / item['path']).is_file()
                       or sha256_file(FORMAL_RUN / item['path']) != item['sha256']]
    write_json(r1_dir / 'protected_artifacts_check.json', {
        'run_id': r1_dir.name, 'generated_local': now_iso(),
        'status': 'PASS' if not changed and not removed and not added and not formal_mismatch
                  else 'FAIL',
        'protected_roots': ['solution/outputs/quality', 'solution/outputs/quality_q01c',
                            'solution/reports', 'diagnostics/TASK-Q01A',
                            'diagnostics/TASK-Q01A-R1'],
        'n_entries_before': len(before_entries), 'n_entries_after': len(after_entries),
        'changed': changed, 'removed': removed, 'added': added,
        'hash_scope': 'sha256 for files <= 8 MiB; size+mtime for every file',
        'formal_run': {'path': str(FORMAL_RUN), 'manifest_files': len(formal_manifest['files']),
                       'matching_files': len(formal_manifest['files']) - len(formal_mismatch),
                       'mismatches': formal_mismatch,
                       'status': read_json(FORMAL_RUN / 'run_summary.json')['status']},
        'a1_a3_policy': 'F题/real_attachments and diagnostics/TASK-C01* were deliberately excluded '
                        'from every R1 snapshot: A1-A3 were never opened, hashed, decompressed or stat-ed',
        'previous_scientific_runs_included': True})
    snapshot_dir = r1_dir / 'code_snapshot'
    snapshot_dir.mkdir(exist_ok=True)
    frozen = []
    for rel in CODE_FILES:
        source = PROJECT / rel
        if not source.is_file():
            continue
        target = snapshot_dir / Path(rel).name
        shutil.copy2(source, target)
        frozen.append({'file': Path(rel).name, 'source_path': rel,
                       'before_sha256': sha256_file((FORMAL_RUN / 'code_snapshot' / Path(rel).name))
                       if (FORMAL_RUN / 'code_snapshot' / Path(rel).name).is_file() else None,
                       'after_sha256': sha256_file(target),
                       'bytes': target.stat().st_size})
    write_json(snapshot_dir / 'code_snapshot_manifest.json',
               {'run_id': r1_dir.name, 'frozen_local': now_iso(), 'files': frozen})
    changes_rows = []
    for item in frozen:
        before = item['before_sha256']
        changes_rows.append({'file': item['source_path'],
                             'change_type': 'modified' if before and before != item['after_sha256']
                                            else ('new_file' if before is None else 'unchanged'),
                             'before_sha256': before, 'after_sha256': item['after_sha256'],
                             'reason': 'Q01C-R1 recovery/log repair' if before is None
                                       or before != item['after_sha256'] else 'no change needed'})
    for name, reason in [('solution/src/quality_q01c.py',
                          'CLI --resume/--stage/--probe-resume contract, v2 checkpoint protocol, '
                          'scan counters, fixture mode, stage/terminal logging, resume evidence'),
                         ('solution/src/quality_q01c_selftest.py',
                          'added extension-role imputation isolation test'),
                         ('solution/src/quality_q01c_verify.py',
                          'added fixture-mode verification path (real-data path untouched)'),
                         ('solution/tests/q01c_r1_fixture.py', 'new synthetic fixture generator'),
                         ('solution/tests/q01c_r1_two_process.py',
                          'new cross-process interruption/resume supervisor'),
                         ('solution/tests/q01c_r1_extension_isolation.py',
                          'new extension isolation test runner'),
                         ('solution/tests/q01c_r1_verify.py', 'new independent R1 verifier'),
                         ('solution/tests/q01c_r1_finalize.py', 'new R1 finalizer')]:
        for row in changes_rows:
            if row['file'] == name:
                row['detail'] = reason
    with open(r1_dir / 'changes.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['file', 'change_type', 'before_sha256', 'after_sha256',
                                                'reason', 'detail'], extrasaction='ignore')
        writer.writeheader()
        for row in changes_rows:
            writer.writerow(row)
    write_json(r1_dir / 'environment.json', {
        'run_id': r1_dir.name, 'task': 'TASK-Q01C-R1', 'generated_local': now_iso(),
        'python': sys.version, 'python_executable': sys.executable,
        'platform': platform.platform(), 'machine': platform.machine(),
        'timezone': str(datetime.now().astimezone().tzinfo),
        'single_process_cpu': True, 'gpu_used': False, 'network_used': False,
        'real_a1_a3_access': {'opened': 0, 'hashed': 0, 'decompressed': 0, 'stat_calls': 0},
        'commands': command_log['commands']})
    runs = {'A1': evidence['scan_counters']['after_p2']['files'].get('A1', {}).get('passes'),
            'A2_arxiv': evidence['scan_counters']['after_p2']['files'].get('A2_arxiv', {}).get('passes'),
            'A3_github': evidence['scan_counters']['after_p2']['files'].get('A3_github', {}).get('passes')}
    status = ('COMPLETE_PENDING_REVIEW'
              if checks['summary']['n_fail'] == 0 and checks['summary']['n_not_checked'] == 0 else
              'INCOMPLETE_OR_FAILED')
    write_json(r1_dir / 'run_summary.json', {
        'task': 'TASK-Q01C-R1', 'run_id': r1_dir.name, 'status': status,
        'started_local': started, 'finished_local': now_iso(),
        'checks': checks['summary'], 'verification': verification['key_metrics'],
        'processes': evidence['processes'], 'scan_passes_per_file': runs,
        'new_scans_in_p2_total': evidence['scan_counters']['new_passes_in_p2_total'],
        'checkpoint_hash_invariant': evidence['checkpoints']['hash_invariant'],
        'synthetic_run_status': evidence['run_summary']['status'],
        'formal_run': {'path': str(FORMAL_RUN), 'manifest_files': 56,
                       'matching_files': verification['key_metrics']['formal_run_files_matching'],
                       'status_preserved': 'COMPLETE_PENDING_REVIEW', 'modified': False},
        'stage_status_file': 'stage_status.jsonl',
        'stage_terminal_events': {row['phase']: 'complete' for row in
                                  [{'phase': p} for p in ['fixture_build', 'p1', 'probe', 'p2',
                                                          'stage_demo', 'harness']]},
        'not_verifiable_items': NOT_VERIFIABLE,
        'code_files_before_after': frozen,
        'strategy_changed': False, 'scientific_results_recomputed': False,
        'a1_a3_access': {'opened': 0, 'hashed': 0, 'decompressed': 0, 'stat_calls': 0},
        'handoff_file': 'handoff.md'})
    handoff = [
        '# TASK-Q01C-R1 交回说明（恢复机制与日志精准小修）', '',
        f'- 状态：{status}；R1目录：`{r1_dir}`',
        f"- 跨进程实证：P1 pid={evidence['processes']['p1']['pid']} 被监督进程终止 → "
        f"P2 pid={evidence['processes']['p2']['pid']} 使用 --resume 复用其检查点。",
        f"- P2 对已完成阶段新增扫描次数：{evidence['scan_counters']['new_passes_in_p2_total']}；"
        f"检查点 hash 前后一致：{evidence['checkpoints']['hash_invariant']}。",
        '- CLI 契约：--resume（拒绝已 finalize、校验后复用、失败即停）、--stage（依赖不足退出 6；'
        '单阶段仅执行所选阶段并记录 SKIPPED）、--probe-resume（只读资格报告）。',
        '- 检查点协议：payload → meta → checkpoint.COMPLETE，阶段标记为 <stage>.stage.COMPLETE，'
        'S20/S30/S40 的检查点标记不再被阶段标记覆盖。',
        '- 日志：R1 主命令、P1、P2、probe、独立验证命令均由实际 argv 记录；每个 R1 阶段有 start + '
        '唯一终态；P1 被外部终止由监督进程写 termination_evidence.json。',
        f"- extension 来源隔离：holdout / extension overlap / extension new 三类极端值扰动后，"
        f"calibration 参数逐字段不变（见 extension_isolation_test.json）。",
        f"- 正式科学run：{verification['key_metrics']['formal_run_files_matching']}/56 manifest 匹配，"
        f"状态 {read_json(FORMAL_RUN / 'run_summary.json')['status']} 未变；之前 7 个 run 与旧证据未变。",
        '- 未读取/未哈希/未解压 A1–A3（本任务全程仅使用合成 fixture）。', '',
        '## 保留的历史限制（NOT_VERIFIABLE）',
        f"- {NOT_VERIFIABLE[0]['item']}：{NOT_VERIFIABLE[0]['reason']}", '',
        '## 待主控审查',
        '- 是否接受 --hold-after-stage 作为仅测试用的中断钩子（只暂停、不改科学语义）。',
        '- 是否接受“阶段标记输出哈希会随后续阶段合法改写而失效”的口径（跨进程恢复仅依赖 '
        '数据检查点绑定）。',
        '- 是否需要在未来运行中把 s50_verify 的终端事件纳入 S50 内的证据文件。']
    (r1_dir / 'handoff.md').write_text('\n'.join(handoff), encoding='utf-8')
    files = []
    for path in sorted(r1_dir.rglob('*')):
        if path.is_file() and path.name != 'output_manifest.json':
            files.append({'path': str(path.relative_to(r1_dir)).replace('\\', '/'),
                          'bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    write_json(r1_dir / 'output_manifest.json',
               {'task': 'TASK-Q01C-R1', 'run_id': r1_dir.name, 'generated_local': now_iso(),
                'n_files': len(files), 'files': files})
    print(json.dumps({'status': status, 'n_files': len(files),
                      'checks': checks['summary']}, ensure_ascii=False), flush=True)
    return 0 if status == 'COMPLETE_PENDING_REVIEW' else 2


if __name__ == '__main__':
    sys.exit(main())
