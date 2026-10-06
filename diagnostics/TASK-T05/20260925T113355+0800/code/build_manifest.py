from pathlib import Path
import hashlib, json, sys
run=Path(__file__).resolve().parents[1]
include_verification = "--include-verification" in sys.argv
excluded={"output_manifest.json"}
if not include_verification:
    excluded.add("verification.json")
files=[]
for p in sorted(run.rglob("*")):
    if not p.is_file(): continue
    rel=p.relative_to(run).as_posix()
    if rel in excluded or "__pycache__" in p.parts: continue
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    files.append({"path":rel,"bytes":p.stat().st_size,"sha256":h})
prior=None
if include_verification and (run/"output_manifest.json").exists():
    prior=hashlib.sha256((run/"output_manifest.json").read_bytes()).hexdigest()
man={
 "task_id":"TASK-T05","run_id":run.name,"generated_after_verification":include_verification,
 "self_excluded":True,"verification_excluded":not include_verification,
 "verified_manifest_sha256":prior,"files":files,
 "scope":"All regular files except output_manifest.json itself, __pycache__, and verification.json before verification; final manifest adds verification.json."
}
(run/"output_manifest.json").write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"files":len(files),"include_verification":include_verification,"prior_manifest":prior},ensure_ascii=False))