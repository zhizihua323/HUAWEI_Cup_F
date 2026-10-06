from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4_common import (  # noqa: E402
    ROOT, RUN_DIR, RUN_ID, iso_local, read_json, relpath, sha256_file,
    write_code_snapshot, write_json, write_stage,
)


def append_command(stage: str, command: str) -> None:
    path = RUN_DIR / "command_log.json"
    obj = read_json(path)
    obj.setdefault("commands", []).append({
        "stage": stage, "command": command, "cwd": str(ROOT),
        "recorded_local": iso_local(), "status": "COMPLETED",
    })
    write_json(path, obj)


def main() -> None:
    verification = read_json(RUN_DIR / "verification.json")
    if verification.get("status") != "PASS":
        raise RuntimeError("independent verifier did not pass; output manifest will not be frozen")
    paper = ROOT / "paper/Q4_GAP_RESULT_FREEZE.md"
    paper_text = paper.read_text(encoding="utf-8")
    paper_text = paper_text.replace("CANDIDATE_PENDING_G4_INDEPENDENT_VERIFICATION", "CANDIDATE_VERIFIED_PENDING_MAIN_CONTROL")
    paper.write_text(paper_text, encoding="utf-8")
    checks = read_json(RUN_DIR / "checks.json")
    checks["independent_verification"] = {
        "status": verification["status"],
        "checks_pass": verification["checks_pass"],
        "checks_total": verification["checks_total"],
        "file": "verification.json",
        "verifier_imported_execution_module": False,
    }
    write_json(RUN_DIR / "checks.json", checks)

    run_summary = read_json(RUN_DIR / "run_summary.json")
    run_summary["status"] = "CANDIDATE_VERIFIED_PENDING_MAIN_CONTROL"
    run_summary["independent_verification"] = checks["independent_verification"]
    write_json(RUN_DIR / "run_summary.json", run_summary)

    append_command("verify", "python diagnostics/TASK-G4/20260925T195716+0800/code/verify_g4.py")
    write_stage("verify", "COMPLETED", verification_status=verification["status"], checks_pass=verification["checks_pass"], checks_total=verification["checks_total"])
    append_command("build_manifest", "python diagnostics/TASK-G4/20260925T195716+0800/code/05_build_manifest.py")
    write_stage("build_manifest", "STARTED", manifest_last=True)

    write_code_snapshot()
    entries = []
    for p in sorted(RUN_DIR.rglob("*")):
        if not p.is_file():
            continue
        if p.name == "output_manifest.json" or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        entries.append({"path": relpath(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    paper = ROOT / "paper/Q4_GAP_RESULT_FREEZE.md"
    entries.append({"path": relpath(paper), "bytes": paper.stat().st_size, "sha256": sha256_file(paper)})
    manifest = {
        "run_id": RUN_ID,
        "created_local": iso_local(),
        "base_directory": relpath(RUN_DIR),
        "manifest_is_last_file": True,
        "excluded_from_manifest": ["output_manifest.json", "__pycache__", "*.pyc"],
        "file_count": len(entries),
        "files": entries,
    }
    write_json(RUN_DIR / "output_manifest.json", manifest)
    # Read-only post-write check; no files are written after this point.
    bad = []
    for item in manifest["files"]:
        p = ROOT / item["path"]
        if not p.exists() or p.stat().st_size != item["bytes"] or sha256_file(p) != item["sha256"]:
            bad.append(item["path"])
    if bad:
        raise RuntimeError({"manifest_postcheck_failed": bad})


if __name__ == "__main__":
    main()
