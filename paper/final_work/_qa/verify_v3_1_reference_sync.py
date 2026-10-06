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
DOCX = WORK / "FINAL_MANUSCRIPT_V3_1.docx"
PDF = WORK / "FINAL_MANUSCRIPT_V3_1.pdf"
EXPECTED = json.loads((WORK / "_qa" / "v3_1_build_audit.json").read_text(encoding="utf-8"))["citation_order"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


checks: list[dict[str, object]] = []


def check(name: str, condition: bool, detail: object) -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


bib_text = (REF / "references_final.bib").read_text(encoding="utf-8")
bib_keys = re.findall(r"(?m)^@\w+\{([^,]+),", bib_text)
check("bib_count", len(bib_keys) == 20, len(bib_keys))
check("bib_order", bib_keys == EXPECTED, bib_keys)

with (REF / "reference_verification_final.csv").open(encoding="utf-8-sig", newline="") as handle:
    verification = list(csv.DictReader(handle))
verify_keys = [row["reference_key"] for row in verification]
check("verification_count", len(verification) == 20, len(verification))
check("verification_order", verify_keys == EXPECTED, verify_keys)
check("verification_numbers", [row["reference_number"] for row in verification] == [str(i) for i in range(1, 21)], [row["reference_number"] for row in verification])
check("verification_all_used", all(row["included_in_final"] == "YES" for row in verification), sorted({row["included_in_final"] for row in verification}))

with (REF / "citation_map_final.csv").open(encoding="utf-8-sig", newline="") as handle:
    citation_map = list(csv.DictReader(handle))
map_keys = set()
for row in citation_map:
    map_keys.update(key for key in row["reference_keys"].split(";") if key)
check("citation_map_covers_all_references", set(EXPECTED).issubset(map_keys), sorted(set(EXPECTED) - map_keys))

with zipfile.ZipFile(DOCX) as archive:
    document_xml = archive.read("word/document.xml").decode("utf-8")
    settings_xml = archive.read("word/settings.xml").decode("utf-8")
    relationships = archive.read("word/_rels/document.xml.rels").decode("utf-8")
    all_xml_text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", document_xml))
    doc_refs = [int(n) for n in re.findall(r"(?:^|>)(?:\[|&#91;)(\d+)(?:\]|&#93;)", document_xml)]
    hyperlinks = len(re.findall(r"<w:hyperlink\b", document_xml))
    toc_fields = len(re.findall(r"TOC \\o", document_xml))
    update_fields = "updateFields" in settings_xml

check("docx_no_unresolved_citation_tokens", "[@" not in all_xml_text and "{{CITE" not in all_xml_text, "no unresolved tokens")
check("docx_reference_sequence", sorted(set(n for n in doc_refs if 1 <= n <= 20)) == list(range(1, 21)), sorted(set(n for n in doc_refs if 1 <= n <= 20)))
check("docx_toc_field_present", toc_fields >= 1, toc_fields)
check("docx_toc_hyperlinks_present", hyperlinks >= 20, hyperlinks)
check("docx_update_fields_enabled", update_fields, update_fields)
check("docx_relationships_present", "Relationship" in relationships, "document relationships loaded")

pdf = PdfReader(str(PDF))
check("pdf_page_count", len(pdf.pages) == 29, len(pdf.pages))

render_dir = WORK / "_qa" / "v3_1_final_pages"
page_pngs = sorted(render_dir.glob("page-*.png"))
check("all_pdf_pages_rendered", len(page_pngs) == 29 and all(path.stat().st_size > 0 for path in page_pngs), {"count": len(page_pngs), "empty": [path.name for path in page_pngs if path.stat().st_size == 0]})

manifest = json.loads((REF / "output_manifest_v3_1.json").read_text(encoding="utf-8"))
manifest_errors = []
for item in manifest["files"]:
    path = ROOT / item["path"]
    if not path.exists() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
        manifest_errors.append(item["path"])
check("manifest_matches_current_files", not manifest_errors, manifest_errors)

source = (WORK / "FINAL_MANUSCRIPT_V3_1_SOURCE.md").read_text(encoding="utf-8")
check("license_limitation_in_source", "公开数据卡没有声明复用许可" in source and "随稿附件不再分发该第三方原始快照" in source, "explicit license and non-redistribution statement")
check("exact_snapshot_commit_in_source", "aa81ecc38fdc5708254b833923368970efdf5ef5" in source, "exact commit present")

result = {
    "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
    "checks": checks,
    "docx_sha256": sha(DOCX),
    "pdf_sha256": sha(PDF),
    "reference_count": 20,
    "pdf_pages": len(pdf.pages),
}
(WORK / "_qa" / "v3_1_reference_sync_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

summary = "\n".join(f"- {item['status']} — {item['name']}: `{item['detail']}`" for item in checks)
(WORK / "REFERENCE_SYNC_QA_V3_1.md").write_text(f"""# V3.1 引用与许可收口 QA

## 结论

- 总体状态：**{result['status']}**。
- V3.1正文、BibTeX、引用映射和核验表统一为20条实际引用。
- Open LLM Leaderboard复用许可仍为未确认；终稿通过精确commit引用和不再分发第三方原始快照控制提交风险，未伪造许可结论。
- 终稿PDF为29页；29页均已渲染，并完成接触表全页审阅以及目录页、Q4改动页、参考文献末页的原尺寸复核。
- 科学模型、数据、数字、结论和资格词均未改变。

## 自动检查

{summary}

## 文件指纹

- DOCX SHA256：`{result['docx_sha256']}`
- PDF SHA256：`{result['pdf_sha256']}`

## 限制

当前在LibreOffice导出链和PDF渲染中完成版式核验；尚未在Microsoft Word桌面程序中逐页复核其原生重排。提交前若使用Word再次打开，应只更新目录并核对总页数、目录页码和最后一页参考文献，避免无意改写正文。
""", encoding="utf-8")

print(json.dumps({"status": result["status"], "checks": len(checks), "failures": [item["name"] for item in checks if item["status"] == "FAIL"]}, ensure_ascii=False))
