from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "paper" / "final_references"
PREFLIGHT_BIB = ROOT / "paper" / "preflight" / "references_verified.bib"
FINAL_BIB = REF / "references_final.bib"
VERIFY = REF / "reference_verification_final.csv"

ORDER = [
    "kaplan2020scaling",
    "hoffmann2022training",
    "penedo2024fineweb",
    "warner2025modernbert",
    "xie2023dsir",
    "spearman1904general",
    "efron1979bootstrap",
    "openai_tools",
    "liu2025regmix",
    "scheffe1958mixtures",
    "biderman2023pythia",
    "zhou2023ifeval",
    "suzgun2023bbh",
    "hendrycks2021math",
    "rein2023gpqa",
    "sprague2023musr",
    "wang2024mmlupro",
    "openllmleaderboard2025results",
    "epochai2026models",
    "koenker1978regression",
]


def bib_blocks(text: str) -> dict[str, str]:
    starts = list(re.finditer(r"(?m)^@(\w+)\{([^,]+),", text))
    out: dict[str, str] = {}
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        out[match.group(2).strip()] = text[match.start():end].strip()
    return out


current = bib_blocks(FINAL_BIB.read_text(encoding="utf-8"))
preflight = bib_blocks(PREFLIGHT_BIB.read_text(encoding="utf-8"))
all_blocks = {**preflight, **current}
all_blocks["openai_tools"] = """@misc{openai_tools,
  author = {{OpenAI}},
  title = {{OpenAI API Changelog: GPT-5.6 Sol and GPT-6 Astra release records}},
  year = {2026},
  howpublished = {Official product changelog},
  url = {https://developers.openai.com/api/docs/changelog},
  note = {GPT-5.6 Sol released 2026-07-09; GPT-6 Astra released 2026-09-03},
  urldate = {2026-09-26}
}"""
missing = [key for key in ORDER if key not in all_blocks]
if missing:
    raise SystemExit(f"Missing BibTeX records: {missing}")

header = (
    "% Submission bibliography synchronized to FINAL_MANUSCRIPT_V3_1.\n"
    "% Order follows first appearance in the V3.1 manuscript.\n"
    "% Exactly 20 cited entries; no uncited candidates are included.\n\n"
)
FINAL_BIB.write_text(
    header + "\n\n".join(all_blocks[key] for key in ORDER) + "\n",
    encoding="utf-8",
)


def load_rows(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), {row["reference_key"]: row for row in reader}


fields, old = load_rows(VERIFY)
openai_row = {
    "reference_number": "8",
    "reference_key": "openai_tools",
    "included_in_final": "YES",
    "entry_type": "misc",
    "authors_verified": "OpenAI",
    "title": "OpenAI API Changelog: GPT-5.6 Sol and GPT-6 Astra release records",
    "year": "2026",
    "venue": "OpenAI official product changelog",
    "volume": "",
    "issue": "",
    "pages_or_article": "",
    "doi": "",
    "official_url": "https://developers.openai.com/api/docs/changelog",
    "verification_sources": "OpenAI official product changelog",
    "accessed_at": "2026-09-26",
    "status": "VERIFIED_OFFICIAL_SOURCE",
    "corrections_or_notes": "Used only for the AI tool disclosure and release dates.",
}
old["openai_tools"] = openai_row
for number, key in enumerate(ORDER, start=1):
    if key not in old:
        raise SystemExit(f"Missing verification row: {key}")
    old[key]["reference_number"] = str(number)
    old[key]["included_in_final"] = "YES"
    if key == "xie2023dsir":
        old[key]["status"] = "VERIFIED_DOI"
        old[key]["corrections_or_notes"] = "Cited for DSIR as a target-relevance/data-selection method; not used as the main Q estimator."
    if key == "koenker1978regression":
        old[key]["status"] = "VERIFIED_DOI"
        old[key]["corrections_or_notes"] = "Cited for the quantile-loss definition used in the frozen Q4 candidate-screening rule."
with VERIFY.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(old[key] for key in ORDER)


map_fields = [
    "citation_id",
    "body_location_or_anchor",
    "claim_text_or_anchor",
    "claim_type",
    "final_reference_numbers",
    "reference_keys",
    "verification_status",
    "verification_basis",
    "required_qualification",
    "project_evidence",
]
map_rows = [
    ["CIT-001", "1.1；4.1", "神经语言模型标度律及计算最优训练背景", "EXTERNAL_METHOD_BACKGROUND", "[1],[2]", "kaplan2020scaling;hoffmann2022training", "VERIFIED", "arXiv official records", "仅作结构启发，不沿用论文参数", "paper/T06_RESULT_FREEZE.md"],
    ["CIT-002", "3.1", "FineWeb质量筛选与ModernBERT编码器背景", "EXTERNAL_METHOD_BACKGROUND", "[3],[4]", "penedo2024fineweb;warner2025modernbert", "VERIFIED", "NeurIPS proceedings; ACL Anthology", "字段语义与处理仍以题目字典和冻结实现为准", "paper/FINAL_SCIENTIFIC_FREEZE.md"],
    ["CIT-003", "3.1", "DSIR是目标相关的数据选择指标", "EXTERNAL_METHOD", "[5]", "xie2023dsir", "VERIFIED", "NeurIPS/Crossref DOI metadata", "只作目标相关向量背景，不称为通用质量分量", "paper/FINAL_SCIENTIFIC_FREEZE.md"],
    ["CIT-004", "3.4", "Spearman秩相关与bootstrap区间", "EXTERNAL_METHOD", "[6],[7]", "spearman1904general;efron1979bootstrap", "VERIFIED", "JSTOR original scan; Crossref/IMS records", "相关不解释为因果；项目数值来自冻结run", "diagnostics/TASK-G1/20260925T223500+08/"],
    ["CIT-005", "3.5；4.5；5.3；6.3；第9章", "AI辅助工具名称、版本、开发者与发布日期", "AI_TOOL_DISCLOSURE", "[8]", "openai_tools", "VERIFIED_OFFICIAL_SOURCE", "OpenAI official product changelog", "只披露辅助范围，不把AI作为科学证据", "paper/FINAL_SCIENTIFIC_FREEZE.md"],
    ["CIT-006", "3.6", "RegMix与Scheffe混合模型背景", "EXTERNAL_METHOD", "[9],[10]", "liu2025regmix;scheffe1958mixtures", "VERIFIED", "OpenReview; Oxford/Crossref", "外部论文结果不替代本项目训练与验证", "paper/T07_RESULT_FREEZE.md"],
    ["CIT-007", "4.1", "Pythia模型族与实验体系", "EXTERNAL_DATASET_AND_METHOD", "[11]", "biderman2023pythia", "VERIFIED", "PMLR official page", "同源记录不称为独立复制", "paper/T06_RESULT_FREEZE.md"],
    ["CIT-008", "6.1", "六项Benchmark的公开定义", "EXTERNAL_BENCHMARK", "[12]-[17]", "zhou2023ifeval;suzgun2023bbh;hendrycks2021math;rein2023gpqa;sprague2023musr;wang2024mmlupro", "VERIFIED", "arXiv; ACL Anthology; NeurIPS; OpenReview", "逐任务保留口径，辅助均值不替代任务向量", "paper/FINAL_SCIENTIFIC_FREEZE.md"],
    ["CIT-009", "6.1", "Open LLM Leaderboard冻结快照与Epoch AI元数据来源", "EXTERNAL_DATASET", "[18],[19]", "openllmleaderboard2025results;epochai2026models", "METADATA_VERIFIED_LICENSE_UNRESOLVED", "Hugging Face exact commit; Epoch AI official data page", "Open LLM快照不随稿再分发；不推定复用许可", "paper/FINAL_PAPER_PATCH_CONTRACT.md"],
    ["CIT-010", "6.2", "0.90分位损失定义", "EXTERNAL_METHOD", "[20]", "koenker1978regression", "VERIFIED", "Econometrica/Crossref DOI metadata", "仅支持冻结候选筛选规则的方法定义", "diagnostics/TASK-G4/20260925T195716+0800/"],
    ["PRJ-FINAL-Q1", "3.1-3.6；7；8", "质量代理、扩展稳定性与人工盲审", "PROJECT_FROZEN_RESULT", "[3]-[7],[9],[10]（仅方法）", "penedo2024fineweb;warner2025modernbert;xie2023dsir;spearman1904general;efron1979bootstrap;liu2025regmix;scheffe1958mixtures", "PROJECT_EVIDENCE_VERIFIED", "FINAL_SCIENTIFIC_FREEZE and G1 run", "项目数字只回引冻结证据", "paper/FINAL_SCIENTIFIC_FREEZE.md;diagnostics/TASK-G1/20260925T223500+08/"],
    ["PRJ-FINAL-Q2", "4.1-4.5；7；8", "条件广义标度律及分来源验证", "PROJECT_FROZEN_RESULT", "[1],[2],[11]（仅背景/数据）", "kaplan2020scaling;hoffmann2022training;biderman2023pythia", "PROJECT_EVIDENCE_VERIFIED", "FINAL_SCIENTIFIC_FREEZE and G2 run", "不得写成统一四变量模型已获多源验证", "paper/FINAL_SCIENTIFIC_FREEZE.md;diagnostics/TASK-G2/20260925T195336+08/"],
    ["PRJ-FINAL-Q3", "5.1-5.4；7；8", "预算约束优化、KKT与敏感性", "PROJECT_FROZEN_RESULT", "无新增外部引用", "", "PROJECT_EVIDENCE_VERIFIED", "T07 frozen interface", "不改变冻结最优解及适用范围", "paper/T07_RESULT_FREEZE.md"],
    ["PRJ-FINAL-Q4", "6.1-6.5；7；8", "任务模型选择、零分解及未来情景", "PROJECT_FROZEN_RESULT", "[12]-[20]（仅定义/数据/方法）", "zhou2023ifeval;suzgun2023bbh;hendrycks2021math;rein2023gpqa;sprague2023musr;wang2024mmlupro;openllmleaderboard2025results;epochai2026models;koenker1978regression", "PROJECT_EVIDENCE_VERIFIED", "FINAL_SCIENTIFIC_FREEZE and G4 run", "保留SCENARIO_ONLY_UNVALIDATED；不得换算Loss为Benchmark", "paper/FINAL_SCIENTIFIC_FREEZE.md;diagnostics/TASK-G4/20260925T195716+0800/"],
]
with (REF / "citation_map_final.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
    writer.writerow(map_fields)
    writer.writerows(map_rows)


(REF / "unresolved_citations.csv").write_text(
    '"reference_key","reference_number","field_or_claim","status","evidence_checked","why_unresolved","impact_on_final_manuscript","required_action"\n'
    '"openllmleaderboard2025results","18","Dataset reuse license","UNRESOLVED_NONREDISTRIBUTION_CONTROLLED","Hugging Face exact commit aa81ecc38fdc5708254b833923368970efdf5ef5; public dataset card exposes no license declaration","No reuse license could be independently confirmed for the frozen snapshot","Source provenance remains citable; the final paper reports project aggregates, while the third-party raw snapshot is excluded from submission attachments","Do not redistribute the raw snapshot or infer permission; if redistribution later becomes necessary, obtain and record an explicit license basis"\n',
    encoding="utf-8-sig",
)


(REF / "OPEN_LLM_LICENSE_HANDLING.md").write_text("""# Open LLM Leaderboard 许可处理

- 核验对象：`open-llm-leaderboard/results`，commit `aa81ecc38fdc5708254b833923368970efdf5ef5`。
- 已确认：来源身份、公开访问地址、冻结commit和论文中的数据来源说明。
- 未确认：该冻结快照的数据卡未声明可独立核验的复用许可，因此不得从“可公开访问”推断“允许再分发”。
- 终稿处理：正文引用准确来源并只报告题目附件经冻结流程得到的汇总结果；提交附件不再分发该第三方原始快照或逐条复制数据。
- 后续边界：如必须重新分发原始快照，应先取得明确许可证或权利人授权并保存证据。当前引用行为不等同于授予复用权。
""", encoding="utf-8")


(REF / "REFERENCE_AUDIT.md").write_text("""# V3.1 最终引用闭环审计

审计日期：2026-09-26

## 结论

- `FINAL_MANUSCRIPT_V3_1` 实际使用并列出 **20** 条参考文献。
- `references_final.bib` 只保留这20条，并按正文首次出现顺序排列。
- `citation_map_final.csv` 已按V3.1章节、编号和资格词重建；旧的23条映射不再作为终稿依据。
- `reference_verification_final.csv` 只登记终稿实际引用的20条；未使用候选不混入最终集合。
- Open LLM Leaderboard的来源、commit和引用元数据已确认；复用许可仍未确认。终稿明确不随稿再分发该第三方原始快照，且不把公开访问解释为复用授权。
- 参考文献同步未改变任何模型、数据、数字、科学结论或资格词。

## 最终编号

| 编号 | 引用键 | 用途 |
|---:|---|---|
| 1 | `kaplan2020scaling` | 神经标度律背景 |
| 2 | `hoffmann2022training` | 计算最优训练背景 |
| 3 | `penedo2024fineweb` | 数据质量筛选背景 |
| 4 | `warner2025modernbert` | 质量评分器背景 |
| 5 | `xie2023dsir` | DSIR目标相关性背景 |
| 6 | `spearman1904general` | 秩相关方法 |
| 7 | `efron1979bootstrap` | bootstrap方法 |
| 8 | `openai_tools` | AI工具披露 |
| 9 | `liu2025regmix` | RegMix方法 |
| 10 | `scheffe1958mixtures` | 混合模型方法 |
| 11 | `biderman2023pythia` | Pythia数据来源 |
| 12--17 | 六项Benchmark来源 | IFEval、BBH、MATH、GPQA、MuSR、MMLU-Pro |
| 18 | `openllmleaderboard2025results` | 冻结评测快照来源 |
| 19 | `epochai2026models` | 模型算力与日期元数据来源 |
| 20 | `koenker1978regression` | 分位损失定义 |

## 提交边界

`references_word_numbered.docx` 是旧23条引用阶段的辅助文件，已被V3.1正文中的正式参考文献表取代，不得再用于终稿替换。最终依据为V3.1 DOCX/PDF、`references_final.bib`、`citation_map_final.csv`和本审计。
""", encoding="utf-8")


manifest_paths = [
    REF / "references_final.bib",
    REF / "citation_map_final.csv",
    REF / "reference_verification_final.csv",
    REF / "unresolved_citations.csv",
    REF / "REFERENCE_AUDIT.md",
    REF / "OPEN_LLM_LICENSE_HANDLING.md",
    ROOT / "paper" / "final_work" / "FINAL_MANUSCRIPT_V3_1.docx",
    ROOT / "paper" / "final_work" / "FINAL_MANUSCRIPT_V3_1.pdf",
]
manifest = {
    "version": "V3.1",
    "generated_at": "2026-09-26",
    "reference_count": 20,
    "citation_order": ORDER,
    "open_llm_license": "UNRESOLVED_NONREDISTRIBUTION_CONTROLLED",
    "files": [],
}
for path in manifest_paths:
    data = path.read_bytes()
    manifest["files"].append({
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
(REF / "output_manifest_v3_1.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"reference_count": len(ORDER), "manifest_files": len(manifest_paths)}, ensure_ascii=False))
