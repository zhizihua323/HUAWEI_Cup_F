"""Build the frozen Q3 budget/context figure for the submission manuscript.

AI-assisted presentation code: OpenAI Codex (GPT-5.6 Sol High), 2026-09-26.
Scientific inputs are read only from the accepted TASK-T07 outputs.  The script
filters the pre-registered S00 grid; it performs no fitting, interpolation, or
optimization.

Figure contract
---------------
Core conclusion: the analytic budget reduction yields conditional optima whose
active support boundary changes with budget and context length.
Archetype: schematic-led composite.
Panel a: three budget branches and the stationary-point/boundary/KKT workflow.
Panel b: all 15 frozen budget x H states, annotated with frozen predicted Loss.
Reviewer risk: the matrix is a discrete grid, not a continuous phase diagram.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SRC = ROOT / "diagnostics" / "TASK-T07" / "20260925T113744+08" / "context_sensitivity.csv"
SOURCE_OUT = OUT / "source_data" / "fig05_v4_q3_budget_context.csv"

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    }
)


def add_box(ax, xy, width, height, text, face, edge="#52606d", size=7.4, weight="normal"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.9,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=size, weight=weight, linespacing=1.25)
    return box


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=9, linewidth=0.9, color="#64748b"))


data = pd.read_csv(SRC)
budgets = [1e18, 1e20, 1e22]
hs = [2048, 4096, 8192, 32768, 131072]
use = data[
    (data["scenario_id"] == "S00_NULL_M0_B1")
    & data["budget_flops"].isin(budgets)
    & data["H"].isin(hs)
].copy()
use = use.sort_values(["budget_flops", "H"])
assert len(use) == 15
assert use.groupby(["budget_flops", "H"]).size().eq(1).all()

def state(row):
    active = str(row["active_constraints"])
    if "N_LOWER" in active:
        return "N下界"
    if "D_UPPER" in active:
        return "D上界"
    return "内点"

use["display_state"] = use.apply(state, axis=1)
SOURCE_OUT.parent.mkdir(parents=True, exist_ok=True)
use[
    [
        "scenario_id",
        "budget_flops",
        "H",
        "N_B",
        "D_B",
        "predicted_loss",
        "active_constraints",
        "support_status",
        "display_state",
    ]
].to_csv(SOURCE_OUT, index=False, encoding="utf-8-sig")

state_code = {"内点": 0, "N下界": 1, "D上界": 2}
matrix = np.empty((3, 5), dtype=int)
losses = np.empty((3, 5), dtype=float)
for i, budget in enumerate(budgets):
    for j, h in enumerate(hs):
        row = use[(use["budget_flops"] == budget) & (use["H"] == h)].iloc[0]
        matrix[i, j] = state_code[row["display_state"]]
        losses[i, j] = row["predicted_loss"]

fig = plt.figure(figsize=(7.15, 4.35), constrained_layout=False)
gs = fig.add_gridspec(1, 2, width_ratios=[0.92, 1.48], wspace=0.26, left=0.035, right=0.985, top=0.91, bottom=0.15)

# a | analytic workflow
ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.text(-0.03, 1.04, "a", transform=ax.transAxes, fontsize=10, weight="bold", va="top")
ax.text(0.5, 1.02, "预算分支与求解闭环", ha="center", va="bottom", fontsize=9.2, weight="bold")
add_box(ax, (0.18, 0.86), 0.64, 0.09, r"计算 $K=C_{max}/[(6+\eta H)10^{18}]$", "#eef3f7", weight="bold")
add_box(ax, (0.01, 0.68), 0.28, 0.10, r"$K<N_{min}D_{min}$" + "\n不可行", "#f2f4f5")
add_box(ax, (0.36, 0.68), 0.28, 0.10, "中间预算\n预算约束活跃", "#e7f0f7")
add_box(ax, (0.71, 0.68), 0.28, 0.10, r"$K\geq N_{max}D_{max}$" + "\n双上界", "#f2f4f5")
arrow(ax, (0.50, 0.86), (0.15, 0.78)); arrow(ax, (0.50, 0.86), (0.50, 0.78)); arrow(ax, (0.50, 0.86), (0.85, 0.78))
add_box(ax, (0.30, 0.49), 0.40, 0.10, r"一维约化：$D_B=K/N_B$", "#d8e8f3", weight="bold")
arrow(ax, (0.50, 0.68), (0.50, 0.59))
add_box(ax, (0.30, 0.31), 0.40, 0.10, "解析驻点\n与合法端点比较", "#f7ead1")
arrow(ax, (0.50, 0.49), (0.50, 0.41))
add_box(ax, (0.30, 0.13), 0.40, 0.10, "KKT与预算残差复核\n输出条件最优配置", "#e5efe6", weight="bold")
arrow(ax, (0.50, 0.31), (0.50, 0.23))
ax.text(0.5, 0.04, "主结果采用冻结 M0_B1；Q不优化，p固定", ha="center", va="center", fontsize=7, color="#4b5563")

# b | discrete state matrix
ax = fig.add_subplot(gs[0, 1])
ax.text(-0.08, 1.04, "b", transform=ax.transAxes, fontsize=10, weight="bold", va="top")
cmap = ListedColormap(["#dcebf4", "#f3ddaa", "#d7dfd2"])
ax.imshow(matrix, cmap=cmap, vmin=-0.5, vmax=2.5, aspect="auto", interpolation="nearest")
ax.set_xticks(range(5), ["2,048", "4,096", "8,192", "32,768", "131,072"])
ax.set_yticks(range(3), [r"$10^{18}$", r"$10^{20}$", r"$10^{22}$"])
ax.set_xlabel("上下文长度 H / token", labelpad=6)
ax.set_ylabel("算力预算 / FLOPs", labelpad=6)
ax.set_title("冻结15点的活跃状态与预测Loss", fontsize=9.2, weight="bold", pad=10)
ax.set_xticks(np.arange(-0.5, 5, 1), minor=True)
ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.8)
ax.tick_params(which="minor", bottom=False, left=False)
for i in range(3):
    for j in range(5):
        label = ["内点", "N下界", "D上界"][matrix[i, j]]
        ax.text(j, i - 0.08, label, ha="center", va="center", fontsize=7.4, weight="bold", color="#203040")
        ax.text(j, i + 0.20, f"L={losses[i, j]:.3f}", ha="center", va="center", fontsize=6.8, color="#425466")
ax.axvline(2.5, color="#b45309", linestyle=(0, (3, 2)), linewidth=1.0)
ax.text(2.55, -0.38, "Hcrit=30,000", fontsize=6.8, color="#92400e", ha="left", va="center")
legend = [
    Patch(facecolor="#dcebf4", edgecolor="none", label="内点"),
    Patch(facecolor="#f3ddaa", edgecolor="none", label="N下界"),
    Patch(facecolor="#d7dfd2", edgecolor="none", label="D上界"),
]
ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=7, handlelength=1.3, columnspacing=1.4)
ax.text(0.0, -0.34, "注：仅显示预注册离散H点；颜色表示活跃支持边界，数字为冻结Loss。", transform=ax.transAxes, fontsize=6.7, color="#4b5563")

base = OUT / "fig05_v4_q3_budget_context"
fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
plt.close(fig)

(OUT / "fig05_v4_q3_budget_context_caption.txt").write_text(
    "图5 预算问题的一维解析约化与离散上下文敏感性。左图给出三种预算分支及驻点、端点与KKT复核流程；右图展示三档预算与五个预注册上下文长度的15个冻结状态，颜色表示内点、N下界或D上界，单元格数字为预测Loss。虚线标出成本项系数相等的Hcrit=30000；该网格表示约束转移，不是连续相图。\n",
    encoding="utf-8",
)
print({"rows": len(use), "svg": str(base.with_suffix('.svg')), "pdf": str(base.with_suffix('.pdf')), "png": str(base.with_suffix('.png'))})
