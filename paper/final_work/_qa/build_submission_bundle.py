from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
DEST = ROOT / f"提交附件汇总_V4_{STAMP}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


copy_records: list[dict[str, str | int | bool]] = []


def copy_file(src_rel: str, dst_rel: str | None = None, *, code: bool = False) -> None:
    src = ROOT / src_rel
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(src_rel)
    dst_rel = dst_rel or src_rel
    dst = DEST / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    original_sha = sha256(src)
    shutil.copy2(src, dst)
    header_added = False
    if code and dst.suffix.lower() == ".py":
        raw = dst.read_text(encoding="utf-8-sig")
        head = "\n".join(raw.splitlines()[:20]).lower()
        if "ai-assisted development disclosure" not in head and "ai辅助" not in head:
            disclosure = (
                "# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) "
                "assisted drafting and debugging; the authors reviewed the final code and outputs.\n"
                "# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.\n"
            )
            dst.write_text(disclosure + raw, encoding="utf-8")
            header_added = True
    copy_records.append(
        {
            "source_path": src_rel.replace("\\", "/"),
            "bundle_path": dst_rel.replace("\\", "/"),
            "source_sha256": original_sha,
            "bundle_sha256": sha256(dst),
            "bytes": dst.stat().st_size,
            "ai_header_added": header_added,
        }
    )


def copy_tree(src_rel: str, dst_rel: str, *, code: bool = False, allowed_suffixes: set[str] | None = None) -> None:
    root = ROOT / src_rel
    if not root.exists():
        raise FileNotFoundError(src_rel)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if allowed_suffixes is not None and path.suffix.lower() not in allowed_suffixes:
            continue
        rel = path.relative_to(root)
        copy_file(str(path.relative_to(ROOT)), str(Path(dst_rel) / rel), code=code)


def copy_run_evidence(src_rel: str, dst_rel: str) -> None:
    root = ROOT / src_rel
    allowed = {".csv", ".json", ".md"}
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in allowed and path.stat().st_size <= 3_000_000:
            copy_file(str(path.relative_to(ROOT)), str(Path(dst_rel) / path.name))


DEST.mkdir(parents=True, exist_ok=False)

# 00 终稿与说明
for name in [
    "FINAL_MANUSCRIPT_V4.docx",
    "FINAL_MANUSCRIPT_V4.pdf",
    "FINAL_MANUSCRIPT_V4_SOURCE.md",
    "V4_REVISION_LOG.md",
    "WORD_QA_REPORT_V4.md",
    "PDF_QA_REPORT_V4.md",
]:
    copy_file(f"paper/final_work/{name}", f"00_论文终稿/{name}")

# 01 科学冻结接口
for name in [
    "FINAL_SCIENTIFIC_FREEZE.md",
    "FINAL_PAPER_PATCH_CONTRACT.md",
    "FINAL_RESULT_INDEX_V2.md",
    "Q1_GAP_RESULT_FREEZE.md",
    "Q2_GAP_RESULT_FREEZE.md",
    "Q4_GAP_RESULT_FREEZE.md",
    "T05_RESULT_FREEZE.md",
    "T06_RESULT_FREEZE.md",
    "T07_RESULT_FREEZE.md",
    "T08_RESULT_FREEZE.md",
]:
    copy_file(f"paper/{name}", f"01_科学冻结/{name}")

# 02 正式源码快照
code_trees = [
    ("solution/src", "02_源码/00_基础审计与基线"),
    ("solution/outputs/quality_q01c/20260924T215718+08/code_snapshot", "02_源码/01_Q1质量主流程"),
    ("diagnostics/TASK-T03E/20260925T020032+08/phase_a_calibration_freeze/code_snapshot", "02_源码/02_Q1规则敏感性"),
    ("diagnostics/TASK-T06E-B-R1/20260925T103130+08/code_snapshot", "02_源码/03_Q2来源内质量"),
    ("diagnostics/TASK-T06E-P/20260925T075729+08/code_snapshot", "02_源码/04_Q2配比与尺度桥接"),
    ("diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/code_snapshot", "02_源码/05_Q2集成合同"),
    ("diagnostics/TASK-T07/20260925T113744+08/code_snapshot", "02_源码/06_Q3预算优化"),
    ("diagnostics/TASK-T05/20260925T113355+0800/code_snapshot", "02_源码/07_Q4_Loss_Benchmark桥接"),
    ("diagnostics/TASK-G1/20260925T223500+08/code_snapshot", "02_源码/08_Q1最终验证"),
    ("diagnostics/TASK-G2/20260925T195336+08/code_snapshot", "02_源码/09_Q2最终闭合"),
    ("diagnostics/TASK-G4/20260925T195716+0800/code_snapshot", "02_源码/10_Q4最终闭合"),
]
for src, dst in code_trees:
    copy_tree(src, dst, code=True, allowed_suffixes={".py", ".json", ".md", ".toml", ".yaml", ".yml"})

for path in [
    "paper/final_work/_qa/create_v4_source.py",
    "paper/final_work/_qa/reconstruct_v4.py",
    "paper/final_work/_qa/verify_v4.py",
]:
    copy_file(path, f"02_源码/11_论文生成与核验/{Path(path).name}", code=True)

# 03 正文引用的小型结果与中间结果
result_files = {
    "03_结果与中间数据/Q1": [
        "solution/outputs/quality_q01c/20260924T215718+08/domain_summary.csv",
        "solution/outputs/quality_q01c/20260924T215718+08/summary_denominators.csv",
        "solution/outputs/quality_q01c/20260924T215718+08/feature_summary.csv",
        "solution/outputs/quality_q01c/20260924T215718+08/extension_shift.csv",
        "solution/outputs/quality_q01c/20260924T215718+08/conditional_bootstrap.csv",
        "solution/outputs/quality_q01c/20260924T215718+08/sensitivity_comparison.csv",
        "diagnostics/TASK-T03E/20260925T020032+08/t06_quality_interface.json",
        "diagnostics/TASK-G1/20260925T223500+08/manual_validation_statistics.csv",
        "diagnostics/TASK-G1/20260925T223500+08/manual_review_parse_audit.csv",
    ],
    "03_结果与中间数据/Q2": [
        "diagnostics/TASK-T06E-B-R1/20260925T103130+08/identifiability_matrix_B_corrected.csv",
        "diagnostics/TASK-T06E-B-R1/20260925T103130+08/t07_bside_contract_candidate_corrected.json",
        "diagnostics/TASK-T06E-P/20260925T075729+08/identifiability_matrix_P.csv",
        "diagnostics/TASK-T06E-P/20260925T075729+08/uncertainty_components_P.json",
        "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_model_contract.json",
        "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/t07_parameter_table.csv",
        "diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08/scenario_registry_filled.csv",
        "diagnostics/TASK-G2/20260925T195336+08/generalized_law_spec.json",
        "diagnostics/TASK-G2/20260925T195336+08/generalized_parameter_qualification.csv",
        "diagnostics/TASK-G2/20260925T195336+08/derivatives_elasticities_and_substitutions.md",
        "diagnostics/TASK-G2/20260925T195336+08/validation_metrics_by_source.csv",
    ],
    "03_结果与中间数据/Q3": [
        "diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv",
        "diagnostics/TASK-T07/20260925T113744+08/context_sensitivity.csv",
        "diagnostics/TASK-T07/20260925T113744+08/structural_transition_diagnostics.csv",
        "diagnostics/TASK-T07/20260925T113744+08/kkt_boundary_checks.csv",
        "diagnostics/TASK-T07/20260925T113744+08/marginal_returns.csv",
        "diagnostics/TASK-T07/20260925T113744+08/quality_cost_sensitivity.csv",
        "diagnostics/TASK-T07/20260925T113744+08/uncertainty_summary.csv",
        "diagnostics/TASK-T07/20260925T113744+08/support_bounds.csv",
    ],
    "03_结果与中间数据/Q4": [
        "diagnostics/TASK-T05/20260925T113355+0800/aggregate_bridge_results.csv",
        "diagnostics/TASK-T05/20260925T113355+0800/taskwise_bridge_results.csv",
        "diagnostics/TASK-T05/20260925T113355+0800/identifiability_decision.json",
        "diagnostics/TASK-G4/20260925T195716+0800/taskwise_coefficients.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/scale_non_scale_contributions.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/forecast_12m_24m_taskwise.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/forecast_auxiliary_composite.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/forecast_uncertainty_components.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/scenario_registry.csv",
        "diagnostics/TASK-G4/20260925T195716+0800/support_oos_audit.csv",
    ],
}
for dst_dir, sources in result_files.items():
    for src in sources:
        copy_file(src, f"{dst_dir}/{Path(src).name}")

# 04 图表、脚本和最小源数据
copy_tree("paper/final_figures/submission_v4", "04_图表/正文图_V4")
copy_file("paper/final_figures/submission_v3/build_submission_v3.py", "04_图表/复用图脚本与源数据/build_submission_v3.py", code=True)
copy_tree("paper/final_figures/submission_v3/source_data", "04_图表/复用图脚本与源数据/source_data")

# 05 引用、许可与AI说明
for name in [
    "references_final.bib",
    "citation_map_final.csv",
    "reference_verification_final.csv",
    "unresolved_citations.csv",
    "OPEN_LLM_LICENSE_HANDLING.md",
    "REFERENCE_AUDIT.md",
]:
    copy_file(f"paper/final_references/{name}", f"05_引用与AI说明/{name}")
copy_file("附件4：“华为杯”第二十三届中国研究生数学建模竞赛人工智能工具及输出使用规定.docx", "05_引用与AI说明/官方AI使用规定.docx")

# 06 正式run的轻量证据，不复制大Parquet、日志和失败run
evidence_runs = [
    ("solution/outputs/quality_q01c/20260924T215718+08", "06_核验与正式run证据/Q01C"),
    ("diagnostics/TASK-T03E/20260925T020032+08", "06_核验与正式run证据/T03E"),
    ("diagnostics/TASK-T06E-B-R1/20260925T103130+08", "06_核验与正式run证据/T06E_B_R1"),
    ("diagnostics/TASK-T06E-P/20260925T075729+08", "06_核验与正式run证据/T06E_P"),
    ("diagnostics/TASK-T06E-INTEGRATE/20260925T110904+08", "06_核验与正式run证据/T06E_INTEGRATE"),
    ("diagnostics/TASK-T07/20260925T113744+08", "06_核验与正式run证据/T07"),
    ("diagnostics/TASK-T05/20260925T113355+0800", "06_核验与正式run证据/T05"),
    ("diagnostics/TASK-G1/20260925T223500+08", "06_核验与正式run证据/G1"),
    ("diagnostics/TASK-G2/20260925T195336+08", "06_核验与正式run证据/G2"),
    ("diagnostics/TASK-G4/20260925T195716+0800", "06_核验与正式run证据/G4"),
]
for src, dst in evidence_runs:
    copy_run_evidence(src, dst)

for name in ["V4_FINAL_CHECKS.json", "v4_build_audit.json", "word_native_check_v4.json", "V4_OUTPUT_MANIFEST.json"]:
    copy_file(f"paper/final_work/_qa/{name}", f"06_核验与正式run证据/论文QA/{name}")

# 根说明文件
readme = """# F题论文与附件汇总（V4）

本目录由现有冻结项目文件**复制**生成，所有源文件均保留在原位置，未移动、未删除。

## 目录

- `00_论文终稿`：当前 V4 Word/PDF、可读源稿与 QA 报告。
- `01_科学冻结`：Q1–Q4 最终科学口径和论文补丁合同。
- `02_源码`：正式流程的源码快照；副本仅增加 AI 辅助前置注释，计算逻辑未改。
- `03_结果与中间数据`：论文实际使用的小型 CSV/JSON/Markdown 结果。
- `04_图表`：正文图的 SVG、矢量 PDF、600 dpi PNG、脚本和最小源数据。
- `05_引用与AI说明`：20 条正式引用、引用映射、许可说明及官方 AI 规定。
- `06_核验与正式run证据`：正式运行的检查、验证、输入输出清单和论文 QA。

## 未复制内容

1. 比赛原始 A/B/C 数据：体积大且主办方已经提供；原位置为 `F题/real_attachments/`。
2. Open LLM Leaderboard 第三方原始快照：复用许可未确认，仅保留精确 commit 引用和汇总结果。
3. 大型行级 Parquet、checkpoint、缓存、失败运行、调试日志和临时文件。
4. 历史旧论文版本、SHOWCASE、参考优秀论文和排版模板。

## 使用提醒

- 正式论文数字以 `01_科学冻结/FINAL_SCIENTIFIC_FREEZE.md` 为准。
- 本目录是“提交附件候选汇总”，正式上传前仍需按比赛系统的附件数量、格式和大小限制选择文件。
- 如需复跑，先把官方原始数据放回项目既定相对位置，再参照各正式 run 的 `input_manifest.json` 和源码快照运行。
"""
(DEST / "README_附件说明.md").write_text(readme, encoding="utf-8")

ai = """# 人工智能工具使用说明

- 工具名称：OpenAI Codex。
- 模型：GPT-5.6 Sol、GPT-6 Astra。
- 开发机构：OpenAI。
- 官方发布日期：2026-07-09、2026-09-03。
- 使用范围：代码起草与调试、结果审查、文字组织、图表排版和引用核对。
- 人工责任：原始评分由作者完成；数据处理、公式、数值、资格词、图表和最终文字由参赛队员复核。AI 未替代人工给出盲审评分，也未生成或篡改实验数据。

为满足源码披露要求，本汇总目录中的 Python 副本在文件顶部增加了上述 AI 辅助注释。该操作只发生在副本中，原项目源码未改动；`SOURCE_COPY_MAP.csv` 同时记录原文件与副本哈希。
"""
(DEST / "05_引用与AI说明" / "AI_DISCLOSURE.md").write_text(ai, encoding="utf-8")

excluded = """# 未纳入汇总目录的材料

| 类型 | 原因 |
|---|---|
| `F题/real_attachments/**` | 主办方原始数据，约 526 MB，不重复上传 |
| Open LLM Leaderboard 原始快照 | 第三方许可未确认 |
| `quality_features_scores.parquet` 等行级大文件 | 体积过大，正文仅使用汇总结果 |
| 全量 `diagnostics/**`、`solution/outputs/**` | 含失败run、调试记录和冗余checkpoint |
| `tmp/**`、`__pycache__/**`、`.pyc` | 临时或缓存文件 |
| 参考优秀论文、模板和旧论文版本 | 不属于提交附件 |
"""
(DEST / "EXCLUDED_FILES.md").write_text(excluded, encoding="utf-8")

# 副本映射
map_path = DEST / "SOURCE_COPY_MAP.csv"
with map_path.open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(copy_records[0].keys()))
    writer.writeheader()
    writer.writerows(copy_records)

# 最终manifest包含说明文件和映射，但不自包含manifest
files = []
for path in sorted(DEST.rglob("*")):
    if path.is_file() and path.name not in {"FILE_MANIFEST.csv", "FILE_MANIFEST.json"}:
        files.append(
            {
                "path": str(path.relative_to(DEST)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

with (DEST / "FILE_MANIFEST.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
    writer.writeheader()
    writer.writerows(files)
(DEST / "FILE_MANIFEST.json").write_text(
    json.dumps({"bundle": DEST.name, "files": files}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

summary = {
    "bundle": str(DEST),
    "files": len(files) + 2,
    "bytes_without_manifest": sum(int(x["bytes"]) for x in files),
    "source_files_modified": False,
    "python_copies_with_ai_header": sum(1 for x in copy_records if x["ai_header_added"]),
}
(DEST / "BUILD_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
