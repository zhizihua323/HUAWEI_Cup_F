# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "paper" / "final_work"
REF = ROOT / "paper" / "final_references"
FIG = ROOT / "paper" / "final_figures" / "submission_v4"
DOCX = WORK / "FINAL_MANUSCRIPT_V4.docx"
PDF = WORK / "FINAL_MANUSCRIPT_V4.pdf"
SOURCE = WORK / "FINAL_MANUSCRIPT_V4_SOURCE.md"
AUDIT = json.loads((WORK / "_qa" / "v4_build_audit.json").read_text(encoding="utf-8"))
EXPECTED = AUDIT["citation_order"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


checks: list[dict[str, object]] = []


def check(name: str, condition: bool, detail: object) -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


source = SOURCE.read_text(encoding="utf-8")
bib_text = (REF / "references_final.bib").read_text(encoding="utf-8")
bib_keys = re.findall(r"(?m)^@\w+\{([^,]+),", bib_text)
check("bib_count", len(bib_keys) == 20, len(bib_keys))
check("bib_order", bib_keys == EXPECTED, bib_keys)

with (REF / "reference_verification_final.csv").open(encoding="utf-8-sig", newline="") as handle:
    verification = list(csv.DictReader(handle))
verify_keys = [row["reference_key"] for row in verification]
check("reference_verification_matches", verify_keys == EXPECTED and len(verification) == 20, len(verification))

with (REF / "citation_map_final.csv").open(encoding="utf-8-sig", newline="") as handle:
    citation_map = list(csv.DictReader(handle))
map_keys: set[str] = set()
for row in citation_map:
    map_keys.update(key for key in row["reference_keys"].split(";") if key)
check("citation_map_covers_all_references", set(EXPECTED).issubset(map_keys), sorted(set(EXPECTED) - map_keys))

with zipfile.ZipFile(DOCX) as archive:
    document_xml = archive.read("word/document.xml").decode("utf-8")
    settings_xml = archive.read("word/settings.xml").decode("utf-8")
    styles_xml = archive.read("word/styles.xml").decode("utf-8")
    relationships = archive.read("word/_rels/document.xml.rels").decode("utf-8")
    plain_xml = re.sub(r"<[^>]+>", "", document_xml)
    doc_refs = [int(n) for n in re.findall(r"\[(\d+)\]", plain_xml)]
    toc_fields = len(re.findall(r"TOC .*?\\o", document_xml))
    hyperlinks = len(re.findall(r"<w:hyperlink\b", document_xml))

check("docx_no_unresolved_citation_tokens", "[@" not in plain_xml and "{{CITE" not in plain_xml, "no unresolved tokens")
check("docx_reference_sequence", sorted(set(n for n in doc_refs if 1 <= n <= 20)) == list(range(1, 21)), sorted(set(n for n in doc_refs if 1 <= n <= 20)))
check("docx_toc_field_present", toc_fields >= 1, toc_fields)
check("docx_toc_hyperlinks_present", hyperlinks >= 20, hyperlinks)
check("docx_toc_is_dynamic_field", "w:fldCharType=\"begin\"" in document_xml and "w:instrText" in document_xml, "dynamic field structure")
check("docx_heading_styles_present", all(name in styles_xml for name in ["heading 1", "heading 2"]), "heading styles found")
check("docx_relationships_present", "Relationship" in relationships, "document relationships loaded")

pdf = PdfReader(str(PDF))
check("pdf_page_count", len(pdf.pages) == 30, len(pdf.pages))
pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
check("pdf_contains_core_q1_result", "55.03%" in pdf_text and "261067" in pdf_text, "Q1 anchors")
check("pdf_contains_core_q3_result", "299.893" in pdf_text and "KKT" in pdf_text, "Q3 anchors")
check("pdf_contains_q4_qualification", "SCENARIO_ONLY_UNV" in pdf_text and "ALIDATED" in pdf_text, "Q4 qualification")
check("pdf_contains_20_references", all(f"[{i}]" in pdf_text for i in range(1, 21)), "[1]-[20]")

render_dir = WORK / "_qa" / "v4_final_pages"
page_pngs = sorted(render_dir.glob("page-*.png"))
check("all_pdf_pages_rendered", len(page_pngs) == 30 and all(path.stat().st_size > 0 for path in page_pngs), {"count": len(page_pngs), "empty": [p.name for p in page_pngs if p.stat().st_size == 0]})

required_fig_ext = ["svg", "pdf", "png"]
q3_assets = [FIG / f"fig05_v4_q3_budget_context.{ext}" for ext in required_fig_ext]
check("q3_figure_assets_complete", all(path.exists() and path.stat().st_size > 0 for path in q3_assets), [p.name for p in q3_assets])
check("q3_figure_script_and_data", (FIG / "build_q3_v4.py").exists() and (FIG / "source_data" / "fig05_v4_q3_budget_context.csv").exists(), "script and source data")

check("source_has_10_tables_6_figures", len(re.findall(r"^@TABLE", source, re.M)) == 10 and len(re.findall(r"^@FIG", source, re.M)) == 6, {"tables": len(re.findall(r"^@TABLE", source, re.M)), "figures": len(re.findall(r"^@FIG", source, re.M))})
check("q1_domain_table_uses_not_covered", "不覆盖" in source and "七域质量得分及扩展覆盖" in source, "domain table present")
check("q3_active_constraints_present", "活跃约束" in source and "D上界" in source, "table 8 active constraints")
check("q4_ratio_not_misreported", "比例形成0/0，正式结论是贡献占比不可定义" in source and "而不是“规模贡献为0”或“非规模贡献为0”" in source, "0/0 explicitly distinguished from zero contribution")
check("science_closed_no_new_analysis", AUDIT.get("science_executed") is False, AUDIT.get("science_executed"))
check("license_limitation_present", "公开数据卡未声明复用许可" in source and "提交附件不再分发第三方原始快照" in source, "license uncertainty retained")
check("exact_snapshot_commit_present", "aa81ecc38fdc5708254b833923368970efdf5ef5" in source, "exact commit present")

result = {
    "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
    "checks": checks,
    "docx_sha256": sha(DOCX),
    "pdf_sha256": sha(PDF),
    "reference_count": 20,
    "pdf_pages": len(pdf.pages),
    "tables": 10,
    "figures": 6,
}
(WORK / "_qa" / "V4_FINAL_CHECKS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "checks": len(checks), "failures": [x["name"] for x in checks if x["status"] == "FAIL"]}, ensure_ascii=False))
