from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
paths = [
    "paper/final_work/FINAL_MANUSCRIPT_V4.docx",
    "paper/final_work/FINAL_MANUSCRIPT_V4.pdf",
    "paper/final_work/FINAL_MANUSCRIPT_V4_SOURCE.md",
    "paper/final_work/FINAL_MANUSCRIPT_V4_INTEGRATED.md",
    "paper/final_work/V4_REVISION_LOG.md",
    "paper/final_work/WORD_QA_REPORT_V4.md",
    "paper/final_work/PDF_QA_REPORT_V4.md",
    "paper/final_work/_qa/V4_FINAL_CHECKS.json",
    "paper/final_work/_qa/v4_build_audit.json",
    "paper/final_work/_qa/word_native_check_v4.json",
    "paper/final_figures/submission_v4/ASSET_INDEX.md",
    "paper/final_figures/submission_v4/VISUAL_QA.md",
    "paper/final_figures/submission_v4/build_q3_v4.py",
    "paper/final_figures/submission_v4/fig05_v4_q3_budget_context.svg",
    "paper/final_figures/submission_v4/fig05_v4_q3_budget_context.pdf",
    "paper/final_figures/submission_v4/fig05_v4_q3_budget_context.png",
    "paper/final_figures/submission_v4/source_data/fig05_v4_q3_budget_context.csv",
    "paper/final_references/references_final.bib",
    "paper/final_references/citation_map_final.csv",
    "paper/final_references/reference_verification_final.csv",
    "paper/final_references/OPEN_LLM_LICENSE_HANDLING.md",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


items = []
for rel in paths:
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(rel)
    items.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest(path)})

manifest = {
    "status": "COMPLETE",
    "version": "FINAL_MANUSCRIPT_V4",
    "science_closed": True,
    "files": items,
}
(ROOT / "paper/final_work/_qa/V4_OUTPUT_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"status": "PASS", "files": len(items)}, ensure_ascii=False))
