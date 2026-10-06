from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

RUN_ID = "20260925T141338+0800"
TZ = timezone(timedelta(hours=8))
TASKS = [
    "IFEval",
    "BBH",
    "MATH Lvl 5",
    "GPQA",
    "MUSR",
    "MMLU-PRO",
]
TASK_TARGETS = {
    "IFEval": "IFEval_pct",
    "BBH": "BBH_pct",
    "MATH Lvl 5": "MATH Lvl 5_pct",
    "GPQA": "GPQA_pct",
    "MUSR": "MUSR_pct",
    "MMLU-PRO": "MMLU-PRO_pct",
}
AUX_TARGET = "benchmark_mean_aux"
ALL_TARGETS = list(TASK_TARGETS.values()) + [AUX_TARGET]
SCENARIOS = [
    ("SCALE_GROWTH_Q25_CONSERVATIVE", 0.25),
    ("SCALE_GROWTH_Q50_BASE", 0.50),
    ("SCALE_GROWTH_Q75_OPTIMISTIC", 0.75),
]
HORIZONS = [12, 24]


def local_now() -> datetime:
    return datetime.now(TZ)


def iso_utc(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def iso_local(dt: datetime | None = None) -> str:
    if dt is None:
        dt = local_now()
    return dt.astimezone(TZ).isoformat()


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        import numpy as np
        import pandas as pd
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            if pd.isna(value):
                return None
            return float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, (pd.Timestamp,)):
            if pd.isna(value):
                return None
            return value.isoformat()
        if isinstance(value, float) and pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_safe(payload), fh, ensure_ascii=False, indent=2, allow_nan=False)
        fh.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(json_safe(row), ensure_ascii=False, allow_nan=False) + "\n")


def write_csv(path: Path, frame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def verify_output_manifest(manifest_path: Path, base_dir: Path) -> dict[str, Any]:
    """Verify every entry in a frozen run's output manifest."""
    manifest = read_json(manifest_path)
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []
    checked = 0
    for entry in manifest.get("files", []):
        rel = entry["path"]
        path = base_dir / rel
        if not path.exists():
            missing.append(rel)
            continue
        checked += 1
        actual_bytes = path.stat().st_size
        actual_sha = sha256_file(path)
        expected_bytes = int(entry.get("bytes", -1))
        expected_sha = str(entry.get("sha256", ""))
        if actual_bytes != expected_bytes or actual_sha != expected_sha:
            mismatches.append({
                "path": rel,
                "expected_bytes": expected_bytes,
                "actual_bytes": actual_bytes,
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
            })
    return {
        "manifest": str(manifest_path),
        "entries": len(manifest.get("files", [])),
        "checked": checked,
        "missing": missing,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "status": "PASS" if not missing and not mismatches else "FAIL",
    }


def safe_quantile(series, q: float):
    s = series.dropna()
    if len(s) == 0:
        return None
    return float(s.quantile(q))


def q1_q3_iqr(series):
    s = series.dropna()
    if len(s) == 0:
        return None, None, None
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    return q1, q3, q3 - q1

def empty(value) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd
        if pd.isna(value):
            return True
    except Exception:
        pass
    return isinstance(value, str) and not value.strip()

