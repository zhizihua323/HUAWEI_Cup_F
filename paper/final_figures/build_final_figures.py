"""Build the frozen final-paper figure bundle.

This script performs display-only transformations of frozen results. It does not
fit models, alter thresholds, clip values, or select observations for aesthetic
reasons. Run from the repository root with the project Anaconda Python.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "final_figures"
OUT.mkdir(parents=True, exist_ok=True)

COL = {
    "blue": "#2E5E8C",
    "blue2": "#7FA6C9",
    "teal": "#4D8F8B",
    "gold": "#C3953E",
    "rose": "#B86B77",
    "red": "#A94442",
    "grey": "#747474",
    "light": "#E8EBED",
    "dark": "#252525",
}

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "font.size": 7.2,
    "axes.titlesize": 8.4,
    "axes.labelsize": 7.4,
    "xtick.labelsize": 6.7,
    "ytick.labelsize": 6.7,
    "legend.fontsize": 6.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.75,
    "legend.frameon": False,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "savefig.facecolor": "white",
})


def rp(path: str) -> Path:
    return ROOT / Path(path)


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def panel(ax, label: str) -> None:
    ax.text(-0.10, 1.04, label, transform=ax.transAxes, fontweight="bold", fontsize=9,
            ha="left", va="bottom")


def write_caption(stem: str, caption: str) -> None:
    (OUT / f"{stem}_caption.md").write_text(caption.strip() + "\n", encoding="utf-8")


def write_source_map(stem: str, records: list[dict]) -> None:
    payload = {"asset": stem, "transformation": "display_only_no_refit_no_clipping", "sources": records}
    (OUT / f"{stem}_source_map.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fig01() -> None:
    stem = "fig01_framework"
    nodes = [
        ("数据与冻结接口", 0.08, 0.78, "输入\n物理记录/模型记录/Benchmark"),
        ("Q1", 0.28, 0.78, "质量代理 Q\n配比预测与运输"),
        ("Q2", 0.50, 0.78, "B1 来源内标度律\n分来源资格"),
        ("Q3", 0.72, 0.78, "三档预算条件优化\n仅 N、D"),
        ("Q4", 0.90, 0.78, "直接 Benchmark\n12/24 月情景"),
        ("边界层", 0.50, 0.25, "资格标签贯穿全文：\nPARTIALLY_STABLE / VALIDATION_FAILED /\nCONDITIONAL_OPTIMUM / SCENARIO_ONLY_UNVALIDATED"),
    ]
    edges = [[0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [2, 5], [3, 5], [4, 5]]
    (OUT / f"{stem}_source.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fig, ax = plt.subplots(figsize=(7.2, 3.35))
    ax.set_axis_off()
    for i, (_, x, y, text) in enumerate(nodes):
        w, h = (0.17, 0.25) if i < 5 else (0.48, 0.25)
        fc = COL["light"] if i == 0 else ("#DDE9F2" if i < 5 else "#F3E7E9")
        box = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                             boxstyle="round,pad=0.012,rounding_size=0.018",
                             linewidth=0.9, edgecolor=COL["dark"], facecolor=fc,
                             hatch=None if i < 5 else "//")
        ax.add_patch(box)
        ax.text(x, y, text, ha="center", va="center", fontsize=7.2,
                fontweight="bold" if i in (1, 2, 3, 4) else "normal")
    for a, b in edges:
        xa, ya = nodes[a][1], nodes[a][2]
        xb, yb = nodes[b][1], nodes[b][2]
        if b == 5:
            ax.annotate("", xy=(xb, yb + 0.13), xytext=(xa, ya - 0.14),
                        arrowprops=dict(arrowstyle="-|>", lw=0.8, color=COL["grey"]))
        else:
            ax.annotate("", xy=(xb - 0.09, yb), xytext=(xa + 0.09, ya),
                        arrowprops=dict(arrowstyle="-|>", lw=1.0, color=COL["blue"]))
    ax.text(0.5, 0.98, "四问建模主线与证据资格闭环", ha="center", va="top",
            fontsize=10.5, fontweight="bold")
    ax.text(0.5, 0.055, "所有数值均来自冻结接口；图表层只改变表达，不改变科学结果。",
            ha="center", color=COL["grey"], fontsize=6.8)
    save_figure(fig, stem)
    write_caption(stem, """
图 1 | 四问建模主线与证据资格闭环。Q1 从冻结质量信号构造操作性质量代理并检验配比运输；Q2 在 B1 来源内估计标度律，并逐来源报告外部验证资格；Q3 在冻结模型、支持域和 H=2048 下给出三档预算的条件最优 N 与 D；Q4 基于直接 Benchmark 接口给出 12/24 个月的未验证数值情景。底部边界层表示资格标签必须随结论、图题和表注同步传播。该图仅表示冻结分析结构，不包含新的科学估计。
""")
    write_source_map(stem, [{"file": "paper/FINAL_RESULT_INDEX_V2.md", "fields": "Q1-Q4 final interface and eligibility", "unit": "none", "denominator": "not applicable"}])


def fig02() -> None:
    stem = "fig02_q1_quality_validation"
    stats = pd.read_csv(rp("diagnostics/TASK-G1/20260925T223500+08/manual_validation_statistics.csv"))
    stats = stats[stats["analysis"].str.startswith("spearman_Q_vs_")].copy()
    labels = ["总体质量", "可读性", "完整性", "污染度"]
    stats["display_metric"] = labels
    source = pd.DataFrame([
        {"section": "denominator", "item": "physical_rows", "value": 272505, "ci_low": np.nan, "ci_high": np.nan, "n": 272505, "unit": "count"},
        {"section": "denominator", "item": "unique_keys", "value": 261086, "ci_low": np.nan, "ci_high": np.nan, "n": 261086, "unit": "count"},
        {"section": "denominator", "item": "Q_valid", "value": 261067, "ci_low": np.nan, "ci_high": np.nan, "n": 261086, "unit": "count"},
        {"section": "denominator", "item": "Q_missing", "value": 19, "ci_low": np.nan, "ci_high": np.nan, "n": 261086, "unit": "count"},
        {"section": "extension", "item": "A2_passed_criteria", "value": 1, "ci_low": np.nan, "ci_high": np.nan, "n": 4, "unit": "criteria"},
        {"section": "extension", "item": "A3_passed_criteria", "value": 3, "ci_low": np.nan, "ci_high": np.nan, "n": 4, "unit": "criteria"},
    ])
    manual = stats[["display_metric", "effect_size", "ci_low_2_5pct", "ci_high_97_5pct", "n_a"]].rename(
        columns={"display_metric": "item", "effect_size": "value", "ci_low_2_5pct": "ci_low", "ci_high_97_5pct": "ci_high", "n_a": "n"}
    )
    manual["section"] = "manual_validation"
    manual["unit"] = "spearman_rho"
    source = pd.concat([source, manual[source.columns]], ignore_index=True)
    source.to_csv(OUT / f"{stem}_source.csv", index=False, encoding="utf-8-sig")

    fig = plt.figure(figsize=(7.2, 5.15))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1], hspace=0.42, wspace=0.34)
    ax0 = fig.add_subplot(gs[0, :]); ax0.set_axis_off(); panel(ax0, "a")
    x0s = [0.08, 0.33, 0.58, 0.84]
    texts = [
        "11 个冻结特征\n可用性 5 / 知识 3 / 教育推理 3",
        "组内等权\n任一组内缺失则该组缺失",
        "三组等权\n缺失不重分配权重",
        "Q_baseline\n261067 有效 / 19 缺失",
    ]
    for i, (x, txt) in enumerate(zip(x0s, texts)):
        box = FancyBboxPatch((x - 0.105, 0.30), 0.21, 0.37,
                             boxstyle="round,pad=0.012", fc="#E5EDF4" if i != 3 else "#F1E5E8",
                             ec=COL["dark"], lw=0.8, hatch=None if i < 3 else "//")
        ax0.add_patch(box); ax0.text(x, 0.485, txt, ha="center", va="center", fontsize=7.2)
        if i < 3:
            ax0.annotate("", xy=(x0s[i+1]-0.115, 0.485), xytext=(x+0.115, 0.485),
                         arrowprops=dict(arrowstyle="-|>", color=COL["blue"], lw=1.0))
    ax0.text(0.5, 0.12, "操作性质量代理；不是人工真值或语义质量金标准", ha="center",
             color=COL["red"], fontweight="bold")

    ax1 = fig.add_subplot(gs[1, 0]); panel(ax1, "b")
    passed = [1, 3]; failed = [3, 1]; xx = np.arange(2)
    ax1.bar(xx, passed, color=[COL["blue"], COL["teal"]], edgecolor=COL["dark"], label="通过", hatch=["//", ".."])
    ax1.bar(xx, failed, bottom=passed, color="white", edgecolor=COL["dark"], label="未通过", hatch="xx")
    ax1.set_xticks(xx, ["A2 扩展", "A3 扩展"]); ax1.set_ylim(0, 4.45); ax1.set_yticks(range(5)); ax1.set_ylabel("全局判据数（共 4 项）")
    ax1.legend(loc="upper left", ncol=2)
    ax1.text(0.5, 4.2, "共同有效域均为 1：域级门槛 NOT_EVALUABLE", ha="center", fontsize=6.4, color=COL["red"])

    ax2 = fig.add_subplot(gs[1, 1]); panel(ax2, "c")
    y = np.arange(len(stats)); est = stats["effect_size"].to_numpy(); lo = stats["ci_low_2_5pct"].to_numpy(); hi = stats["ci_high_97_5pct"].to_numpy()
    ax2.axvline(0, color=COL["grey"], lw=0.8, ls="--")
    ax2.errorbar(est, y, xerr=[est-lo, hi-est], fmt="o", color=COL["blue"], ecolor=COL["blue2"], capsize=2.5, lw=1)
    ax2.set_yticks(y, [f"{m} (n={int(n)})" for m, n in zip(labels, stats["n_a"])])
    ax2.invert_yaxis(); ax2.set_xlim(-0.66, 0.48); ax2.set_xlabel("Spearman ρ（95% bootstrap 区间）")
    ax2.text(0.98, 0.04, "有限盲审未显示\n稳定正向一致性", transform=ax2.transAxes,
             ha="right", va="bottom", color=COL["red"], fontweight="bold")
    fig.suptitle("Q1 质量构造、扩展稳定性与人工盲审", fontsize=10.5, fontweight="bold", y=0.985)
    save_figure(fig, stem)
    write_caption(stem, """
图 2 | Q1 质量构造、扩展稳定性与人工盲审。a，主 Q 由 11 个冻结特征构成，可用性、知识、教育推理三组分别组内等权、组间等权；任一主特征缺失均严格传播，272505 条物理记录对应 261086 个唯一键，其中 Q 有效 261067、缺失 19。b，A2 与 A3 扩展的四项全局判据分别通过 1 项和 3 项，整体资格为 PARTIALLY_STABLE；二者共同有效域均只有 1 个，因此域级门槛 NOT_EVALUABLE。c，作者盲审采用逐指标成对有效分母，点为 Spearman ρ，线为 2000 次 bootstrap 的 95% 区间；总体质量、可读性、完整性与污染度的 n 分别为 47、47、47、46。污染度越低越好。结果未显示稳定正向一致性，Q 仅作为操作性质量代理。
""")
    write_source_map(stem, [
        {"file": "solution/outputs/quality_q01c/20260924T215718+08/run_config.json", "fields": "primary_q_rule; group_rule", "unit": "0-1", "denominator": "11-feature strict complete case"},
        {"file": "paper/FINAL_PAPER_PATCH_CONTRACT.md", "fields": "Q1 final denominator and A2/A3 passed criteria", "unit": "count", "denominator": "physical rows and unique keys reported separately"},
        {"file": "diagnostics/TASK-G1/20260925T223500+08/manual_validation_statistics.csv", "fields": "effect_size; ci_low_2_5pct; ci_high_97_5pct; n_a", "unit": "Spearman rho", "denominator": "pairwise complete author ratings"},
    ])


def _melt_regmix(path: str, scale: str) -> pd.DataFrame:
    wide = pd.read_csv(rp(path))
    rows = []
    for col in wide.columns:
        if not col.startswith("actual_metric/"):
            continue
        suffix = col[len("actual_metric/"):]
        pred = "pred_metric/" + suffix
        frame = pd.DataFrame({"scale": scale, "index": wide["index"], "domain": suffix,
                              "observed_loss": wide[col], "predicted_loss": wide[pred]})
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def fig03() -> None:
    stem = "fig03_q1_regmix_transport"
    parts = [
        _melt_regmix("solution/outputs/mixture/linear_test_1m_predictions.csv", "1M"),
        _melt_regmix("solution/outputs/mixture/linear_test_60m_predictions.csv", "60M"),
        _melt_regmix("solution/outputs/mixture/linear_test_1B_predictions.csv", "1B"),
    ]
    src = pd.concat(parts, ignore_index=True)
    src.to_csv(OUT / f"{stem}_source.csv", index=False, encoding="utf-8-sig")
    metrics = pd.read_csv(rp("solution/outputs/mixture/metrics.csv"))
    metric_rows = {
        "1M": metrics[(metrics.model == "linear") & (metrics.set == "test_1m")].iloc[0],
        "60M": metrics[(metrics.model == "linear") & (metrics.set == "test_60m")].iloc[0],
        "1B": metrics[(metrics.model == "linear") & (metrics.set == "test_1B")].iloc[0],
    }
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.72), constrained_layout=True)
    roles = {"1M": "同尺度独立检验", "60M": "零样本跨尺度运输", "1B": "零样本跨尺度运输"}
    for label, ax in zip(["a", "b", "c"], axes):
        scale = ["1M", "60M", "1B"][["a", "b", "c"].index(label)]
        d = src[src.scale == scale]
        ax.scatter(d.observed_loss, d.predicted_loss, s=5, alpha=0.16,
                   color=COL["blue"], edgecolors="none", rasterized=True)
        mn = min(d.observed_loss.min(), d.predicted_loss.min()); mx = max(d.observed_loss.max(), d.predicted_loss.max())
        ax.plot([mn, mx], [mn, mx], ls="--", lw=0.8, color=COL["grey"])
        ax.set_xlim(mn, mx); ax.set_ylim(mn, mx); ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("观测 Loss"); ax.set_ylabel("预测 Loss")
        m = metric_rows[scale]
        ax.set_title(f"{scale} · {roles[scale]}")
        ax.text(0.04, 0.96, f"n={int(m['n'])} mixtures\nRMSE={m['rmse_all_domains']:.3f}\nρ={m['spearman_equal_domain_mean']:.3f}",
                transform=ax.transAxes, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=COL["light"], alpha=0.9))
        panel(ax, label)
    fig.suptitle("Q1 RegMix 配比预测及跨尺度运输", fontsize=10.5, fontweight="bold")
    save_figure(fig, stem)
    write_caption(stem, """
图 3 | Q1 RegMix 配比预测及跨尺度运输。a，1M 独立同尺度检验；b、c，将同一冻结线性关系零样本运输至 60M 和 1B。散点包含对应冻结预测文件中的全部混合配比和全部 13 个验证域，虚线为预测等于观测。面板内 n 为混合配比数，RMSE 为全域指标，ρ 为等权域 Spearman 相关。1M 结果可称 SAME_SCALE_TEST；60M 和 1B 仅为 TRANSPORT_ONLY，不构成跨尺度重新验证。
""")
    write_source_map(stem, [
        {"file": "solution/outputs/mixture/linear_test_1m_predictions.csv", "fields": "all actual_metric/* and pred_metric/*", "unit": "Loss", "denominator": "256 mixtures x 13 domains"},
        {"file": "solution/outputs/mixture/linear_test_60m_predictions.csv", "fields": "all actual_metric/* and pred_metric/*", "unit": "Loss", "denominator": "256 mixtures x 13 domains"},
        {"file": "solution/outputs/mixture/linear_test_1B_predictions.csv", "fields": "all actual_metric/* and pred_metric/*", "unit": "Loss", "denominator": "64 mixtures x 13 domains"},
        {"file": "solution/outputs/mixture/metrics.csv", "fields": "n; rmse_all_domains; spearman_equal_domain_mean; role", "unit": "Loss; rank correlation", "denominator": "frozen scale-specific test sets"},
    ])


def fig04() -> None:
    stem = "fig04_q2_fit_validation"
    b1 = pd.read_csv(rp("solution/outputs/scaling/B1_all_predictions.csv"))
    val = pd.read_parquet(rp("diagnostics/TASK-G2/20260925T195336+08/validation_predictions.parquet"))
    metric = pd.read_csv(rp("diagnostics/TASK-G2/20260925T195336+08/validation_metrics_by_source.csv"))
    audit = pd.read_csv(rp("diagnostics/TASK-G2/20260925T195336+08/support_oos_audit.csv"))
    large = pd.read_csv(rp("diagnostics/TASK-G2/20260925T195336+08/large_model_gt10b_audit.csv"))
    use = val[val.source_id.isin(["B2", "B3", "B4", "B5"]) & val.prediction_valid & val.actual_loss.notna()].copy()
    src_b1 = b1[["run_id", "N_params_B", "D_tokens_B", "val_loss", "prediction", "residual_pred_minus_actual", "split"]].copy()
    src_b1.insert(0, "source_id", "B1")
    src_val = use[["source_id", "row_id", "N_B", "D_B", "actual_loss", "frozen_M0_B1_prediction", "support_status", "oos_flag", "loss_is_ground_truth"]]
    src_b1.to_csv(OUT / f"{stem}_source_b1.csv", index=False, encoding="utf-8-sig")
    src_val.to_csv(OUT / f"{stem}_source_validation.csv", index=False, encoding="utf-8-sig")

    fig = plt.figure(figsize=(7.2, 5.05))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1], hspace=0.42, wspace=0.36)
    ax0 = fig.add_subplot(gs[0, 0]); panel(ax0, "a")
    ax0.scatter(b1.val_loss, b1.prediction, s=13, facecolor=COL["blue2"], edgecolor=COL["dark"], linewidth=0.25, alpha=0.75)
    mn = min(b1.val_loss.min(), b1.prediction.min()); mx = max(b1.val_loss.max(), b1.prediction.max())
    ax0.plot([mn, mx], [mn, mx], ls="--", color=COL["grey"], lw=0.8)
    ax0.set_xlabel("B1 观测验证 Loss"); ax0.set_ylabel("M0_B1 拟合 Loss"); ax0.set_title(f"B1 来源内拟合（n={len(b1)}）")
    ax0.text(0.04, 0.96, "支持框：\nN_B∈[0.070542,11.965825]\nD_B∈[0.134,299.893]",
             transform=ax0.transAxes, va="top", bbox=dict(boxstyle="round", fc="white", ec=COL["light"]))

    ax1 = fig.add_subplot(gs[0, 1]); panel(ax1, "b")
    source_colors = {"B2": COL["rose"], "B3": COL["blue"], "B4": COL["gold"], "B5": COL["teal"]}
    for sid in ["B2", "B3", "B4", "B5"]:
        d = use[use.source_id == sid]
        ins = d[d.in_B1_box]; oos = d[~d.in_B1_box]
        ax1.scatter(ins.actual_loss, ins.frozen_M0_B1_prediction, s=8, alpha=0.25,
                    color=source_colors[sid], marker="o", label=f"{sid} 支持内")
        if len(oos):
            ax1.scatter(oos.actual_loss, oos.frozen_M0_B1_prediction, s=10, alpha=0.26,
                        facecolors="none", edgecolors=source_colors[sid], marker="s", linewidths=0.45,
                        label=f"{sid} OOS")
    lim_lo = min(use.actual_loss.min(), use.frozen_M0_B1_prediction.min()); lim_hi = max(use.actual_loss.max(), use.frozen_M0_B1_prediction.max())
    ax1.plot([lim_lo, lim_hi], [lim_lo, lim_hi], ls="--", color=COL["grey"], lw=0.8)
    ax1.set_xlabel("来源观测 Loss"); ax1.set_ylabel("冻结 M0_B1 预测 Loss"); ax1.set_title("B2–B5 分来源验证（全部有效行）")
    ax1.legend(ncol=2, loc="lower right", fontsize=5.4, handletextpad=0.25, columnspacing=0.55)

    ax2 = fig.add_subplot(gs[1, :]); panel(ax2, "c")
    rows = []
    for sid in ["B2", "B3", "B4", "B5"]:
        r = audit[audit.source_id == sid].iloc[0]
        mr = metric[(metric.source_id == sid) & (metric.subset == "IN_SUPPORT")].iloc[0]
        rows.append((sid, int(r.in_B1_box_rows), int(r.finite_positive_N_D_rows-r.in_B1_box_rows), float(mr.rmse), mr.final_qualification))
    for sid in ["B9", "B10"]:
        r = large[large.source_id == sid].iloc[0]
        rows.append((sid, int(r.inside_B1_box_records), int(r.finite_frozen_prediction_records-r.inside_B1_box_records), np.nan, r.final_qualification))
    y = np.arange(len(rows)); inside = [r[1] for r in rows]; outside = [r[2] for r in rows]
    totals = [a + b for a, b in zip(inside, outside)]
    ax2.barh(y, totals, color="white", edgecolor=COL["dark"], hatch="xx", label="全部有效记录")
    ax2.barh(y, inside, color=COL["blue2"], edgecolor=COL["dark"], hatch="//", label="其中支持内")
    ax2.set_yticks(y, [r[0] for r in rows]); ax2.invert_yaxis(); ax2.set_xlabel("记录数（对数轴）"); ax2.set_xscale("symlog", linthresh=1)
    ax2.legend(loc="lower right")
    for yi, r in enumerate(rows):
        suffix = "真实误差不可计算" if np.isnan(r[3]) else f"支持内 RMSE={r[3]:.6g}"
        ax2.text(max(r[1]+r[2], 1)*1.08, yi, f"{suffix} · {r[4]}", va="center", fontsize=5.9,
                 color=COL["red"] if "FAILED" in str(r[4]) or "ONLY" in str(r[4]) else COL["dark"])
    ax2.set_xlim(0, max([r[1]+r[2] for r in rows])*13)
    fig.suptitle("Q2 B1 来源内拟合与分来源外部验证资格", fontsize=10.5, fontweight="bold", y=0.985)
    save_figure(fig, stem)
    write_caption(stem, """
图 4 | Q2 B1 来源内拟合与分来源外部验证资格。a，冻结 M0_B1 在 B1 来源内的观测与拟合；支持框为 N_B∈[0.070542,11.965825]、D_B∈[0.134,299.893]，单位分别为十亿参数和十亿 token。b，B2–B5 的全部有效预测行按来源绘制，实心圆为支持内、空心方形为 OOS；各来源不合并计算 RMSE。c，逐来源支持内/OOS 记录数和最终资格。B2、B4、B5 为 VALIDATION_FAILED；B3 为同源 Pythia 插值下的 VALIDATION_SUPPORTED，不是独立复制；B9 无观测 Loss，仅 OOS_STRESS_ONLY；B10 的 Loss 为估算参考，仅 ESTIMATED_SCENARIO_ONLY。
""")
    write_source_map(stem, [
        {"file": "solution/outputs/scaling/B1_all_predictions.csv", "fields": "val_loss; prediction; N_params_B; D_tokens_B", "unit": "Loss; billion parameters; billion tokens", "denominator": "all B1 rows"},
        {"file": "diagnostics/TASK-G2/20260925T195336+08/validation_predictions.parquet", "fields": "source_id; actual_loss; frozen_M0_B1_prediction; in_B1_box; oos_flag", "unit": "Loss", "denominator": "all prediction_valid rows with observed loss for B2-B5"},
        {"file": "diagnostics/TASK-G2/20260925T195336+08/validation_metrics_by_source.csv", "fields": "IN_SUPPORT n; rmse; final_qualification", "unit": "Loss", "denominator": "source-specific support-in rows"},
        {"file": "diagnostics/TASK-G2/20260925T195336+08/large_model_gt10b_audit.csv", "fields": "finite_frozen_prediction_records; inside_B1_box_records; final_qualification", "unit": "count", "denominator": "B9/B10 records"},
    ])


def fig05() -> None:
    stem = "fig05_q3_budget_optima"
    d = pd.read_csv(rp("diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv"))
    d = d[(d.scenario_id == "S00_NULL_M0_B1") & (d.H == 2048)].copy().sort_values("budget_flops")
    cols = ["budget_flops", "H", "N_B", "D_B", "predicted_loss", "active_constraints", "support_status", "Q_status", "p_status"]
    d[cols].to_csv(OUT / f"{stem}_source.csv", index=False, encoding="utf-8-sig")
    x = np.arange(3); labs = [r"$10^{18}$", r"$10^{20}$", r"$10^{22}$"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.75), constrained_layout=True)
    specs = [("N_B", "最优 N_B\n（十亿参数）", COL["blue"], "//"),
             ("D_B", "最优 D_B\n（十亿 token）", COL["teal"], ".."),
             ("predicted_loss", "冻结预测 Loss", COL["rose"], "xx")]
    for i, (ax, (field, ylabel, color, hatch)) in enumerate(zip(axes, specs)):
        vals = d[field].to_numpy()
        ax.plot(x, vals, color=color, marker="o", lw=1.7, ms=5)
        ax.fill_between(x, vals, np.min(vals)*0.93 if field != "predicted_loss" else np.min(vals)-0.08,
                        color=color, alpha=0.10, hatch=hatch, edgecolor=color)
        if field in ("N_B", "D_B"):
            ax.set_yscale("log")
        ax.set_xticks(x, labs); ax.set_xlabel("预算 FLOPs"); ax.set_ylabel(ylabel); panel(ax, chr(ord("a")+i))
        for xi, v in zip(x, vals): ax.annotate(f"{v:.6g}", (xi, v), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=6.1)
        if field == "D_B":
            ax.scatter([2], [vals[-1]], s=70, facecolors="none", edgecolors=COL["red"], lw=1.2)
            ax.text(0.98, 0.06, "10²²：D 达到 B1 上界\n299.893", transform=ax.transAxes, ha="right", color=COL["red"], fontsize=6.2)
    fig.suptitle("Q3 三档预算下的冻结支持域内条件最优", fontsize=10.5, fontweight="bold")
    save_figure(fig, stem)
    write_caption(stem, """
图 5 | Q3 三档预算下的冻结支持域内条件最优。a–c，在正式主场景 S00_NULL_M0_B1、H=2048 下，仅优化 N 与 D，分别给出十亿参数、十亿 token 和冻结预测 Loss。预算为 10^18、10^20、10^22 FLOPs。10^22 档的 D_B=299.893，达到 B1 支持上界，以空心红圈标识。Q 为 NOT_IDENTIFIED_NOT_OPTIMIZED，p 为 FIXED_P0_NOT_OPTIMIZED；结果只能解释为冻结模型、预算与支持域内的 CONDITIONAL_OPTIMUM。
""")
    write_source_map(stem, [{"file": "diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv", "fields": "; ".join(cols), "unit": "FLOPs; billion parameters; billion tokens; Loss", "denominator": "scenario S00_NULL_M0_B1 and H=2048 only"}])


def fig06() -> None:
    stem = "fig06_q4_scenarios"
    d = pd.read_csv(rp("diagnostics/TASK-G4/20260925T195716+0800/forecast_12m_24m_taskwise.csv"))
    aux = pd.read_csv(rp("diagnostics/TASK-G4/20260925T195716+0800/forecast_auxiliary_composite.csv"))
    d = pd.concat([d, aux], ignore_index=True)
    cols = ["benchmark_task", "target_role", "scenario_id", "scenario_order", "horizon_months", "forecast_origin", "forecast_date", "selected_contribution_model", "scenario_model", "forecast_eligibility", "prediction_points", "loss_bridge_used"]
    d[cols].to_csv(OUT / f"{stem}_source.csv", index=False, encoding="utf-8-sig")
    tasks = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO", "six_task_mean_complete_only"]
    display = {"six_task_mean_complete_only": "六任务均值（辅助）"}
    scenarios = ["SLOW", "BASELINE", "UPPER_SENSITIVITY"]
    colors = [COL["grey"], COL["blue"], COL["rose"]]
    markers = ["o", "s", "^"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.9), sharey=True, constrained_layout=True)
    y = np.arange(len(tasks))
    for j, (ax, horizon) in enumerate(zip(axes, [12, 24])):
        for k, (sc, color, marker) in enumerate(zip(scenarios, colors, markers)):
            vals = []
            for task in tasks:
                vals.append(float(d[(d.benchmark_task == task) & (d.horizon_months == horizon) & (d.scenario_id == sc)].prediction_points.iloc[0]))
            ax.plot(vals, y, marker=marker, color=color, lw=1.2, ms=4.5, label=sc,
                    ls=["--", "-", ":"][k])
        ax.axvline(0, color=COL["dark"], lw=0.8, ls="--")
        ax.set_yticks(y, [display.get(t, t) for t in tasks]); ax.invert_yaxis()
        ax.set_xlabel("Benchmark 点（原始未截断值）"); ax.set_title(f"{horizon} 个月 · {2025+horizon//12}-01-28")
        panel(ax, chr(ord("a")+j))
        ax.text(0.02, 0.02, "SCENARIO_ONLY_UNVALIDATED", transform=ax.transAxes, ha="left", va="bottom",
                color="white", fontweight="bold", fontsize=7.2,
                bbox=dict(boxstyle="round,pad=0.22", fc=COL["red"], ec=COL["red"]))
        if horizon == 24:
            math_base = float(d[(d.benchmark_task == "MATH Lvl 5") & (d.horizon_months == 24) & (d.scenario_id == "BASELINE")].prediction_points.iloc[0])
            ax.annotate(f"保留负值 {math_base:.3f}", xy=(math_base, 2), xytext=(8, -18), textcoords="offset points",
                        arrowprops=dict(arrowstyle="->", color=COL["red"], lw=0.8), color=COL["red"], fontsize=6.3)
    axes[1].legend(loc="lower right", title="数学情景", fontsize=6.1, title_fontsize=6.3)
    fig.suptitle("Q4 六任务及辅助均值的 12/24 月三情景", fontsize=10.5, fontweight="bold")
    save_figure(fig, stem)
    write_caption(stem, """
图 6 | Q4 六任务及辅助均值的 12/24 月三情景。a、b，以 2025-01-28 为原点，分别展示 2026-01-28 和 2027-01-28 的 SLOW、BASELINE、UPPER_SENSITIVITY 数学情景，单位为 Benchmark 点。所有数值均为 SCENARIO_ONLY_UNVALIDATED，且时间位于训练范围外；情景增长率来自预注册数学网格，不是历史估计。MATH Lvl 5 的 24 个月三项原始预测均为负值，图中不截断、不替换为 0。直接 Benchmark 模型未使用 Loss，Loss 到 Benchmark 的数值转换次数为 0。
""")
    write_source_map(stem, [
        {"file": "diagnostics/TASK-G4/20260925T195716+0800/forecast_12m_24m_taskwise.csv", "fields": "; ".join(cols), "unit": "Benchmark points; date", "denominator": "6 primary tasks x 3 scenarios x 2 horizons"},
        {"file": "diagnostics/TASK-G4/20260925T195716+0800/forecast_auxiliary_composite.csv", "fields": "; ".join(cols), "unit": "Benchmark points; date", "denominator": "1 auxiliary composite x 3 scenarios x 2 horizons"},
    ])


def fig07() -> None:
    stem = "fig07_qualification_map"
    rows = [
        ("Q1 主 Q", "操作性代理", "CLOSED_WITH_LIMITATION", "人工核验弱且方向不一致"),
        ("Q1 A2/A3", "PARTIALLY_STABLE", "NOT_EVALUABLE（域级）", "全局判据 1/4 与 3/4"),
        ("Q2 B1", "来源内识别", "条件广义表达", "不同来源模块不可合并资格"),
        ("Q2 B2/B4/B5", "外部检验", "VALIDATION_FAILED", "负结果必须保留"),
        ("Q2 B3", "同源插值支持", "VALIDATION_SUPPORTED", "非独立复制"),
        ("Q2 B9/B10", "OOS/估算", "SCENARIO_ONLY", "不得宣称大模型真值外推"),
        ("Q3 三档预算", "条件优化", "CONDITIONAL_OPTIMUM", "Q 未识别；p 固定"),
        ("Q4 12/24 月", "数值情景", "SCENARIO_ONLY_UNVALIDATED", "M2 未通过升级门槛"),
    ]
    pd.DataFrame(rows, columns=["object", "evidence_role", "eligibility", "boundary"]).to_csv(
        OUT / f"{stem}_source.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(7.2, 4.25))
    ax.set_xlim(0, 10); ax.set_ylim(-0.7, len(rows)+0.2); ax.set_axis_off()
    header_y = len(rows)-0.08
    ax.text(0.2, header_y, "对象", fontweight="bold"); ax.text(2.0, header_y, "证据角色", fontweight="bold")
    ax.text(4.2, header_y, "最终资格", fontweight="bold"); ax.text(7.0, header_y, "解释边界", fontweight="bold")
    for i, r in enumerate(rows):
        yy = len(rows)-1-i
        ax.add_patch(FancyBboxPatch((0.05, yy-0.34), 9.75, 0.66, boxstyle="round,pad=0.01",
                                    fc="white" if i % 2 else "#F3F5F6", ec="#D5D8DA", lw=0.55,
                                    hatch="" if i % 2 else ".."))
        ax.text(0.2, yy, r[0], va="center", fontweight="bold")
        ax.text(2.0, yy, r[1], va="center")
        col = COL["red"] if any(k in r[2] for k in ["FAILED", "UNVALIDATED", "SCENARIO_ONLY", "NOT_EVALUABLE"]) else COL["blue"]
        ax.text(4.2, yy, r[2], va="center", color=col, fontweight="bold", fontsize=6.5)
        ax.text(7.0, yy, r[3], va="center", fontsize=6.4)
    ax.set_title("全文结果资格与解释边界", fontsize=10.5, fontweight="bold", pad=24)
    save_figure(fig, stem)
    write_caption(stem, """
图 7 | 全文结果资格与解释边界。各行按对象、证据角色、最终资格和不可越过的解释边界汇总 Q1–Q4 的冻结状态。该图用于防止把操作性代理写成人工真值、把来源内拟合写成统一多源验证、把条件最优写成全局最优，或把数值情景写成经验证预测。所有资格以 SCIENCE_CLOSED 接口为准。
""")
    write_source_map(stem, [{"file": "paper/FINAL_SCIENTIFIC_FREEZE.md", "fields": "Q1-Q4 final status, allowed and prohibited interpretation", "unit": "none", "denominator": "not applicable"}, {"file": "paper/FINAL_PAPER_PATCH_CONTRACT.md", "fields": "mandatory figure/table qualification language", "unit": "none", "denominator": "not applicable"}])


BUILDERS = {
    "FIG-01": fig01,
    "FIG-02": fig02,
    "FIG-03": fig03,
    "FIG-04": fig04,
    "FIG-05": fig05,
    "FIG-06": fig06,
    "FIG-07": fig07,
}


def write_wrappers() -> None:
    for asset, func in BUILDERS.items():
        idx = asset.split("-")[1]
        path = OUT / f"generate_fig{idx}.py"
        path.write_text(
            "from build_final_figures import BUILDERS\n"
            f"BUILDERS[{asset!r}]()\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--figure", choices=["all", *BUILDERS], default="all")
    args = parser.parse_args()
    if args.figure == "all":
        for fn in BUILDERS.values():
            fn()
    else:
        BUILDERS[args.figure]()
    write_wrappers()


if __name__ == "__main__":
    main()
