from __future__ import annotations
import csv, hashlib, json
from datetime import datetime
from pathlib import Path
import platform, sys
import numpy as np, pandas as pd, pyarrow

RUN_ID = "20260925T075729+08"
ROOT = Path(__file__).resolve().parents[1]
REG_DIR = ROOT / "scenario_registry"
REG_DIR.mkdir(parents=True, exist_ok=True)
REG_CSV = REG_DIR / "scenario_registry_preregistered.csv"
SEAL = REG_DIR / "SCENARIO_REGISTRY_SEAL.json"

rows = [
    ("S00_NULL_M0_B1","null_reference","S00","H0","none",None,None,None,"off","off",None,"NO_QUALITY_EFFECT","default"),
    ("S01_QREF_QA_H2_B1_R06_ADD","quality_reference","S01","H2","Q_baseline",1.0,0.6,1.0,"additive","off",0.0,"SCENARIO_REFERENCE","scenario_only"),
    ("S02_QC","quality_univariate","S01","H2","Q_C",1.0,0.6,1.0,"additive","off",0.0,"PAIRED_SENSITIVITY","scenario_only"),
    ("S03_H1_IDENTITY","quality_univariate","S01","H1","Q_baseline",None,0.6,1.0,"additive","off",0.0,"BRIDGE_ALTERNATIVE","scenario_only"),
    ("S04_H2_B05","quality_univariate","S01","H2","Q_baseline",0.5,0.6,1.0,"additive","off",0.0,"BRIDGE_ALTERNATIVE","scenario_only"),
    ("S05_H2_B20","quality_univariate","S01","H2","Q_baseline",2.0,0.6,1.0,"additive","off",0.0,"BRIDGE_ALTERNATIVE","scenario_only"),
    ("S06_H3_EQQUANTILE","quality_univariate","S01","H3","Q_baseline",None,0.6,1.0,"additive","off",0.0,"BRIDGE_ALTERNATIVE","scenario_only"),
    ("S07_H4_DIRECTION_ONLY","quality_univariate","S01","H4","none",None,0.6,1.0,"direction_only","off",0.0,"NO_NUMERIC_PREDICTION","direction_only_not_optimizable"),
    ("S08_RB1_02","quality_univariate","S01","H2","Q_baseline",1.0,0.2,1.0,"additive","off",0.0,"R_B1_FIXED_SCENARIO","scenario_only"),
    ("S09_RB1_09","quality_univariate","S01","H2","Q_baseline",1.0,0.9,1.0,"additive","off",0.0,"R_B1_FIXED_SCENARIO","scenario_only"),
    ("S10_RHOQ_00","quality_univariate","S01","H2","Q_baseline",1.0,0.6,0.0,"off","off",0.0,"DEGENERATE_KERNEL_CHECK","scenario_only"),
    ("S11_RHOQ_05","quality_univariate","S01","H2","Q_baseline",1.0,0.6,0.5,"additive","off",0.0,"RHO_Q_FIXED_SCENARIO","scenario_only"),
    ("S12_EFF_KEEP_ETA","quality_univariate","S01","H2","Q_baseline",1.0,0.6,1.0,"effective_data_keep_eta","eta",0.0,"TRANSPORT_FIXED_SCENARIO","scenario_only"),
    ("S13_EFF_KEEP_K","quality_univariate","S01","H2","Q_baseline",1.0,0.6,1.0,"effective_data_keep_k","k",0.0,"TRANSPORT_FIXED_SCENARIO","scenario_only"),
    ("S14_MIX_TAU05","mixture_transport_univariate","S00","H0","none",None,None,None,"off","off",0.5,"TAU_P_FIXED_SCENARIO","scenario_only"),
    ("S15_MIX_TAU10","mixture_transport_univariate","S00","H0","none",None,None,None,"off","off",1.0,"TAU_P_FIXED_SCENARIO","scenario_only"),
    ("S16_MIX_TAUM10_STRESS","mixture_transport_univariate","S00","H0","none",None,None,None,"off","off",-1.0,"FAILURE_STRESS_ONLY","failure_stress"),
    ("S17_B8_REVERSE_COMMON_SUPPORT","conflict_univariate","S00","H0","none",None,None,None,"off","off",0.0,"B8_COMMON_SUPPORT_SLOT_ONLY","NO_NUMERIC_PREDICTION"),
    ("X01_Q_HIGH","extreme_combination","X01","H2","Q_baseline",2.0,0.2,1.0,"additive","off",0.0,"EXTREME_FIXED_COMBINATION","scenario_only"),
    ("X02_Q_CONSERVATIVE","extreme_combination","X02","H2","Q_C",0.5,0.9,0.5,"additive","off",0.0,"EXTREME_FIXED_COMBINATION","scenario_only"),
    ("X03_H3_EFF","extreme_combination","X03","H3","Q_baseline",None,0.6,1.0,"effective_data_keep_eta","eta",0.0,"EXTREME_FIXED_COMBINATION","scenario_only"),
]
fields = ["scenario_order","scenario_id","family","base_scenario","bridge","q_source","h_parameter_b","r_B1","rho_Q","quality_transport","transport_parameter","tau_p","p_change","use","eligibility","frozen_definition"]
def definition(r):
    sid, fam, base, bridge, qsrc, b, rb1, rhoq, qtrans, tparam, tau_p, use, elig = r
    if sid == "S00_NULL_M0_B1":
        return "H0; quality off; mixture transport off; T07 default"
    if sid == "S01_QREF_QA_H2_B1_R06_ADD":
        return "Q_baseline; H2 b=1; r_B1=0.6; rho_Q=1; additive; p fixed/transport off"
    if sid.startswith("S02"): return "relative S01: Q_baseline -> Q_C"
    if sid.startswith("S03"): return "relative S01: H2 -> H1"
    if sid.startswith("S04"): return "relative S01: H2 b=1 -> b=0.5"
    if sid.startswith("S05"): return "relative S01: H2 b=1 -> b=2"
    if sid.startswith("S06"): return "relative S01: H2 -> H3"
    if sid.startswith("S07"): return "relative S01: H2 -> H4; direction only; no numeric loss; not optimizable"
    if sid.startswith("S08"): return "relative S01: r_B1=0.6 -> 0.2"
    if sid.startswith("S09"): return "relative S01: r_B1=0.6 -> 0.9"
    if sid.startswith("S10"): return "relative S01: rho_Q=1 -> 0; quality term off"
    if sid.startswith("S11"): return "relative S01: rho_Q=1 -> 0.5"
    if sid.startswith("S12"): return "relative S01: additive -> effective-data; transport keeps eta"
    if sid.startswith("S13"): return "relative S01: additive -> effective-data; transport keeps k; target beta recomputes eta"
    if sid.startswith("S14"): return "base S00: quality off; tau_p=0.5; mixture transport perturbation"
    if sid.startswith("S15"): return "base S00: quality off; tau_p=1; mixture transport perturbation"
    if sid.startswith("S16"): return "base S00: quality off; tau_p=-1; failure stress only"
    if sid.startswith("S17"): return "base S00: B8 common-support reverse-evidence slot; no legacy k=-20; no out-of-support numeric prediction"
    if sid == "X01_Q_HIGH": return "Q_baseline; H2 b=2; r_B1=0.2; rho_Q=1; additive; tau_p=0; no p change"
    if sid == "X02_Q_CONSERVATIVE": return "Q_C; H2 b=0.5; r_B1=0.9; rho_Q=0.5; additive; tau_p=0; no p change"
    if sid == "X03_H3_EFF": return "Q_baseline; H3; r_B1=0.6; rho_Q=1; effective-data keep eta; tau_p=0; no p change"
    raise ValueError(sid)

with REG_CSV.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for i, r in enumerate(rows, 1):
        sid, fam, base, bridge, qsrc, b, rb1, rhoq, qtrans, tparam, tau_p, use, elig = r
        rec = dict(zip(fields, [i,sid,fam,base,bridge,qsrc,b,rb1,rhoq,qtrans,tparam,tau_p,"none",use,elig,definition(r)]))
        rec = {k: ("" if v is None else v) for k,v in rec.items()}
        w.writerow(rec)

raw = REG_CSV.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
ordered = [tuple(r[:13]) for r in rows]
seal = {
    "seal_status": "SEALED_BEFORE_TEST_METRIC_READ",
    "task_id": "TASK-T06E-P",
    "run_id": RUN_ID,
    "scenario_count": len(rows),
    "scenario_ids_in_order": [r[0] for r in rows],
    "registry_file": "scenario_registry/scenario_registry_preregistered.csv",
    "registry_sha256": sha,
    "registry_bytes": len(raw),
    "frozen_scenario_tuple_sha256": hashlib.sha256(json.dumps(ordered, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
    "sealed_local_time": datetime.now().astimezone().isoformat(timespec="seconds"),
    "seed_audit_anchor": 20260927,
    "solver": "NONE",
    "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "pyarrow": pyarrow.__version__, "platform": platform.platform()},
    "constraints": [
        "No scenario may be added, deleted, renamed, reordered, or semantically changed after this seal.",
        "Only the 21 preregistered IDs are permitted.",
        "No Cartesian-product scenarios are permitted.",
        "No random sampling or random optimization is permitted.",
        "S07 and S17 remain registered without numeric prediction."
    ]
}
SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"registry": str(REG_CSV), "registry_sha256": sha, "seal": str(SEAL), "scenario_count": len(rows)}, ensure_ascii=False))

