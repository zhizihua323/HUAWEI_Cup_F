"""Regenerate output_manifest.json so it covers every file in the run directory,
including the post-run reconciliation artifacts."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


postrun = ['postrun_reconciliation.py', 'checks_postrun_reconciliation.json',
           '_fix6_recon.py', '_fix7_recon_c12.py', '_fix8_recon_lookup.py',
           '_regenerate_manifest.py']
files = []
for path in sorted(RUN_DIR.rglob('*')):
    if not path.is_file() or path.name == 'output_manifest.json':
        continue
    stat = path.stat()
    rel = str(path.relative_to(RUN_DIR)).replace('\\', '/')
    files.append({'path': rel, 'bytes': stat.st_size, 'sha256': sha256_file(path),
                  'created_after_inprocess_finalize': rel in postrun})
payload = {'run_id': RUN_DIR.name,
           'generated_local': datetime.now(CST).isoformat(timespec='seconds'),
           'note': 'regenerated after the post-run read-only reconciliation; entries flagged '
                   'created_after_inprocess_finalize were produced after checks.json/run_summary.json '
                   'and are supplementary evidence, not part of the in-process check list',
           'n_files': len(files), 'files': files}
(RUN_DIR / 'output_manifest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                              encoding='utf-8')
print('manifest files:', len(files))
for item in files:
    if item['created_after_inprocess_finalize']:
        print('  post-run:', item['path'], item['bytes'])
