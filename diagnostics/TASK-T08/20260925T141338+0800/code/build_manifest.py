from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    run = args.workspace.resolve()/"diagnostics/TASK-T08"/args.run_id
    critical = ["run_summary.json", "command_log.json", "stage_status.jsonl", "checks.json", "verification.json", "handoff.md"]
    missing = [name for name in critical if not (run/name).exists()]
    if missing:
        raise SystemExit(f"critical files missing before manifest: {missing}")
    files = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path.name != "output_manifest.json":
            files.append({"path": path.relative_to(run).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest_mtime = datetime.now(timezone.utc)
    critical_times = {name: datetime.fromtimestamp((run/name).stat().st_mtime, timezone.utc).isoformat() for name in critical}
    payload = {
        "task_id": "TASK-T08", "run_id": args.run_id, "generated_at_utc": manifest_mtime.isoformat(),
        "generated_after": critical, "critical_file_mtimes_utc": critical_times,
        "generated_after_checks": (run/"checks.json").stat().st_mtime <= manifest_mtime.timestamp(),
        "generated_after_verification": (run/"verification.json").stat().st_mtime <= manifest_mtime.timestamp(),
        "generated_after_handoff": (run/"handoff.md").stat().st_mtime <= manifest_mtime.timestamp(),
        "self_excluded": True, "files": files, "n_files": len(files),
    }
    (run/"output_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    mismatches = []
    for e in files:
        p = run/e["path"]
        if p.stat().st_size != e["bytes"] or sha256(p) != e["sha256"]:
            mismatches.append(e["path"])
    print(json.dumps({"n_files": len(files), "mismatches": mismatches, "manifest_last": all([payload["generated_after_checks"], payload["generated_after_verification"], payload["generated_after_handoff"]])}, ensure_ascii=False))
    return 0 if not mismatches and all([payload["generated_after_checks"], payload["generated_after_verification"], payload["generated_after_handoff"]]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

