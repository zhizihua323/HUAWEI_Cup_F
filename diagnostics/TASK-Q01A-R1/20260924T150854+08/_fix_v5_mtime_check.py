from pathlib import Path
p = Path(__file__).resolve().parent / 'verify_repairs.py'
t = p.read_text(encoding='utf-8-sig')
old = """    c07_manifest = read_json(R_DIR / 'input_manifest.json')"""
new = """    add_check('V22_c08c_historical_full_tree_mtime',
              'historical full-directory mtime unchanged (original C08 proposition, mtime part)',
              'NOT_VERIFIABLE',
              {'pre_run_full_tree_mtime_snapshot_available': False,
               'in_run_scope': 'the original run recorded size/mtime only while it ran, so no pre-run snapshot '
                               'of all 2012 files exists',
               'r1_action': 'no retrospective snapshot was manufactured; the substitute evidence is the '
                            'path/size registry comparison (V19) and the three XZ hashes (C08b)'},
              'unchanged mtimes for every file under F题/real_attachments',
              'R/checks.json C08 evidence and R/run_summary.json; no pre-run snapshot',
              note='kept out of PASS on purpose: the available evidence cannot prove the historical mtime claim')
    c07_manifest = read_json(R_DIR / 'input_manifest.json')"""
assert t.count(old) == 1
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8-sig')
print('V22 mtime check added')
