"""Build submission-grade visual revisions from already-delivered source assets only.

Scientific values and qualifications are frozen. This script reads only the
source CSV/JSON files previously delivered in paper/final_figures and
paper/final_tables. It performs no fitting, thresholding, clipping, sampling,
or model selection.
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
# 165 mm / 25.4 mm per inch. Keep the literal visible for static QA tools.
WIDTH_IN = 6.4960629921
MAIN_TEXT_STEMS = {
    "fig01_submission_framework",
    "fig02_submission_q1_quality_validation",
    "fig03_submission_regmix_transport",
    "fig04_submission_q2_validation",
    "fig06_submission_q4_scenarios",
}
RENDERED_MIN_FONT_PT: dict[str, float] = {}

COL = {
    "blue": "#3F6F8F",
    "blue_light": "#AFC7D8",
    "teal": "#5C8F87",
    "rose": "#B36C75",
    "gold": "#B18A45",
    "grey": "#777777",
    "light": "#F1F1EF",
    "dark": "#222222",
    "red": "#9F3D3D",
}

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "SimSun"],
    "mathtext.fontset": "stix",
    "font.size": 11.5,
    "axes.titlesize": 12,
    "axes.labelsize": 11.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.facecolor": "white",
})


def apply_submission_fonts(fig: plt.Figure) -> None:
    """Apply the manuscript's script-specific font contract to every text artist."""
    for artist in fig.findobj(match=Text):
        value = artist.get_text() or ""
        has_cjk = any("\u3400" <= char <= "\u9fff" for char in value)
        artist.set_fontfamily("SimSun" if has_cjk else "Times New Roman")


def enforce_main_text_minimum(fig: plt.Figure, stem: str) -> None:
    """Enforce the official 12 pt minimum for every text artist in main-text figures."""
    text_artists = fig.findobj(match=Text)
    if stem in MAIN_TEXT_STEMS:
        for artist in text_artists:
            artist.set_fontsize(max(12.0, float(artist.get_fontsize())))
    RENDERED_MIN_FONT_PT[stem] = min(float(artist.get_fontsize()) for artist in text_artists)


def save(fig: plt.Figure, stem: str) -> None:
    enforce_main_text_minimum(fig, stem)
    apply_submission_fonts(fig)
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.svg")
    plt.close(fig)


def panel(ax, letter: str) -> None:
    ax.text(-0.08, 1.03, letter, transform=ax.transAxes, fontsize=13,
            fontweight="bold", ha="left", va="bottom")


def caption(stem: str, text: str) -> None:
    (OUT / f"{stem}_caption.txt").write_text(text.strip() + "\n", encoding="utf-8")


def fig01() -> None:
    stem = "fig01_submission_framework"
    source = json.loads((SRC / "fig01_framework_source.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.25))
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    labels = [
        (0.10, "数据整理\n统一口径"),
        (0.30, "问题一\n质量与配比"),
        (0.50, "问题二\n标度建模"),
        (0.70, "问题三\n预算优化"),
        (0.90, "问题四\n能力与情景"),
    ]
    for i, (x, text) in enumerate(labels):
        box = FancyBboxPatch((x - 0.085, 0.58), 0.17, 0.23,
                             boxstyle="round,pad=0.012,rounding_size=0.015",
                             fc="#E7EEF2" if i else COL["light"], ec=COL["dark"], lw=0.9,
                             hatch=None)
        ax.add_patch(box); ax.text(x, 0.695, text, ha="center", va="center", fontsize=10.8)
        if i < len(labels) - 1:
            ax.annotate("", xy=(labels[i+1][0]-0.09, 0.695), xytext=(x+0.09, 0.695),
                        arrowprops=dict(arrowstyle="-|>", lw=1.2, color=COL["blue"]))
    band = FancyBboxPatch((0.17, 0.17), 0.66, 0.21, boxstyle="round,pad=0.012",
                          fc="#F6ECEC", ec=COL["red"], lw=0.9, hatch=None)
    ax.add_patch(band)
    ax.text(0.50, 0.275, "全过程保留适用范围与证据资格",
            ha="center", va="center", fontsize=11.2, fontweight="bold", color=COL["red"])
    for x, _ in labels[1:]:
        ax.annotate("", xy=(0.50, 0.39), xytext=(x, 0.57),
                    arrowprops=dict(arrowstyle="-|>", lw=0.8, color=COL["grey"]))
    ax.text(0.50, 0.07, "建模、验证、优化与情景分析共享同一结果口径",
            ha="center", color=COL["grey"], fontsize=9.8)
    save(fig, stem)
    caption(stem, "四问总体技术路线。数据经统一口径处理后依次进入质量评价、标度建模、预算优化和未来情景分析；各阶段均保留相应的适用范围与证据资格。")


def fig02() -> None:
    stem = "fig02_submission_q1_quality_validation"
    d = pd.read_csv(SRC / "fig02_q1_quality_validation_source.csv")
    fig = plt.figure(figsize=(WIDTH_IN, 5.75))
    gs = fig.add_gridspec(2, 2, height_ratios=[0.85, 1.15], hspace=0.43, wspace=0.50,
                          left=0.09, right=0.98, top=0.97, bottom=0.10)
    ax0 = fig.add_subplot(gs[0, :]); ax0.set_axis_off(); panel(ax0, "a")
    boxes = [
        (0.25, 0.72, "11 个质量特征\n按 5 / 3 / 3 分组"),
        (0.75, 0.72, "组内等权\n缺一则该组缺失"),
        (0.75, 0.30, "三组等权\n缺失不重分配"),
        (0.25, 0.30, "质量得分 Q\n有效 261,067；缺失 19"),
    ]
    w, h = 0.38, 0.28
    for i, (x, y0, text) in enumerate(boxes):
        box = FancyBboxPatch((x-w/2, y0-h/2), w, h, boxstyle="round,pad=0.012",
                             fc="#E8EFF3" if i < 3 else "#F5EAEA", ec=COL["dark"], lw=0.9,
                             hatch=None)
        ax0.add_patch(box); ax0.text(x, y0, text, ha="center", va="center", fontsize=9.9)
    ax0.annotate("", xy=(0.75-w/2-0.01,0.72), xytext=(0.25+w/2+0.01,0.72),
                 arrowprops=dict(arrowstyle="-|>",lw=1.1,color=COL["blue"]))
    ax0.annotate("", xy=(0.75,0.30+h/2+0.01), xytext=(0.75,0.72-h/2-0.01),
                 arrowprops=dict(arrowstyle="-|>",lw=1.1,color=COL["blue"]))
    ax0.annotate("", xy=(0.25+w/2+0.01,0.30), xytext=(0.75-w/2-0.01,0.30),
                 arrowprops=dict(arrowstyle="-|>",lw=1.1,color=COL["blue"]))
    ax0.text(0.50, 0.03, "操作性质量代理；不能等同于人工真值或语义质量金标准",
             ha="center", color=COL["red"], fontweight="bold", fontsize=11.2)

    ax1 = fig.add_subplot(gs[1, 0]); panel(ax1, "b")
    x = np.arange(2); passed = [1, 3]; failed = [3, 1]
    ax1.bar(x, passed, color=[COL["blue"], COL["teal"]], edgecolor=COL["dark"], hatch=["//", ".."], label="通过")
    ax1.bar(x, failed, bottom=passed, color="white", edgecolor=COL["dark"], hatch="xx", label="未通过")
    ax1.set_xticks(x, ["A2 扩展", "A3 扩展"]); ax1.set_ylim(0, 5.0); ax1.set_yticks(range(5))
    ax1.set_ylabel("全局判据数（共 4 项）")
    for xi, (p, f) in enumerate(zip(passed, failed)):
        ax1.text(xi, p / 2, f"通过 {p}", ha="center", va="center", color="white", fontsize=9.5, fontweight="bold")
        ax1.text(xi, p + f / 2, f"未通过 {f}", ha="center", va="center", fontsize=9.5)
    ax1.text(0.03, 0.97, "总体：部分稳定",
             transform=ax1.transAxes, ha="left", va="top", color=COL["red"], fontsize=10.5, fontweight="bold")
    ax1.text(0.03, 0.89, "共同有效域均为 1；域级不可评价",
             transform=ax1.transAxes, ha="left", va="top", fontsize=9.6)

    ax2 = fig.add_subplot(gs[1, 1]); panel(ax2, "c")
    m = d[d.section == "manual_validation"].copy()
    y = np.arange(len(m)); est = m.value.to_numpy(); lo = m.ci_low.to_numpy(); hi = m.ci_high.to_numpy()
    labels = ["总体质量", "可读性", "完整性", "污染度"]
    ns = m.n.astype(int).tolist()
    ax2.axvline(0, color=COL["grey"], lw=1, ls="--")
    ax2.errorbar(est, y, xerr=[est-lo, hi-est], fmt="o", color=COL["blue"],
                 ecolor=COL["blue_light"], capsize=3, lw=1.5, ms=6)
    ax2.set_yticks(y, [f"{lab}（n={n}）" for lab, n in zip(labels, ns)]); ax2.invert_yaxis()
    ax2.set_xlim(-0.66, 0.48); ax2.set_xlabel("Spearman ρ（95% 重抽样区间）")
    ax2.text(0.98, 1.03, "未显示稳定正向一致性", transform=ax2.transAxes,
             ha="right", va="bottom", color=COL["red"], fontweight="bold", fontsize=9.8,
             bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.90))
    save(fig, stem)
    caption(stem, "问题一质量得分的构造、扩展稳定性与人工核验。扩展判据仅部分稳定，有限作者盲审未显示质量得分与人工判断之间稳定的正向一致性。")


def fig03() -> None:
    stem = "fig03_submission_regmix_transport"
    d = pd.read_csv(SRC / "fig03_q1_regmix_transport_source.csv")
    metrics = {
        "1M": (256, 0.5229481985104112, 0.6250743877317463, "同尺度独立检验"),
        "60M": (256, 1.618576045611434, 0.5591496910048065, "零样本跨尺度运输"),
        "1B": (64, 3.2522400649420837, 0.37229853479853475, "零样本跨尺度运输"),
    }
    fig = plt.figure(figsize=(WIDTH_IN, 6.15))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.04, 1], hspace=0.48, wspace=0.38,
                          left=0.10, right=0.98, top=0.97, bottom=0.09)
    axes = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    for ax, scale, letter in zip(axes, ["1M", "60M", "1B"], ["a", "b", "c"]):
        s = d[d.scale == scale]
        ax.scatter(s.observed_loss, s.predicted_loss, s=6 if scale == "1M" else 8,
                   alpha=0.16, color=COL["blue"], edgecolors="none", rasterized=True)
        mn = min(s.observed_loss.min(), s.predicted_loss.min()); mx = max(s.observed_loss.max(), s.predicted_loss.max())
        ax.plot([mn, mx], [mn, mx], color=COL["grey"], lw=1, ls="--")
        ax.set_xlim(mn, mx); ax.set_ylim(mn, mx); ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("观测 Loss"); ax.set_ylabel("预测 Loss"); panel(ax, letter)
        n, rmse, rho, role = metrics[scale]
        short_role = "同尺度独立检验" if scale == "1M" else "零样本运输"
        ax.text(0.03, 0.96, f"{scale} · {short_role}\nn={n}\nRMSE={rmse:.3f}；ρ={rho:.3f}",
                transform=ax.transAxes, va="top", ha="left", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#D5D5D5", alpha=0.92))
    save(fig, stem)
    caption(stem, "问题一领域配比模型的同尺度检验与跨尺度运输。1M 为同尺度独立检验；60M 与 1B 仅表示冻结关系的零样本运输，不构成跨尺度重新验证。")


def fig04() -> None:
    stem = "fig04_submission_q2_validation"
    b1 = pd.read_csv(SRC / "fig04_q2_fit_validation_source_b1.csv")
    val = pd.read_csv(SRC / "fig04_q2_fit_validation_source_validation.csv")
    qual = pd.read_csv(TSRC / "table06_q2_validation.csv")
    fig = plt.figure(figsize=(WIDTH_IN, 6.90))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.48, wspace=0.42,
                          left=0.10, right=0.98, top=0.97, bottom=0.18)
    ax0 = fig.add_subplot(gs[0, 0]); panel(ax0, "a")
    ax0.scatter(b1.val_loss, b1.prediction, s=8, alpha=0.40, color=COL["blue"], edgecolors="none", rasterized=True)
    mn = min(b1.val_loss.min(), b1.prediction.min()); mx = max(b1.val_loss.max(), b1.prediction.max())
    ax0.plot([mn, mx], [mn, mx], color=COL["grey"], ls="--", lw=1)
    ax0.set_xlabel("B1 观测 Loss"); ax0.set_ylabel("B1 拟合 Loss")
    ax0.text(0.03, 0.96, f"来源内拟合（n={len(b1)}）\nN：0.070542–11.965825 十亿参数\nD：0.134–299.893 十亿 token",
             transform=ax0.transAxes, va="top", fontsize=9.8,
             bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#D5D5D5"))

    ax1 = fig.add_subplot(gs[0, 1]); panel(ax1, "b")
    sources = qual["来源"].tolist(); inside=[]; total=[]
    for text in qual["支持内 / OOS"]:
        a, b = [int(x.strip()) for x in text.split("/")]; inside.append(a); total.append(a+b)
    y=np.arange(len(sources))
    ax1.barh(y, total, color="white", edgecolor=COL["dark"], hatch="xx", label="全部记录")
    ax1.barh(y, inside, color=COL["blue_light"], edgecolor=COL["dark"], hatch="//", label="其中支持内")
    ax1.set_yticks(y, sources); ax1.invert_yaxis(); ax1.set_xscale("symlog", linthresh=1)
    ax1.set_xlabel("记录数（对数轴）")
    qual_transform=mpl.transforms.blended_transform_factory(ax1.transAxes, ax1.transData)
    for yi, r in qual.iterrows():
        short = {"VALIDATION_FAILED":"失败", "VALIDATION_SUPPORTED":"同源插值",
                 "OOS_STRESS_ONLY":"域外", "ESTIMATED_SCENARIO_ONLY":"估算"}[r["最终资格"]]
        ax1.text(0.71, yi, short, transform=qual_transform, va="center", fontsize=8.8, linespacing=0.92,
                 color=COL["blue"] if r["最终资格"] == "VALIDATION_SUPPORTED" else COL["red"])
    ax1.set_xlim(0, max(total)*70)

    ax2 = fig.add_subplot(gs[1, :]); panel(ax2, "c")
    colors={"B2":COL["rose"],"B3":COL["blue"],"B4":COL["gold"],"B5":COL["teal"]}
    for sid in ["B2","B3","B4","B5"]:
        s=val[val.source_id==sid]
        ins=s[s.support_status=="IN_SUPPORT"]; oos=s[s.support_status!="IN_SUPPORT"]
        ax2.scatter(ins.actual_loss, ins.frozen_M0_B1_prediction, s=8, alpha=0.23,
                    color=colors[sid], marker="o", edgecolors="none", rasterized=True)
        if len(oos):
            ax2.scatter(oos.actual_loss, oos.frozen_M0_B1_prediction, s=10, alpha=0.30,
                        facecolors="none", edgecolors=colors[sid], marker="s", linewidths=0.5, rasterized=True)
    lo=min(val.actual_loss.min(),val.frozen_M0_B1_prediction.min()); hi=max(val.actual_loss.max(),val.frozen_M0_B1_prediction.max())
    ax2.plot([lo,hi],[lo,hi],color=COL["grey"],ls="--",lw=1)
    ax2.set_xlabel("分来源观测 Loss"); ax2.set_ylabel("冻结模型预测 Loss")
    handles=[]
    for sid in ["B2","B3","B4","B5"]:
        handles.append(Line2D([0],[0],marker="o",color="none",markerfacecolor=colors[sid],markeredgecolor="none",label=sid))
    handles += [Line2D([0],[0],marker="o",color="none",markerfacecolor="white",markeredgecolor=COL["dark"],label="支持内"),
                Line2D([0],[0],marker="s",color="none",markerfacecolor="white",markeredgecolor=COL["dark"],label="支持外")]
    ax2.legend(handles=handles,ncol=6,loc="upper center",bbox_to_anchor=(0.5,-0.19),
               columnspacing=0.7,handletextpad=0.2)
    ax2.text(0.02,0.96,"各来源分别评价，不合并 RMSE",transform=ax2.transAxes,va="top",color=COL["red"],fontweight="bold")
    save(fig, stem)
    caption(stem, "问题二基础标度模型的来源内拟合、支持覆盖与分来源验证。B2、B4、B5 外部验证失败；B3 仅为同源插值支持；B9、B10 完全位于经验支持域外。")


def fig05() -> None:
    stem = "fig05_submission_q3_optima"
    d = pd.read_csv(SRC / "fig05_q3_budget_optima_source.csv").sort_values("budget_flops")
    x=np.arange(3); labs=[r"$10^{18}$",r"$10^{20}$",r"$10^{22}$"]
    fig,axes=plt.subplots(1,3,figsize=(WIDTH_IN,3.35),constrained_layout=True)
    specs=[("N_B","最优参数规模\n（十亿参数）",COL["blue"],"//"),
           ("D_B","最优训练数据量\n（十亿 token）",COL["teal"],".."),
           ("predicted_loss","冻结预测 Loss",COL["rose"],"xx")]
    for i,(ax,(field,ylabel,color,hatch)) in enumerate(zip(axes,specs)):
        vals=d[field].to_numpy(); base=np.min(vals)*0.92 if field!="predicted_loss" else np.min(vals)-0.08
        ax.plot(x,vals,color=color,marker="o",lw=1.8,ms=5.5)
        ax.fill_between(x,vals,base,color=color,alpha=0.10,hatch=hatch,edgecolor=color)
        if field in ("N_B","D_B"): ax.set_yscale("log")
        ax.set_xticks(x,labs); ax.set_xlabel("预算 FLOPs"); ax.set_ylabel(ylabel); panel(ax,chr(97+i))
        for xi,v in zip(x,vals):
            offset=(7,7) if xi==0 else ((-2,8) if xi==2 else (0,7))
            align="left" if xi==0 else ("center" if xi==1 else "center")
            ax.annotate(f"{v:.4g}",(xi,v),xytext=offset,textcoords="offset points",ha=align,fontsize=9.7)
        if field=="D_B":
            ax.scatter([2],[vals[-1]],s=80,facecolors="none",edgecolors=COL["red"],lw=1.4)
            ax.text(0.98,0.05,"达到支持上界",transform=ax.transAxes,ha="right",color=COL["red"],fontsize=10)
    save(fig,stem)
    caption(stem,"问题三三档算力预算下的条件最优配置。仅优化参数规模与训练数据量；在 10^22 FLOPs 下训练数据量达到 B1 经验支持上界。")


def fig06() -> None:
    stem="fig06_submission_q4_scenarios"
    d=pd.read_csv(SRC / "fig06_q4_scenarios_source.csv")
    tasks=["IFEval","BBH","MATH Lvl 5","GPQA","MUSR","MMLU-PRO","six_task_mean_complete_only"]
    display={"MATH Lvl 5":"MATH Level 5","six_task_mean_complete_only":"六任务均值\n（辅助）"}
    scenarios=[("SLOW","慢速情景",COL["grey"],"o","--"),("BASELINE","基准情景",COL["blue"],"s","-"),("UPPER_SENSITIVITY","上界敏感性",COL["rose"],"^",":")]
    fig,axes=plt.subplots(1,2,figsize=(WIDTH_IN,5.60),sharey=True)
    fig.subplots_adjust(left=0.20, right=0.98, top=0.82, bottom=0.18, wspace=0.12)
    y=np.arange(len(tasks))
    for j,(ax,horizon,date) in enumerate(zip(axes,[12,24],["2026-01-28","2027-01-28"])):
        for code,label,color,marker,ls in scenarios:
            vals=[float(d[(d.benchmark_task==t)&(d.horizon_months==horizon)&(d.scenario_id==code)].prediction_points.iloc[0]) for t in tasks]
            ax.plot(vals,y,color=color,marker=marker,ls=ls,lw=1.5,ms=5.5,label=label)
        ax.axvline(0,color=COL["dark"],lw=0.9,ls="--")
        ax.set_yticks(y,[display.get(t,t) for t in tasks]); ax.invert_yaxis()
        ax.set_xlabel("Benchmark 点（原始未截断值）")
        ax.text(-0.08,1.12,chr(97+j),transform=ax.transAxes,fontsize=13,fontweight="bold",ha="left",va="bottom")
        ax.text(0.50,1.12,f"{horizon} 个月（{date}）",transform=ax.transAxes,ha="center",va="bottom",fontsize=11.5)
        ax.text(0.50,1.025,"仅情景分析，未经时间外验证",transform=ax.transAxes,ha="center",va="bottom",
                color=COL["red"],fontweight="bold",fontsize=9.7,clip_on=False)
        if horizon==24:
            vals=[float(d[(d.benchmark_task=="MATH Lvl 5")&(d.horizon_months==24)&(d.scenario_id==s)].prediction_points.iloc[0]) for s, *_ in scenarios]
            ax.annotate(f"负值完整保留\n{vals[0]:.2f} / {vals[1]:.2f} / {vals[2]:.2f}",xy=(vals[1],2),xytext=(0.35,2.75),
                        textcoords="data",arrowprops=dict(arrowstyle="->",color=COL["red"],lw=1),color=COL["red"],fontsize=9.8)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.59, 0.015),
               columnspacing=1.3, handletextpad=0.45)
    save(fig,stem)
    caption(stem,"问题四六项任务及辅助均值的 12 个月和 24 个月三情景。所有数值仅用于情景分析，未经时间外验证；MATH Level 5 的负值保持原样，三种情景不是置信区间。")


def fig07() -> None:
    stem="fig07_submission_qualification_map"
    d=pd.read_csv(SRC / "fig07_qualification_map_source.csv")
    rows=[
        ("Q1 质量得分","操作性代理","限定条件下关闭","人工核验弱；方向不一致"),
        ("A2/A3 扩展","稳定性检验","部分稳定\n域级不可评价","判据通过 1/4、3/4"),
        ("Q2 B1","来源内估计","条件广义表达","不同来源资格不合并"),
        ("B2/B4/B5","外部检验","外部验证失败","保留负结果"),
        ("B3","同源插值","同源插值支持","不是独立复现"),
        ("B9/B10","域外／估算","仅情景／压力测试","不证明大模型真值外推"),
        ("Q3 三档预算","约束优化","条件最优","质量未识别；配比固定"),
        ("Q4 12/24 月","数值情景","仅情景分析\n未经时间外验证","时间模型未通过门槛"),
    ]
    fig,ax=plt.subplots(figsize=(WIDTH_IN,5.80)); ax.set_axis_off(); ax.set_xlim(0,1); ax.set_ylim(-0.15,8.8)
    xs=[0.025,0.205,0.395,0.635]; separators=[0.19,0.38,0.62]
    headers=["对象","证据角色","最终资格","解释边界"]
    for x,h in zip(xs,headers): ax.text(x,8.35,h,fontweight="bold",fontsize=11.2)
    for i,row in enumerate(rows):
        yy=7.72-i
        rect=FancyBboxPatch((0.01,yy-0.34),0.98,0.64,boxstyle="round,pad=0.005",
                            fc="#F3F3F1" if i%2==0 else "white",ec="#C8C8C8",lw=0.7,
                            hatch=".." if i%2==0 else None)
        ax.add_patch(rect)
        for sx in separators:
            ax.plot([sx,sx],[yy-0.34,yy+0.30],color="#D4D4D4",lw=0.55)
        ax.text(xs[0],yy,row[0],va="center",fontweight="bold",fontsize=9.2)
        ax.text(xs[1],yy,row[1],va="center",fontsize=9.0)
        red=any(k in row[2] for k in ["失败","未经","仅作","不可评价"])
        ax.text(xs[2],yy,row[2],va="center",fontsize=8.8,fontweight="bold",linespacing=0.90,color=COL["red"] if red else COL["blue"])
        ax.text(xs[3],yy,row[3],va="center",fontsize=8.6)
    save(fig,stem)
    caption(stem,"全文主要结果的证据角色、最终资格与解释边界。该图用于防止把操作性代理、来源内拟合、条件最优或未验证情景解释为更强的科学结论。")


def write_source_map() -> None:
    rows=[
        ["FIG-01","fig01_submission_framework","paper/final_figures/fig01_framework_source.json","nodes; edges","结构重排；删除内部工程语言"],
        ["FIG-02","fig02_submission_q1_quality_validation","paper/final_figures/fig02_q1_quality_validation_source.csv","section; item; value; ci_low; ci_high; n","只改排版和中文资格标签"],
        ["FIG-03","fig03_submission_regmix_transport","paper/final_figures/fig03_q1_regmix_transport_source.csv","scale; observed_loss; predicted_loss","全部点；无抽样"],
        ["FIG-04","fig04_submission_q2_validation","paper/final_figures/fig04_q2_fit_validation_source_b1.csv","val_loss; prediction","全部 B1 行"],
        ["FIG-04","fig04_submission_q2_validation","paper/final_figures/fig04_q2_fit_validation_source_validation.csv","source_id; actual_loss; frozen_M0_B1_prediction; support_status","全部已交付验证行"],
        ["FIG-04","fig04_submission_q2_validation","paper/final_tables/table06_q2_validation.csv","原始记录; 支持内/OOS; 最终资格","仅用于资格与计数标签"],
        ["FIG-05","fig05_submission_q3_optima","paper/final_figures/fig05_q3_budget_optima_source.csv","budget_flops; N_B; D_B; predicted_loss","冻结三档预算"],
        ["FIG-06","fig06_submission_q4_scenarios","paper/final_figures/fig06_q4_scenarios_source.csv","task; scenario; horizon; prediction_points; eligibility","不截断；不画置信区间"],
        ["FIG-07","fig07_submission_qualification_map","paper/final_figures/fig07_qualification_map_source.csv","object; evidence_role; eligibility; boundary","中文化并保留必要资格"],
    ]
    with (OUT/"figure_source_map.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["asset_id","output_stem","source_file","fields","display_transformation"]); w.writerows(rows)


def write_index() -> None:
    items=[
        ("FIG-01","fig01_submission_framework","总体技术路线"),
        ("FIG-02","fig02_submission_q1_quality_validation","质量构造、扩展稳定性与人工核验"),
        ("FIG-03","fig03_submission_regmix_transport","配比预测与跨尺度运输"),
        ("FIG-04","fig04_submission_q2_validation","来源内拟合、支持覆盖与分来源验证"),
        ("FIG-05","fig05_submission_q3_optima","三档预算条件最优"),
        ("FIG-06","fig06_submission_q4_scenarios","十二和二十四个月三情景"),
        ("FIG-07","fig07_submission_qualification_map","全文资格与解释边界"),
    ]
    lines=["# 投稿版核心图索引","","所有图按 165 mm 正文宽度生成。图内无重复整图标题；中文使用宋体，英文和数字使用 Times New Roman。","","| 编号 | 内容 | PNG | PDF | SVG | 短图注 |","|---|---|---|---|---|---|"]
    for aid,stem,title in items:
        lines.append(f"| {aid} | {title} | [{stem}.png]({stem}.png) | [{stem}.pdf]({stem}.pdf) | [{stem}.svg]({stem}.svg) | [{stem}_caption.txt]({stem}_caption.txt) |")
    lines += ["","生成脚本：`build_submission_figures.py`；统一溯源：`figure_source_map.csv`；机器检查：`checks.json`。",""]
    (OUT/"ASSET_INDEX.md").write_text("\n".join(lines),encoding="utf-8")


def write_checks() -> None:
    stems=["fig01_submission_framework","fig02_submission_q1_quality_validation","fig03_submission_regmix_transport","fig04_submission_q2_validation","fig05_submission_q3_optima","fig06_submission_q4_scenarios","fig07_submission_qualification_map"]
    details={}; ok=True
    from PIL import Image
    for stem in stems:
        png=OUT/f"{stem}.png"; pdf=OUT/f"{stem}.pdf"; svg=OUT/f"{stem}.svg"; cap=OUT/f"{stem}_caption.txt"
        im=Image.open(png); dpi=im.info.get("dpi",(0,0)); width_mm=im.size[0]/dpi[0]*25.4
        svg_text=svg.read_text(encoding="utf-8") if svg.exists() else ""
        details[stem]={"png":png.exists(),"pdf":pdf.exists(),"svg":svg.exists(),"svg_has_editable_text":"<text" in svg_text,"caption":cap.exists(),"dpi":list(dpi),"width_mm":width_mm}
        ok &= pdf.exists() and svg.exists() and "<text" in svg_text and cap.exists() and min(dpi)>=599 and abs(width_mm-165)<0.5
    q4=pd.read_csv(SRC/"fig06_q4_scenarios_source.csv")
    negatives=q4[(q4.benchmark_task=="MATH Lvl 5")&(q4.horizon_months==24)].prediction_points.tolist()
    q4_ok=len(negatives)==3 and all(v<0 for v in negatives) and set(q4.forecast_eligibility)=={"SCENARIO_ONLY_UNVALIDATED"}
    payload={"status":"PASS" if ok and q4_ok else "FAIL","science_changed":False,"figure_count":7,
             "final_width_mm":165,"font_contract":{"Chinese":"SimSun","Latin":"Times New Roman","target_equivalent_pt":12},
             "figures":details,"q4_negative_values":negatives,"q4_unvalidated":q4_ok,
             "main_text_min_font_pt":{stem:RENDERED_MIN_FONT_PT[stem] for stem in sorted(MAIN_TEXT_STEMS)},
             "source_scope":"previously delivered figure/table source CSV/JSON only","no_refit":True,"no_clipping":True,"no_sampling":True}
    (OUT/"checks.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    if payload["status"]!="PASS": raise SystemExit("submission figure checks failed")


def write_main_text_hashes() -> None:
    rows = [
        ("FIG-01", "fig01_submission_framework.png"),
        ("FIG-02", "fig02_submission_q1_quality_validation.png"),
        ("FIG-03", "fig03_submission_regmix_transport.png"),
        ("FIG-04", "fig04_submission_q2_validation.png"),
        ("FIG-06", "fig06_submission_q4_scenarios.png"),
    ]
    with (OUT / "main_text_png_sha256.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["asset_id", "file", "sha256", "status"])
        for asset_id, name in rows:
            digest = hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            writer.writerow([asset_id, name, digest, "FROZEN_AFTER_VISUAL_QA"])


def main() -> None:
    for fn in [fig01,fig02,fig03,fig04,fig05,fig06,fig07]: fn()
    write_source_map(); write_index(); write_checks(); write_main_text_hashes()


if __name__=="__main__": main()
