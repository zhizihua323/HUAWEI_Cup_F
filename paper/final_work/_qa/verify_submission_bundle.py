from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
candidates = sorted(ROOT.glob("提交附件汇总_V4_*"), key=lambda p: p.stat().st_mtime)
if not candidates:
    raise SystemExit("No submission bundle found")
BUNDLE = candidates[-1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


checks: list[dict[str, object]] = []


def check(name: str, ok: bool, detail: object) -> None:
    checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})


with (BUNDLE / "SOURCE_COPY_MAP.csv").open(encoding="utf-8-sig", newline="") as fh:
    mapping = list(csv.DictReader(fh))

source_errors = []
copy_errors = []
for row in mapping:
    src = ROOT / row["source_path"]
    dst = BUNDLE / row["bundle_path"]
    if not src.exists() or sha256(src) != row["source_sha256"]:
        source_errors.append(row["source_path"])
    if not dst.exists() or sha256(dst) != row["bundle_sha256"]:
        copy_errors.append(row["bundle_path"])
check("source_files_unchanged_since_copy", not source_errors, source_errors)
check("copied_files_match_copy_map", not copy_errors, copy_errors)

python_errors = []
for path in BUNDLE.rglob("*.py"):
    try:
        compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
    except Exception as exc:  # noqa: BLE001
        python_errors.append(f"{path.relative_to(BUNDLE)}: {exc}")
check("python_copies_syntax_valid", not python_errors, python_errors)

all_paths = [p for p in BUNDLE.rglob("*") if p.is_file()]
forbidden = [
    str(p.relative_to(BUNDLE))
    for p in all_paths
    if "real_attachments" in p.parts
    or "__pycache__" in p.parts
    or p.suffix.lower() in {".pyc", ".pyo", ".parquet"}
    or p.name.lower() == "run.log"
]
check("forbidden_large_raw_or_cache_files_absent", not forbidden, forbidden)

required = [
    "00_论文终稿/FINAL_MANUSCRIPT_V4.docx",
    "00_论文终稿/FINAL_MANUSCRIPT_V4.pdf",
    "01_科学冻结/FINAL_SCIENTIFIC_FREEZE.md",
    "04_图表/正文图_V4/ASSET_INDEX.md",
    "05_引用与AI说明/references_final.bib",
    "05_引用与AI说明/AI_DISCLOSURE.md",
    "README_附件说明.md",
    "EXCLUDED_FILES.md",
]
missing = [rel for rel in required if not (BUNDLE / rel).exists()]
check("required_submission_assets_present", not missing, missing)

total_bytes = sum(p.stat().st_size for p in all_paths)
check("bundle_under_50_MiB", total_bytes < 50 * 1024 * 1024, total_bytes)
check("ai_headers_added_to_code_copies", sum(row["ai_header_added"].lower() == "true" for row in mapping) >= 1, sum(row["ai_header_added"].lower() == "true" for row in mapping))

result = {
    "status": "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL",
    "bundle": str(BUNDLE),
    "checks": checks,
    "files_before_manifest_refresh": len(all_paths),
    "bytes_before_manifest_refresh": total_bytes,
}
(BUNDLE / "PACKAGE_VERIFICATION.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Refresh manifest after every generated report; manifest intentionally excludes itself.
manifest_files = []
for path in sorted(BUNDLE.rglob("*")):
    if path.is_file() and path.name not in {"FILE_MANIFEST.csv", "FILE_MANIFEST.json"}:
        manifest_files.append(
            {
                "path": str(path.relative_to(BUNDLE)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
with (BUNDLE / "FILE_MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
    writer.writeheader()
    writer.writerows(manifest_files)
(BUNDLE / "FILE_MANIFEST.json").write_text(
    json.dumps({"bundle": BUNDLE.name, "files": manifest_files}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(json.dumps({"status": result["status"], "bundle": str(BUNDLE), "checks": len(checks), "files": len(manifest_files) + 2, "bytes": sum(p.stat().st_size for p in BUNDLE.rglob("*") if p.is_file())}, ensure_ascii=False))
