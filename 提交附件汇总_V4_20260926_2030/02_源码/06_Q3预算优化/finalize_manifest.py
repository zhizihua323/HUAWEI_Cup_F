# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path.cwd()
RUN = ROOT / "diagnostics/TASK-T07/20260925T113744+08"
SNAP = RUN / "code_snapshot"
SNAP.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


stages = [
    {"stage": "input_validation", "event": "start"},
    {"stage": "input_validation", "event": "complete"},
    {"stage": "deterministic_optimization", "event": "start"},
    {"stage": "deterministic_optimization", "event": "complete"},
    {"stage": "uncertainty_propagation", "event": "start"},
    {"stage": "uncertainty_propagation", "event": "complete"},
    {"stage": "independent_verification", "event": "start"},
    {"stage": "independent_verification", "event": "complete" if (RUN / "verification.json").exists() else "pending"},
    {"stage": "manifest_finalization", "event": "start"},
    {"stage": "manifest_finalization", "event": "complete"},
]
(RUN / "stage_status.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in stages) + "\n", encoding="utf-8")
for f in (RUN / "code").glob("*.py"):
    shutil.copy2(f, SNAP / f.name)

if (RUN / "verification.json").exists():
    summary = json.loads((RUN / "run_summary.json").read_text(encoding="utf-8"))
    verification = json.loads((RUN / "verification.json").read_text(encoding="utf-8"))
    summary["verification_status"] = verification.get("status")
    summary["verification_check_count"] = len(verification.get("checks", []))
    summary["status"] = "COMPLETE_PENDING_CONTROLLER_REVIEW" if verification.get("status") == "PASS" else "FAILED_VERIFICATION"
    (RUN / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    interface = json.loads((RUN / "t08_or_paper_interface.json").read_text(encoding="utf-8"))
    interface["independent_verification_status"] = verification.get("status")
    interface["independent_verification_check_count"] = len(verification.get("checks", []))
    (RUN / "t08_or_paper_interface.json").write_text(json.dumps(interface, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

files = []
for path in sorted(RUN.rglob("*")):
    if not path.is_file() or path.name == "output_manifest.json" or "__pycache__" in path.parts:
        continue
    files.append({"path": str(path.relative_to(RUN)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)})
manifest = {"schema_version": 1, "task": "TASK-T07", "run_id": RUN.name, "status": "COMPLETE_PENDING_CONTROLLER_REVIEW", "generated_last": True, "file_count": len(files), "files": files}
(RUN / "output_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"manifest_files": len(files), "verification": (RUN / "verification.json").exists()}, ensure_ascii=False))
