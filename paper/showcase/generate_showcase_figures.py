from __future__ import annotations

from pathlib import Path
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "showcase" / "showcase_figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Times New Roman", "SimSun"],
    "font.size": 9.6,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.6,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 8.7,
    "ytick.labelsize": 8.7,
    "legend.fontsize": 8.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.06,
})

COL = ["#264653", "#2A9D8F", "#E9A23B", "#C8553D", "#6A4C93", "#5F6B6D"]

def save(fig, name):
    path = OUT / name
    fig.savefig(path, dpi=600)
    plt.close(fig)
    print(path)

def fig1():
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.4); ax.axis("off")
    boxes = {
        "A": (0.6, 5.7, 2.25, 0.9, "A侧数据质量\n去重·方向统一·11特征"),
        "B": (3.7, 5.7, 2.35, 0.9, "B6来源质量关系\nMQ-add条件接受"),
        "C": (6.9, 5.7, 2.45, 0.9, "B1来源标度关系\nM0_B1主模型"),
        "M": (3.7, 3.95, 2.35, 0.9, "RegMix领域配比\n同尺度预测与运输诊断"),
        "Q3": (3.7, 2.2, 2.35, 0.9, "预算约束优化\n条件最优N_B、D_B与KKT"),
        "Q4": (6.9, 2.2, 2.45, 0.9, "Loss-Benchmark识别\n六任务条件基线"),
        "S": (0.6, 3.95, 2.25, 0.9, "证据分层\n来源内·情景·不可识别·冲突"),
        "R": (0.6, 2.2, 2.25, 0.9, "检验与复现\n门限·剖面·manifest"),
    }
    for x, y, w, h, txt in boxes.values():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                                    linewidth=1.0, edgecolor="#2F3A3D", facecolor="#F7F7F4"))
        ax.text(x+w/2, y+h/2, txt, ha="center", va="center", linespacing=1.25)
    arrows = [("A","S"),("B","M"),("C","M"),("S","M"),("M","Q3"),("C","Q4"),("Q3","R"),("Q4","R")]
    for a,b in arrows:
        xa,ya,wa,ha,_ = boxes[a]; xb,yb,wb,hb,_ = boxes[b]
        p1=(xa+wa/2,ya); p2=(xb+wb/2,yb+hb)
        if ya < yb:
            p1=(xa+wa/2,ya+ha); p2=(xb+wb/2,yb)
        ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle="-|>",mutation_scale=10,linewidth=1.0,color="#4C5B5F"))
    ax.text(5, 7.05, "四问建模主线与证据分层", ha="center", va="center", fontsize=12, fontproperties=matplotlib.font_manager.FontProperties(family="SimHei"))
    ax.text(5, 0.75, "实线为正式分析接口；跨来源映射与未来输出均须保留条件资格。",
            ha="center", va="center", color="#4C5B5F")
    save(fig, "fig1_modeling_framework.png")

def fig2():
    quality = {
        "mean": 0.4959665403209771, "median": 0.48247852816491466,
        "p10": 0.32164589603454746, "p90": 0.681334413298976,
        "usability": 0.603019195964164, "knowledge": 0.5341024804018979,
        "education": 0.3507774096831335,
        "disagreement": 0.3030181779626825, "high_fraction": 0.06342737642003018,
        "coverage": 0.9999272270439625, "unique": 261086, "valid": 261067,
    }
    fig, axs = plt.subplots(2, 2, figsize=(7.15, 5.35))
    ax=axs[0,0]
    labels=["物理记录","唯一键","主Q有效","主Q缺失"]
    vals=[272505,261086,261067,19]
    bars=ax.bar(labels,vals,color=[COL[0],COL[1],COL[2],COL[3]])
    ax.set_yscale("log"); ax.set_ylabel("记录数（对数坐标）")
    for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v*1.15,f"{v:,}",ha="center",va="bottom",fontsize=7.6)
    ax.set_ylim(10,5e5); ax.grid(axis="y",alpha=.18)
    ax.set_title("(a) 质量分母与有效记录")
    ax=axs[0,1]
    labels=["可用性","知识性","教育推理"]
    vals=[quality["usability"],quality["knowledge"],quality["education"]]
    bars=ax.bar(labels,vals,color=[COL[2],COL[1],COL[3]])
    ax.set_ylim(0,0.72); ax.set_ylabel("组内均值")
    for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,v+0.018,f"{v:.3f}",ha="center",fontsize=8.0)
    ax.grid(axis="y",alpha=.18); ax.set_title("(b) 三组操作性质量均值")
    ax=axs[1,0]
    x=[0,1]; y=[quality["disagreement"],quality["high_fraction"]]
    bars=ax.bar(["平均分歧范围","范围>0.5比例"],y,color=[COL[4],COL[3]])
    ax.set_ylim(0,0.4); ax.set_ylabel("取值或比例")
    for b,v in zip(bars,y): ax.text(b.get_x()+b.get_width()/2,v+0.012,f"{v:.3f}",ha="center",fontsize=8.0)
    ax.grid(axis="y",alpha=.18); ax.set_title("(c) 质量冲突诊断")
    ax=axs[1,1]
    xs=[quality["p10"],quality["median"],quality["mean"],quality["p90"]]
    ax.plot(xs,[1,1,1,1],color=COL[0],linewidth=2)
    ax.scatter(xs,[1,1,1,1],color=[COL[1],COL[2],COL[3],COL[4]],zorder=3)
    for x,t in zip(xs,["P10","中位数","均值","P90"]):
        ax.annotate(f"{t}\n{x:.3f}",(x,1),xytext=(0,12 if t in ["均值","P90"] else -26),textcoords="offset points",ha="center",fontsize=7.7)
    ax.set_xlim(0.25,0.75); ax.set_ylim(0.65,1.35); ax.set_yticks([]); ax.set_xlabel("Q_baseline")
    ax.set_title("(d) 主质量分位点")
    fig.suptitle("问题一：质量评价与冲突分析",fontproperties=matplotlib.font_manager.FontProperties(family="SimHei"),fontsize=12)
    fig.tight_layout(rect=[0,0,1,0.95])
    save(fig, "fig2_q1_quality_conflict.png")

def fig3():
    val = pd.read_csv(ROOT/"diagnostics/TASK-T06E-P/20260925T075729+08/mixture_audit/regmix_fixed_model_validation.csv")
    smap={"test_1m":"1M检验","test_60m":"60M运输","test_1B":"1B运输"}
    val=val[val["scale"].isin(smap)].copy()
    val["label"]=val["scale"].map(smap)
    order=["1M检验","60M运输","1B运输"]
    val=val.set_index("label").loc[order].reset_index()
    pred=pd.read_csv(ROOT/"solution/outputs/mixture/linear_test_1m_predictions.csv")
    actual=[]; fitted=[]
    for c in pred.columns:
        if c.startswith("actual_"):
            suffix=c[len("actual_"):]
            pc="pred_"+suffix
            if pc in pred.columns:
                actual.extend(pred[c].to_numpy(float)); fitted.extend(pred[pc].to_numpy(float))
    actual=np.asarray(actual); fitted=np.asarray(fitted)
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.15),gridspec_kw={"width_ratios":[1,1.15]})
    ax=axs[0]
    bars=ax.bar(val["label"], val["rmse_equal_domain_mean"], color=[COL[1],COL[2],COL[3]])
    ax.set_ylabel("逐域等权RMSE"); ax.set_title("(a) 同尺度检验与跨尺度运输")
    for b,v in zip(bars,val["rmse_equal_domain_mean"]): ax.text(b.get_x()+b.get_width()/2,v+0.045,f"{v:.3f}",ha="center",fontsize=8.0)
    ax.set_ylim(0,3.65); ax.grid(axis="y",alpha=.18)
    ax.text(0,0.12,f"1M MSE改善 {val.iloc[0]['mse_improvement_vs_domain_training_mean']*100:.2f}%\nSpearman {val.iloc[0]['spearman_equal_domain_mean']:.3f}",ha="center",va="bottom",fontsize=8.0)
    ax=axs[1]
    ax.scatter(actual,fitted,s=11,alpha=.28,color=COL[0],edgecolors="none",label="逐配方")
    lo=min(actual.min(),fitted.min()); hi=max(actual.max(),fitted.max())
    ax.plot([lo,hi],[lo,hi],color=COL[3],linewidth=1.2,label="y=x")
    ax.set_xlim(lo,hi); ax.set_ylim(lo,hi); ax.set_xlabel("1M检验实测Loss"); ax.set_ylabel("冻结模型预测Loss")
    ax.set_title("(b) 1M预测—实测一致性"); ax.legend(frameon=False,loc="upper left")
    fig.tight_layout()
    save(fig, "fig3_regmix_validation.png")

def fig4():
    df=pd.read_csv(ROOT/"diagnostics/TASK-T06E-B/20260925T100306+08/fit/full_fit_predictions.csv")
    df=df[(df["source"]=="B1") & (df["model"]=="M0_B1") & (df["role"]=="in_sample")].copy()
    actual=df["actual"].to_numpy(float); pred=df["prediction"].to_numpy(float); residual=actual-pred
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.1))
    ax=axs[0]
    hb=ax.hexbin(actual,pred,gridsize=36,mincnt=1,cmap="YlGnBu",linewidths=0)
    lo=min(actual.min(),pred.min()); hi=max(actual.max(),pred.max())
    ax.plot([lo,hi],[lo,hi],color=COL[3],linewidth=1.2)
    ax.set_xlabel("B1实测Loss"); ax.set_ylabel("M0_B1预测Loss"); ax.set_title("(a) 预测—实测")
    fig.colorbar(hb,ax=ax,label="样本数",shrink=.85)
    ax=axs[1]
    ax.scatter(pred,residual,s=6,alpha=.18,color=COL[0],edgecolors="none")
    ax.axhline(0,color=COL[3],linewidth=1.0)
    ax.set_xlabel("M0_B1预测Loss"); ax.set_ylabel("实测−预测"); ax.set_title("(b) 残差诊断")
    ax.text(0.02,0.96,f"n={len(df)}\nRMSE={math.sqrt(np.mean(residual**2)):.4f}",transform=ax.transAxes,ha="left",va="top",fontsize=8.2)
    fig.tight_layout(); save(fig,"fig4_b1_scaling_fit.png")

def fig5():
    df=pd.read_csv(ROOT/"diagnostics/TASK-T07/20260925T113744+08/budget_scenario_optima.csv")
    df=df[(df["scenario_id"]=="S00_NULL_M0_B1") & (df["H"]==2048)].copy()
    order=["1e+18","1e+20","1e+22"]
    df["budget_flops"]=df["budget_flops"].astype(str)
    df=df.set_index("budget_flops").loc[order].reset_index()
    labels=["10^18","10^20","10^22"]
    fig,axs=plt.subplots(1,3,figsize=(7.15,2.85))
    for ax,col,label,color in zip(axs,["N_B","D_B","predicted_loss"],["N_B / 十亿参数","D_B / 十亿token","预测Loss"],COL[:3]):
        bars=ax.bar(labels,df[col],color=color)
        ax.set_xlabel("预算 / FLOPs"); ax.set_ylabel(label)
        ax.grid(axis="y",alpha=.18)
        if col!="predicted_loss": ax.set_yscale("log")
        for b,v in zip(bars,df[col]): ax.text(b.get_x()+b.get_width()/2,v*(1.08 if col!="predicted_loss" else 1.01),f"{v:.3g}",ha="center",fontsize=7.8)
    axs[2].set_ylim(1.95,3.75)
    axs[2].text(2,df.iloc[2]["predicted_loss"]+0.11,"D上界",ha="center",fontsize=7.8,color=COL[3])
    fig.suptitle("三档预算下的条件最优N_B—D_B配置",fontproperties=matplotlib.font_manager.FontProperties(family="SimHei"),fontsize=12)
    fig.tight_layout(rect=[0,0,1,0.92]); save(fig,"fig5_budget_optima.png")

def fig6():
    df=pd.read_csv(ROOT/"diagnostics/TASK-T07/20260925T113744+08/context_sensitivity.csv")
    df=df[df["scenario_id"]=="S00_NULL_M0_B1"].copy()
    budgets=["1e+18","1e+20","1e+22"]; labels=["10^18","10^20","10^22"]
    fig,axs=plt.subplots(1,3,figsize=(7.25,2.75))
    for ax,col,ylab in zip(axs,["N_B","D_B","predicted_loss"],["N_B / 十亿参数","D_B / 十亿token","预测Loss"]):
        for b,l,c in zip(budgets,labels,COL):
            d=df[df["budget_flops"].astype(str)==b].sort_values("H")
            ax.plot(d["H"],d[col],marker="o",markersize=3.3,linewidth=1.15,color=c,label=l)
        ax.axvline(30000,color="#777777",linestyle="--",linewidth=.9)
        ax.set_xscale("log"); ax.set_xlabel("上下文长度H / token")
        ax.set_ylabel(ylab); ax.grid(alpha=.16)
        if col!="predicted_loss": ax.set_yscale("log")
    axs[0].legend(frameon=False,title="预算",loc="best")
    axs[2].text(31000,axs[2].get_ylim()[1]*.97,"H_crit=30000",rotation=90,va="top",ha="left",fontsize=7.5,color="#555555")
    fig.suptitle("上下文敏感性与活跃结构变化",fontproperties=matplotlib.font_manager.FontProperties(family="SimHei"),fontsize=12)
    fig.tight_layout(rect=[0,0,1,0.92]); save(fig,"fig6_h_sensitivity.png")

def fig7():
    df=pd.read_csv(ROOT/"diagnostics/TASK-T08/20260925T142203+0800/taskwise_progress.csv")
    tasks=["IFEval_pct","BBH_pct","MATH Lvl 5_pct","GPQA_pct","MUSR_pct","MMLU-PRO_pct"]
    labels=["IFEval","BBH","MATH L5","GPQA","MuSR","MMLU-PRO"]
    d=df.set_index("benchmark_task").loc[tasks]
    y=np.arange(len(tasks)); low=d["constant_baseline_points"]-d["conditional_interval_low_points"]; high=d["conditional_interval_high_points"]-d["constant_baseline_points"]
    fig,ax=plt.subplots(figsize=(7.15,3.35))
    ax.errorbar(d["constant_baseline_points"],y,xerr=np.vstack([low,high]),fmt="o",color=COL[0],ecolor=COL[1],capsize=4,markersize=5,linewidth=1.1)
    for i,(v,lo,hi) in enumerate(zip(d["constant_baseline_points"],d["conditional_interval_low_points"],d["conditional_interval_high_points"])):
        ax.text(hi+0.8,i,f"{v:.2f} [{lo:.2f}, {hi:.2f}]",va="center",fontsize=8.0)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.set_xlim(0,46); ax.set_xlabel("Benchmark得分 / 分")
    ax.set_title("问题四：六任务条件基线与条件区间（T08当前冻结）")
    ax.grid(axis="x",alpha=.16)
    ax.text(0.01,0.02,"标注：PROVISIONAL_Q4_CURRENT_FREEZE；不是未来能力点预测。",transform=ax.transAxes,fontsize=8.0,color="#555555")
    fig.tight_layout(); save(fig,"fig7_q4_task_baseline_interval.png")

if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()

