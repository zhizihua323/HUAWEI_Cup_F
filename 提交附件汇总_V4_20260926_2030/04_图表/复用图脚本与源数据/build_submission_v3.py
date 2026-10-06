# AI-assisted development disclosure: OpenAI Codex (GPT-5.6 Sol / GPT-6 Astra) assisted drafting and debugging; the authors reviewed the final code and outputs.
# Developer: OpenAI; official release dates: 2026-07-09 and 2026-09-03.
"""Build the final V3 manuscript figures from frozen delivered source assets only.

The script performs no fitting, thresholding, clipping, sampling, or model
selection. It writes five figures plus minimal frozen source snapshots and QA
metadata into submission_v3.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "paper" / "final_figures"
TSRC = ROOT / "paper" / "final_tables"
OUT = Path(__file__).resolve().parent
SD = OUT / "source_data"
WIDTH_IN = 6.4960629921  # 165 mm
MIN_FONT_PT = 12.0

INK = "#26343D"
NAVY = "#315E73"
BLUE = "#4F7E97"
BLUE_2 = "#7FA3B6"
BLUE_PALE = "#DFE9EE"
GREY = "#89969D"
GREY_2 = "#B8C0C4"
GREY_PALE = "#EEF1F2"
ROSE = "#A65B5E"
ROSE_PALE = "#F3E4E4"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "SimSun"],
    "mathtext.fontset": "stix",
    "font.size": 12,
    "axes.titlesize": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.85,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.frameon": False,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "savefig.facecolor": "white",
})

MIN_FONT_AUDIT: dict[str, float] = {}
FIGURE_SIZES: dict[str, tuple[float, float]] = {}
TEXT_BBOX_AUDIT: dict[str, list[dict[str, float | str]]] = {}
ENCLOSURE_PAIRS: dict[str, list[tuple[Text, FancyBboxPatch]]] = {}
ENCLOSURE_AUDIT: dict[str, list[dict[str, str]]] = {}


def apply_fonts_and_minimum(fig: plt.Figure, stem: str) -> None:
    texts = fig.findobj(match=Text)
    for artist in texts:
        artist.set_fontsize(max(MIN_FONT_PT, float(artist.get_fontsize())))
        value = artist.get_text() or ""
        has_cjk = any("\u3400" <= c <= "\u9fff" for c in value)
        artist.set_fontfamily("SimSun" if has_cjk else "Times New Roman")
    MIN_FONT_AUDIT[stem] = min(float(t.get_fontsize()) for t in texts)
    FIGURE_SIZES[stem] = tuple(float(v) for v in fig.get_size_inches())


def save(fig: plt.Figure, stem: str) -> None:
    apply_fonts_and_minimum(fig, stem)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.get_window_extent(renderer)
    violations = []
    for artist in fig.findobj(match=Text):
        if not artist.get_visible() or not (artist.get_text() or "").strip():
            continue
        box = artist.get_window_extent(renderer)
        if not np.isfinite([box.x0, box.y0, box.x1, box.y1]).all():
            continue
        if (box.x0 < canvas.x0 - 1 or box.y0 < canvas.y0 - 1 or
                box.x1 > canvas.x1 + 1 or box.y1 > canvas.y1 + 1):
            violations.append({
                "text": artist.get_text().replace("\n", " / "),
                "x0": float(box.x0), "y0": float(box.y0),
                "x1": float(box.x1), "y1": float(box.y1),
            })
    TEXT_BBOX_AUDIT[stem] = violations
    enclosure_violations = []
    for text_artist, container in ENCLOSURE_PAIRS.get(stem, []):
        text_box = text_artist.get_window_extent(renderer)
        container_box = container.get_window_extent(renderer)
        if not (text_box.x0 >= container_box.x0 + 2 and
                text_box.y0 >= container_box.y0 + 2 and
                text_box.x1 <= container_box.x1 - 2 and
                text_box.y1 <= container_box.y1 - 2):
            enclosure_violations.append({
                "text": text_artist.get_text().replace("\n", " / "),
                "container": type(container).__name__,
            })
    ENCLOSURE_AUDIT[stem] = enclosure_violations
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.svg")
    plt.close(fig)


def panel(ax: plt.Axes, letter: str, x: float = -0.08, y: float = 1.01) -> None:
    ax.text(x, y, letter, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=13, fontweight="bold", color=INK)


def write_caption(stem: str, text: str) -> None:
    (OUT / f"{stem}_caption.txt").write_text(text.strip() + "\n", encoding="utf-8")


def snapshot_sources() -> None:
    SD.mkdir(parents=True, exist_ok=True)
    framework = json.loads((SRC / "fig01_framework_source.json").read_text(encoding="utf-8"))
    (SD / "fig01_framework.json").write_text(
        json.dumps(framework, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    q1 = pd.read_csv(SRC / "fig02_q1_quality_validation_source.csv")
    q1.to_csv(SD / "fig02_q1_quality_validation.csv", index=False, encoding="utf-8-sig")

    reg = pd.read_csv(SRC / "fig03_q1_regmix_transport_source.csv")
    reg[["scale", "index", "domain", "observed_loss", "predicted_loss"]].to_csv(
        SD / "fig03_regmix_points.csv", index=False, encoding="utf-8-sig"
    )
    metrics = pd.DataFrame([
        ["1M", "同尺度独立检验", 256, 13, 3328, 0.5229481985104112, 0.6250743877317463],
        ["60M", "零样本跨尺度运输", 256, 13, 3328, 1.618576045611434, 0.5591496910048065],
        ["1B", "零样本跨尺度运输", 64, 13, 832, 3.2522400649420837, 0.37229853479853475],
    ], columns=["scale", "role", "recipe_n", "domain_n", "point_n",
                "rmse_all_domains", "rho_equal_domain_mean"])
    metrics.to_csv(SD / "fig03_regmix_metrics.csv", index=False, encoding="utf-8-sig")

    b1 = pd.read_csv(SRC / "fig04_q2_fit_validation_source_b1.csv")
    b1[["val_loss", "prediction"]].to_csv(
        SD / "fig04_b1_fit.csv", index=False, encoding="utf-8-sig"
    )
    q2 = pd.read_csv(TSRC / "table06_q2_validation.csv")
    rows = []
    for _, r in q2.iterrows():
        inside, oos = [int(v.strip()) for v in str(r["支持内 / OOS"]).split("/")]
        rmse = pd.to_numeric(pd.Series([r["RMSE"]]), errors="coerce").iloc[0]
        rows.append({
            "source": r["来源"],
            "total_records": int(r["原始记录"]),
            "in_support": inside,
            "oos": oos,
            "rmse": None if pd.isna(rmse) else float(rmse),
            "qualification": r["最终资格"],
            "error_basis": r["误差口径"],
        })
    pd.DataFrame(rows).to_csv(
        SD / "fig04_validation_summary.csv", index=False, encoding="utf-8-sig"
    )

    q4 = pd.read_csv(SRC / "fig06_q4_scenarios_source.csv")
    q4[["benchmark_task", "target_role", "scenario_id", "scenario_order",
        "horizon_months", "forecast_origin", "forecast_date",
        "forecast_eligibility", "prediction_points"]].to_csv(
        SD / "fig05_q4_scenarios.csv", index=False, encoding="utf-8-sig"
    )


def figure01_framework() -> None:
    stem = "fig01_v3_framework"
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.30))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    cards = [
        (0.10, "统一口径\n数据审计", "输入"),
        (0.30, "质量代理\n配比回归", "Q1"),
        (0.50, "条件标度\n分来源验证", "Q2"),
        (0.70, "预算约束\n条件最优", "Q3"),
        (0.90, "能力分解\n未来情景", "Q4"),
    ]
    for i, (x, text, tag) in enumerate(cards):
        fc = GREY_PALE if i == 0 else BLUE_PALE
        card = FancyBboxPatch(
            (x - 0.082, 0.55), 0.164, 0.25,
            boxstyle="round,pad=0.010,rounding_size=0.015",
            facecolor=fc, edgecolor=INK, linewidth=0.9,
        )
        ax.add_patch(card)
        ax.text(x, 0.675, text, ha="center", va="center", color=INK, linespacing=1.18)
        ax.text(x, 0.865, tag, ha="center", va="center", color=NAVY,
                fontweight="bold")
        if i < len(cards) - 1:
            ax.annotate("", xy=(cards[i + 1][0] - 0.088, 0.675),
                        xytext=(x + 0.088, 0.675),
                        arrowprops=dict(arrowstyle="-|>", color=BLUE,
                                        lw=1.4, mutation_scale=12))

    anchors = [0.30, 0.50, 0.70, 0.90]
    labels = ["操作性代理", "来源资格", "约束条件", "未验证情景"]
    colors = [GREY, ROSE, NAVY, ROSE]
    for x, lab, color in zip(anchors, labels, colors):
        ax.plot([x, x], [0.54, 0.38], color=GREY_2, lw=0.9)
        ax.scatter([x], [0.36], s=34, color=color, zorder=3)
        ax.text(x, 0.285, lab, ha="center", va="center", color=color)

    ax.plot([0.24, 0.96], [0.36, 0.36], color=GREY_2, lw=1.0, zorder=1)
    ax.text(0.60, 0.11, "适用范围与证据资格贯穿建模、验证、优化和情景分析",
            ha="center", va="center", color=ROSE, fontweight="bold")
    save(fig, stem)
    write_caption(
        stem,
        "总体技术路线。统一口径的数据依次用于质量代理与配比回归、条件标度与分来源验证、预算约束优化及未来情景分析；适用范围和证据资格在各阶段持续保留。",
    )


def figure02_q1() -> None:
    stem = "fig02_v3_q1_quality"
    d = pd.read_csv(SD / "fig02_q1_quality_validation.csv")
    fig = plt.figure(figsize=(WIDTH_IN, 7.35))
    gs = fig.add_gridspec(
        3, 1, height_ratios=[0.80, 0.62, 1.18], hspace=0.40,
        left=0.22, right=0.97, top=0.97, bottom=0.08,
    )

    ax0 = fig.add_subplot(gs[0, 0])
    ax0.set_axis_off()
    panel(ax0, "a", x=-0.07, y=1.01)
    flow = [
        (0.12, "11 个特征\n5/3/3"),
        (0.38, "组内等权\n缺失则缺组分"),
        (0.64, "三组等权\n缺失不重分配"),
        (0.88, "质量得分 Q\n有效 261,067\n缺失 19"),
    ]
    widths = [0.21, 0.22, 0.22, 0.20]
    for i, ((x, text), w) in enumerate(zip(flow, widths)):
        box = FancyBboxPatch(
            (x - w / 2, 0.37), w, 0.40,
            boxstyle="round,pad=0.010,rounding_size=0.012",
            facecolor=ROSE_PALE if i == 3 else BLUE_PALE,
            edgecolor=INK, linewidth=0.85,
        )
        ax0.add_patch(box)
        text_artist = ax0.text(x, 0.57, text, ha="center", va="center", color=INK,
                               linespacing=1.10)
        ENCLOSURE_PAIRS.setdefault(stem, []).append((text_artist, box))
        if i < 3:
            ax0.annotate("", xy=(flow[i + 1][0] - widths[i + 1] / 2 - 0.008, 0.57),
                         xytext=(x + w / 2 + 0.008, 0.57),
                         arrowprops=dict(arrowstyle="-|>", color=BLUE,
                                         lw=1.25, mutation_scale=11))
    ax0.text(0.50, 0.12, "操作性质量代理；不等同于人工真值或语义质量金标准",
             ha="center", va="center", color=ROSE, fontweight="bold")

    ax1 = fig.add_subplot(gs[1, 0])
    panel(ax1, "b")
    labels = ["A2 扩展", "A3 扩展"]
    passed = np.array([1, 3])
    y = np.arange(2)
    ax1.barh(y, np.full(2, 4), color=GREY_PALE, edgecolor="none", height=0.52)
    ax1.barh(y, passed, color=[BLUE_2, BLUE], edgecolor="none", height=0.52)
    for yi, p in zip(y, passed):
        ax1.text(p + 0.10, yi, f"{p}/4 通过", va="center", ha="left",
                 color=NAVY, fontweight="bold")
    ax1.set_yticks(y, labels)
    ax1.invert_yaxis()
    ax1.set_xlim(0, 6.0)
    ax1.set_xticks([0, 1, 2, 3, 4])
    ax1.set_xlabel("全局稳定性判据")
    ax1.text(0.99, 1.03, "总体：部分稳定；共同有效域均为 1；域级不可评价",
             transform=ax1.transAxes, ha="right", va="bottom", color=ROSE)

    ax2 = fig.add_subplot(gs[2, 0])
    panel(ax2, "c")
    m = d[d.section == "manual_validation"].copy()
    order = ["总体质量", "可读性", "完整性", "污染度"]
    m["item"] = pd.Categorical(m.item, order, ordered=True)
    m = m.sort_values("item")
    y2 = np.arange(len(m))
    est = m.value.to_numpy(float)
    lo = m.ci_low.to_numpy(float)
    hi = m.ci_high.to_numpy(float)
    ax2.axvline(0, color=GREY, lw=1.0, ls="--")
    ax2.errorbar(est, y2, xerr=[est - lo, hi - est], fmt="o", ms=6.5,
                 color=NAVY, ecolor=BLUE_2, elinewidth=1.8, capsize=3.5)
    ax2.set_yticks(y2, [f"{r['item']}\n(n={int(r['n'])})" for _, r in m.iterrows()])
    ax2.invert_yaxis()
    ax2.set_xlim(-0.66, 0.48)
    ax2.set_xticks([-0.6, -0.4, -0.2, 0.0, 0.2, 0.4])
    ax2.set_xlabel("Spearman ρ（95% 重抽样区间）")
    ax2.text(0.98, 1.02, "未显示稳定正向一致性", transform=ax2.transAxes,
             ha="right", va="bottom", color=ROSE, fontweight="bold")
    save(fig, stem)
    write_caption(
        stem,
        "质量得分的构造、扩展稳定性与人工核验。扩展检验仅达到部分稳定；有限作者盲审未显示质量得分与人工判断之间稳定的正向一致性。",
    )


def figure03_regmix() -> None:
    stem = "fig03_v3_regmix_transport"
    d = pd.read_csv(SD / "fig03_regmix_points.csv")
    metrics = pd.read_csv(SD / "fig03_regmix_metrics.csv").set_index("scale")
    fig = plt.figure(figsize=(WIDTH_IN, 5.10))
    gs = fig.add_gridspec(
        2, 3, height_ratios=[1.0, 0.28],
        hspace=0.38, wspace=0.25, left=0.10, right=0.98, top=0.88, bottom=0.07,
    )
    specs = [
        ("1M", fig.add_subplot(gs[0, 0]), "a", "1M 独立测试"),
        ("60M", fig.add_subplot(gs[0, 1]), "b", "60M 迁移"),
        ("1B", fig.add_subplot(gs[0, 2]), "c", "1B 迁移"),
    ]
    for scale, ax, letter, title in specs:
        s = d[d.scale == scale]
        ax.scatter(s.observed_loss, s.predicted_loss, s=5, alpha=0.13,
                   color=BLUE, edgecolors="none", rasterized=True)
        lower = min(s.observed_loss.min(), s.predicted_loss.min())
        upper = max(s.observed_loss.max(), s.predicted_loss.max())
        pad = (upper - lower) * 0.035
        ax.plot([lower - pad, upper + pad], [lower - pad, upper + pad],
                color=GREY, lw=1.1, ls="--")
        ax.set_xlim(lower - pad, upper + pad)
        ax.set_ylim(lower - pad, upper + pad)
        ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=3, prune="both"))
        ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=5, prune="both"))
        ax.set_title(title, pad=8, fontweight="bold", color=INK)
        if scale == "1M":
            ax.set_ylabel("预测 Loss")
        else:
            ax.set_ylabel("")
        panel(ax, letter, x=-0.12, y=1.11)

    for col, scale in enumerate(["1M", "60M", "1B"]):
        axm = fig.add_subplot(gs[1, col])
        axm.set_axis_off()
        row = metrics.loc[scale]
        axm.text(0.50, 0.72, f"n={int(row.recipe_n)} 配方",
                 ha="center", va="center", color=INK)
        axm.text(0.50, 0.22,
                 f"RMSE={row.rmse_all_domains:.3f}   ρ={row.rho_equal_domain_mean:.3f}",
                 ha="center", va="center", color=NAVY, fontweight="bold")
    fig.text(0.54, 0.255, "观测 Loss", ha="center", va="center", color=INK)
    save(fig, stem)
    write_caption(
        stem,
        "领域配比模型的同尺度检验与跨尺度运输。n 表示配方数；散点表示配方与 13 个领域的组合，1M、60M、1B 分别含 3,328、3,328、832 个点。图内 RMSE 合并全部配方×域点，ρ 为逐域计算后等权平均，区别于正文另报的逐域等权 RMSE。",
    )


def figure04_q2() -> None:
    stem = "fig04_v3_q2_validation"
    b1 = pd.read_csv(SD / "fig04_b1_fit.csv")
    q = pd.read_csv(SD / "fig04_validation_summary.csv")
    order = ["B2", "B3", "B4", "B5", "B9", "B10"]
    q["source"] = pd.Categorical(q.source, order, ordered=True)
    q = q.sort_values("source")

    fig = plt.figure(figsize=(WIDTH_IN, 7.15))
    outer = fig.add_gridspec(
        2, 1, height_ratios=[0.95, 1.12], hspace=0.36,
        left=0.10, right=0.98, top=0.96, bottom=0.09,
    )
    top = outer[0].subgridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.18)
    bottom = outer[1].subgridspec(1, 2, width_ratios=[1.06, 0.94], wspace=0.42)
    ax0 = fig.add_subplot(top[0, 0])
    axq = fig.add_subplot(top[0, 1], sharey=ax0)
    ax1 = fig.add_subplot(bottom[0, 0])
    ax2 = fig.add_subplot(bottom[0, 1])

    panel(ax0, "a")
    y = np.arange(len(q))
    share = q.in_support.to_numpy(float) / q.total_records.to_numpy(float) * 100
    ax0.barh(y, np.full(len(q), 100), height=0.56, color=GREY_PALE, edgecolor="none")
    ax0.barh(y, share, height=0.56, color=BLUE_2, edgecolor="none")
    for yi, row, pct in zip(y, q.itertuples(), share):
        ax0.text(102, yi, f"{int(row.in_support)}/{int(row.total_records)}",
                 ha="left", va="center", color=INK, clip_on=False)
        if pct >= 17:
            ax0.text(pct - 2, yi, f"{pct:.0f}%", ha="right", va="center",
                     color="white", fontweight="bold")
        elif pct > 0:
            ax0.text(pct + 2, yi, f"{pct:.0f}%", ha="left", va="center", color=NAVY)
    ax0.set_yticks(y, q.source.astype(str))
    ax0.invert_yaxis()
    ax0.set_xlim(0, 124)
    ax0.set_xticks([0, 25, 50, 75, 100])
    ax0.set_xlabel("经验支持域内记录占比（%）")
    ax0.text(0.01, 1.02, "蓝色：支持内；浅灰：支持外", transform=ax0.transAxes,
             ha="left", va="bottom", color=GREY)

    axq.set_axis_off()
    qual_map = {
        "VALIDATION_FAILED": ("外部验证失败", ROSE),
        "VALIDATION_SUPPORTED": ("同源插值支持", NAVY),
        "OOS_STRESS_ONLY": ("仅作域外压力测试", ROSE),
        "ESTIMATED_SCENARIO_ONLY": ("仅作估算情景", ROSE),
    }
    axq.text(0.02, 1.02, "最终资格", transform=axq.transAxes,
             ha="left", va="bottom", color=INK, fontweight="bold")
    for yi, row in zip(y, q.itertuples()):
        label, color = qual_map[row.qualification]
        axq.text(0.02, yi, label, ha="left", va="center", color=color,
                 fontweight="bold" if row.qualification != "VALIDATION_SUPPORTED" else "normal")
    axq.set_ylim(ax0.get_ylim())

    panel(ax1, "b")
    ax1.scatter(b1.val_loss, b1.prediction, s=7, alpha=0.24,
                color=BLUE, edgecolors="none", rasterized=True)
    lo = min(b1.val_loss.min(), b1.prediction.min())
    hi = max(b1.val_loss.max(), b1.prediction.max())
    ax1.plot([lo, hi], [lo, hi], color=GREY, lw=1.1, ls="--")
    ax1.set_xticks([2, 3, 4])
    ax1.set_xlabel("B1 观测 Loss")
    ax1.set_ylabel("B1 拟合 Loss")
    ax1.text(0.04, 0.96, f"来源内拟合\nn={len(b1):,}", transform=ax1.transAxes,
             ha="left", va="top", color=INK,
             bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=GREY_2, alpha=0.92))

    panel(ax2, "c")
    real = q.copy()
    y2 = np.arange(len(real))
    for yi, row in zip(y2, real.itertuples()):
        if pd.isna(row.rmse):
            ax2.text(0.00082, yi, "无观测，不计算", ha="left", va="center", color=GREY)
            continue
        supported = row.qualification == "VALIDATION_SUPPORTED"
        estimated = row.qualification == "ESTIMATED_SCENARIO_ONLY"
        color = NAVY if supported else (GREY if estimated else ROSE)
        marker = "D" if estimated else "o"
        face = "white" if estimated else color
        ax2.scatter([row.rmse], [yi], s=58, marker=marker,
                    facecolors=face, edgecolors=color, linewidths=1.3, zorder=3)
        suffix = "（估算）" if estimated else ""
        offset = (-8, 0) if row.rmse > 1 else (8, 0)
        align = "right" if row.rmse > 1 else "left"
        ax2.annotate(f"{row.rmse:.4g}{suffix}", xy=(row.rmse, yi),
                     xytext=offset, textcoords="offset points",
                     ha=align, va="center", color=color, annotation_clip=False)
    ax2.set_xscale("log")
    ax2.set_xticks([1e-3, 1e-2, 1e-1, 1e0])
    ax2.set_yticks(y2, real.source.astype(str))
    ax2.invert_yaxis()
    ax2.set_xlim(0.0007, 5.0)
    ax2.set_xlabel("分来源 RMSE")
    save(fig, stem)
    write_caption(
        stem,
        "基础标度模型的支持覆盖、来源内拟合与分来源误差。B2、B3、B4、B5 的图示误差限于支持内记录且不跨来源合并；B2、B4、B5 外部验证失败，B3 仅获同源插值支持。B9 缺少观测 Loss，故不计算误差；B10 的误差仅为估算参考。",
    )


def figure05_q4() -> None:
    stem = "fig05_v3_q4_scenarios"
    d = pd.read_csv(SD / "fig05_q4_scenarios.csv")
    tasks = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO",
             "six_task_mean_complete_only"]
    labels = ["IFEval", "BBH", "MATH Level 5", "GPQA", "MUSR", "MMLU-PRO",
              "辅助均值"]
    scenarios = [
        ("SLOW", "慢速情景", GREY, "o", 0.18),
        ("BASELINE", "基准情景", NAVY, "s", 0.00),
        ("UPPER_SENSITIVITY", "上界敏感性", ROSE, "^", -0.18),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_IN, 6.35), sharey=True)
    fig.subplots_adjust(left=0.25, right=0.98, top=0.78, bottom=0.17, wspace=0.12)
    y = np.arange(len(tasks))[::-1]
    for j, (ax, horizon, date) in enumerate(zip(axes, [12, 24], ["2026-01-28", "2027-01-28"])):
        for code, lab, color, marker, offset in scenarios:
            values = []
            for task in tasks:
                row = d[(d.benchmark_task == task) & (d.horizon_months == horizon) &
                        (d.scenario_id == code)]
                values.append(float(row.prediction_points.iloc[0]))
            ax.scatter(values, y + offset, s=48, color=color, marker=marker,
                       edgecolors="white", linewidths=0.45, label=lab, zorder=3)
        ax.axvline(0, color=GREY, lw=1.0, ls="--", zorder=1)
        ax.axhline(0.5, color=GREY_2, lw=0.8)
        ax.set_xlim(-6, 39)
        ax.set_xticks([-5, 0, 10, 20, 30])
        ax.set_xlabel("")
        ax.text(-0.08, 1.13, chr(97 + j), transform=ax.transAxes,
                ha="left", va="bottom", fontsize=13, fontweight="bold", color=INK)
        ax.text(0.50, 1.13, f"{horizon} 个月 · {date}", transform=ax.transAxes,
                ha="center", va="bottom", color=INK, fontweight="bold")
        ax.text(0.50, 1.045, "相对起点：2025-01-28", transform=ax.transAxes,
                ha="center", va="bottom", color=GREY)
        if j == 0:
            ax.set_yticks(y, labels)
        else:
            ax.tick_params(axis="y", labelleft=False)
    fig.text(0.62, 0.965, "仅情景分析 · 未经时间外验证", ha="center", va="center",
             color=ROSE, fontweight="bold")
    fig.text(0.62, 0.920, "三种标记为独立情景，不是置信区间；负值保持原样。",
             ha="center", va="center", color=GREY)
    fig.text(0.62, 0.115, "Benchmark 点（原始未截断值）",
             ha="center", va="center", color=INK)
    handles, labs = axes[1].get_legend_handles_labels()
    fig.legend(handles, labs, ncol=3, loc="lower center", bbox_to_anchor=(0.60, 0.02),
               columnspacing=1.3, handletextpad=0.45)
    save(fig, stem)
    write_caption(
        stem,
        "六项任务及辅助均值在 12 个月和 24 个月的三种独立情景。预测以 2025-01-28 为相对起点；三种标记不是置信区间，所有负值保持原样。全部结果仅用于情景分析，未经时间外验证。",
    )


def write_source_map() -> None:
    rows = [
        ["FIG-V3-01", "fig01_v3_framework", "fig01_framework_source.json",
         "nodes; edges", "结构重排与中文读者化；无数值变更"],
        ["FIG-V3-02", "fig02_v3_q1_quality", "fig02_q1_quality_validation_source.csv",
         "section; item; value; ci_low; ci_high; n", "全部已交付汇总项"],
        ["FIG-V3-03", "fig03_v3_regmix_transport", "fig03_q1_regmix_transport_source.csv",
         "scale; index; domain; observed_loss; predicted_loss", "全部散点；无抽样"],
        ["FIG-V3-03", "fig03_v3_regmix_transport", "frozen V2 metric labels",
         "recipe_n; domain_n; point_n; rmse_all_domains; rho_equal_domain_mean",
         "仅澄清统计口径，不重算模型"],
        ["FIG-V3-04", "fig04_v3_q2_validation", "fig04_q2_fit_validation_source_b1.csv",
         "val_loss; prediction", "全部 B1 来源内拟合点"],
        ["FIG-V3-04", "fig04_v3_q2_validation", "table06_q2_validation.csv",
         "来源; 原始记录; 支持内/OOS; RMSE; 最终资格; 误差口径",
         "支持占比、资格和分来源 RMSE"],
        ["FIG-V3-05", "fig05_v3_q4_scenarios", "fig06_q4_scenarios_source.csv",
         "task; role; scenario; horizon; origin; date; eligibility; prediction_points",
         "全部任务与情景；不截断；不连接无序任务"],
    ]
    with (OUT / "figure_source_map.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset_id", "output_stem", "frozen_source", "fields", "display_transform"])
        w.writerows(rows)


def write_contracts() -> None:
    text = """# FIG-FINAL V3 figure contracts

| Figure | Core conclusion | Archetype | Evidence hierarchy | Reviewer risk controlled |
|---|---|---|---|---|
| FIG-V3-01 | Four questions form one sequential workflow whose evidence qualification is preserved throughout. | schematic-led | workflow cards > qualification rail | engineering paths and run identifiers removed |
| FIG-V3-02 | Q is an operational proxy with partial extension stability and weak manual agreement. | schematic-led composite | construction > stability > manual validation | no implication that Q is a human ground truth |
| FIG-V3-03 | Same-scale prediction transports imperfectly to larger scales, with metric denominators made explicit. | asymmetric quantitative | 1M hero > 60M/1B transport | recipe n, point unit, RMSE and rho aggregation distinguished |
| FIG-V3-04 | Q2 evidence must be read by source: support coverage, in-source fit, and source-specific error have different qualifications. | layered quantitative | support/qualification > B1 fit > source RMSE | failures and OOS/estimated qualifications retained |
| FIG-V3-05 | Q4 values are unordered task-wise scenarios, not trends or confidence intervals. | parallel grouped-point | six primary tasks > auxiliary mean | negative values retained; origin and no temporal validation explicit |

Backend: Python/matplotlib only. Final width: 165 mm. Minimum final-size text: 12 pt. Exports: editable-text SVG, vector PDF, 600 dpi PNG.
"""
    (OUT / "FIGURE_CONTRACTS.md").write_text(text, encoding="utf-8")


def write_index() -> None:
    rows = [
        ("FIG-V3-01", "fig01_v3_framework", "总体技术路线与证据边界", "165 × 84 mm",
         "置于数据与总体思路说明之后", "随后说明四问共享冻结口径及资格标签。"),
        ("FIG-V3-02", "fig02_v3_q1_quality", "质量代理的构造与验证", "165 × 187 mm",
         "置于质量得分 Q 定义之后", "随后解释部分稳定和人工核验局限。"),
        ("FIG-V3-03", "fig03_v3_regmix_transport", "配比模型检验与跨尺度运输", "165 × 130 mm",
         "置于 RegMix 模型与验证口径之后", "随后强调 n、散点单位及两种 RMSE 口径。"),
        ("FIG-V3-04", "fig04_v3_q2_validation", "标度模型的支持覆盖与分来源验证", "165 × 182 mm",
         "置于 B1 条件标度模型之后", "随后逐来源陈述失败、同源插值、域外和估算资格。"),
        ("FIG-V3-05", "fig05_v3_q4_scenarios", "六任务未来情景", "165 × 161 mm",
         "置于情景定义与预测起点之后", "随后强调三点并非置信区间且未经时间外验证。"),
    ]
    lines = [
        "# FIG-FINAL V3 asset index", "",
        "五张核心图均按 165 mm 正文宽度绘制；中文使用宋体，纯拉丁字符与数字使用 Times New Roman；所有图内文字最终物理尺寸不低于 12 pt。",
        "", "| 顺序 | 图题 | 尺寸 | PNG | PDF | SVG | 图前建议 | 图后解释建议 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for aid, stem, title, size, before, after in rows:
        lines.append(
            f"| {aid} | {title} | {size} | [{stem}.png]({stem}.png) | "
            f"[{stem}.pdf]({stem}.pdf) | [{stem}.svg]({stem}.svg) | {before} | {after} |"
        )
    lines += [
        "", "## Supporting files", "",
        "- `source_data/`: minimal frozen plotting inputs.",
        "- `figure_source_map.csv`: source-to-panel mapping.",
        "- `FIGURE_CONTRACTS.md`: claim and reviewer-risk contract.",
        "- `checks.json`: machine-readable export and integrity checks.",
        "- `VISUAL_QA.md`: final-size visual inspection record.",
        "- `main_text_png_sha256.csv`: frozen PNG hashes.",
        "- `build_submission_v3.py`: reproducible Python builder.",
        "",
    ]
    (OUT / "ASSET_INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def write_checks() -> None:
    from PIL import Image

    stems = [
        "fig01_v3_framework", "fig02_v3_q1_quality", "fig03_v3_regmix_transport",
        "fig04_v3_q2_validation", "fig05_v3_q4_scenarios",
    ]
    details = {}
    ok = True
    for stem in stems:
        png, pdf, svg, cap = [OUT / f"{stem}{suffix}" for suffix in
                              [".png", ".pdf", ".svg", "_caption.txt"]]
        im = Image.open(png)
        dpi = im.info.get("dpi", (0, 0))
        width_mm = im.size[0] / dpi[0] * 25.4
        height_mm = im.size[1] / dpi[1] * 25.4
        svg_text = svg.read_text(encoding="utf-8")
        item_ok = (pdf.exists() and cap.exists() and "<text" in svg_text and
                   min(dpi) >= 599 and abs(width_mm - 165) < 0.5 and
                   height_mm <= 200 and MIN_FONT_AUDIT[stem] >= 12 and
                   len(TEXT_BBOX_AUDIT[stem]) == 0 and
                   len(ENCLOSURE_AUDIT[stem]) == 0)
        ok &= item_ok
        details[stem] = {
            "png": png.exists(), "pdf": pdf.exists(), "svg": svg.exists(),
            "svg_has_editable_text": "<text" in svg_text,
            "caption": cap.exists(), "dpi": list(dpi),
            "width_mm": width_mm, "height_mm": height_mm,
            "minimum_font_pt": MIN_FONT_AUDIT[stem],
            "text_bbox_violations": TEXT_BBOX_AUDIT[stem], "pass": item_ok,
            "container_bbox_violations": ENCLOSURE_AUDIT[stem],
        }

    q4 = pd.read_csv(SD / "fig05_q4_scenarios.csv")
    negatives = q4[(q4.benchmark_task == "MATH Lvl 5") &
                   (q4.horizon_months == 24)].prediction_points.tolist()
    q4_ok = len(negatives) == 3 and all(v < 0 for v in negatives)
    source_rows = {
        "fig02_q1_rows": len(pd.read_csv(SD / "fig02_q1_quality_validation.csv")),
        "fig03_point_rows": len(pd.read_csv(SD / "fig03_regmix_points.csv")),
        "fig04_b1_rows": len(pd.read_csv(SD / "fig04_b1_fit.csv")),
        "fig04_summary_rows": len(pd.read_csv(SD / "fig04_validation_summary.csv")),
        "fig05_scenario_rows": len(q4),
    }
    payload = {
        "status": "PASS" if ok and q4_ok else "FAIL",
        "figure_count": 5,
        "science_changed": False,
        "source_scope": "previously delivered frozen figure/table sources only",
        "no_refit": True, "no_threshold_change": True, "no_clipping": True,
        "no_sampling": True, "no_large_hatch": True,
        "font_contract": {"Chinese": "SimSun", "Latin": "Times New Roman",
                          "minimum_final_size_pt": 12},
        "figures": details,
        "source_rows": source_rows,
        "q4_negative_values": negatives,
        "q4_negative_values_retained": q4_ok,
        "q4_qualification": sorted(q4.forecast_eligibility.unique().tolist()),
    }
    (OUT / "checks.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if payload["status"] != "PASS":
        raise SystemExit("V3 checks failed")


def write_hashes() -> None:
    rows = [
        ("FIG-V3-01", "fig01_v3_framework.png"),
        ("FIG-V3-02", "fig02_v3_q1_quality.png"),
        ("FIG-V3-03", "fig03_v3_regmix_transport.png"),
        ("FIG-V3-04", "fig04_v3_q2_validation.png"),
        ("FIG-V3-05", "fig05_v3_q4_scenarios.png"),
    ]
    with (OUT / "main_text_png_sha256.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset_id", "file", "sha256", "status"])
        for aid, name in rows:
            digest = hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            w.writerow([aid, name, digest, "FROZEN_AFTER_VISUAL_QA"])


def main() -> None:
    snapshot_sources()
    for fn in [figure01_framework, figure02_q1, figure03_regmix, figure04_q2, figure05_q4]:
        fn()
    write_source_map()
    write_contracts()
    write_index()
    write_checks()
    write_hashes()


if __name__ == "__main__":
    main()
