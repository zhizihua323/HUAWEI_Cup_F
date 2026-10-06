# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4_common import (  # noqa: E402
    RUN_DIR, T05, T08, TASKS, iso_local, metric_mae, metric_rmse,
    read_json, safe_quantile, write_csv, write_json, write_stage,
)


def bridge_summary() -> tuple[pd.DataFrame, dict]:
    table = pd.read_csv(T05 / "taskwise_bridge_results.csv", low_memory=False)
    contract = read_json(T05 / "t08_bridge_contract.json")
    main = table[table["main_bridge_eligible"].fillna(False).astype(bool)].copy()
    rows = []
    for target, g in main.groupby("target"):
        y = pd.to_numeric(g["observed"], errors="coerce")
        p = pd.to_numeric(g["predicted"], errors="coerce")
        mask = y.notna() & p.notna()
        y, p = y[mask], p[mask]
        rows.append({
            "benchmark_task": target,
            "n_models": int(len(g)),
            "n_with_prediction": int(len(y)),
            "effective_candidates": "|".join(sorted(g["effective_candidate_id"].dropna().astype(str).unique().tolist())),
            "mae_points": metric_mae(y.to_numpy(float), p.to_numpy(float)) if len(y) else np.nan,
            "rmse_points": metric_rmse(y.to_numpy(float), p.to_numpy(float)) if len(y) else np.nan,
            "residual_median_points": safe_quantile(g["residual"], 0.5),
            "residual_q25_points": safe_quantile(g["residual"], 0.25),
            "residual_q75_points": safe_quantile(g["residual"], 0.75),
            "eligibility": "CONDITIONAL_ASSOCIATION_ONLY",
            "used_to_select_direct_benchmark_model": False,
        })
    counts = {
        "source": str(T05),
        "contract_eligibility": contract.get("eligibility"),
        "bridge_rows": int(len(table)),
        "main_bridge_rows": int(len(main)),
        "main_models": int(main["model_id"].nunique()) if len(main) else 0,
        "main_model_families": int(main["model_family"].nunique()) if len(main) else 0,
        "qualification": "CONDITIONAL_ASSOCIATION_ONLY",
        "loss_to_benchmark_conversion_count": 0,
        "used_in_direct_model_selection": False,
    }
    return pd.DataFrame(rows), counts


def main() -> None:
    write_stage("loss_bridge_sensitivity", "STARTED")
    summary, counts = bridge_summary()
    write_csv(RUN_DIR / "loss_bridge_sensitivity.csv", summary)
    selection_summary = read_json(RUN_DIR / "model_selection_summary.json")
    lines = [
        "# G4 Loss-Benchmark桥接只读敏感性",
        "",
        f"生成时间：{iso_local()}",
        "",
        "## 资格边界",
        "",
        "- 资格：CONDITIONAL_ASSOCIATION_ONLY。",
        "- 本文件不重新运行T05桥接，不重新解析C8 JSON，不重跑Loss模型。",
        "- 桥接只描述前三问Loss与Benchmark的条件联系及误差。",
        "- Loss变化不得换算为Benchmark点数；桥接误差、残差或显著性不得控制G4直接Benchmark候选、门槛或情景。",
        "- 本次Loss-Benchmark数值换算次数为0。",
        "",
        "## 冻结来源",
        "",
        f"- T05 run：{T05.relative_to(T05.parents[2]).as_posix()}",
        f"- 桥接表行数：{counts['bridge_rows']}",
        f"- 主层行数：{counts['main_bridge_rows']}；主层模型数：{counts['main_models']}；模型族数：{counts['main_model_families']}",
        f"- T05合同资格：{counts['contract_eligibility']}",
        "",
        "## 冻结桥接误差（仅条件描述）",
        "",
        "| benchmark | n | MAE | RMSE | residual median | eligibility |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r['benchmark_task']} | {r['n_with_prediction']} | {r['mae_points']:.6g} | "
            f"{r['rmse_points']:.6g} | {r['residual_median_points']:.6g} | {r['eligibility']} |"
        )
    lines += [
        "",
        "## 与G4直接Benchmark模型的隔离",
        "",
        f"- G4直接模型选择是否使用Loss桥接：{selection_summary.get('loss_bridge_used_for_selection')}。",
        "- 直接模型使用C2/C1审计、C3时间、C4元数据和C8 corrected任务分数。",
        "- 直接模型的情景预测与贡献分解不引用本文件的预测值或残差。",
        "",
        "## 允许与禁止表述",
        "",
        "允许：条件关联、桥接误差、来源差异、不可迁移性。",
        "",
        "禁止：可靠统一Loss->Benchmark转换、因果技术进度、用桥接残差替代直接Benchmark模型、用Loss下降直接推未来Benchmark点数。",
    ]
    (RUN_DIR / "loss_bridge_sensitivity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(RUN_DIR / "loss_bridge_summary.json", counts)
    write_stage("loss_bridge_sensitivity", "COMPLETED", **counts)


if __name__ == "__main__":
    main()
