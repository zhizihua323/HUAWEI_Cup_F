import os, json, collections
import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
c5 = pd.read_csv(ext(ROOT/"loss_benchmark_bridge.csv"), low_memory=False)
c6 = pd.read_csv(ext(ROOT/"loss_benchmark_bridge_expanded.csv"), low_memory=False)
m = c5.merge(c6, on="Model", suffixes=("_C5","_C6"))
print("C5-C6 merged:", len(m))
for col in ["N_params_B","D_tokens_B","Val_Loss","LB_Average","LB_IFEval","LB_BBH","LB_MATH","LB_GPQA","LB_MUSR","LB_MMLU_PRO"]:
    a=m[col+"_C5"].astype(float); b=m[col+"_C6"].astype(float)
    same = np.isclose(a,b,equal_nan=True)
    print(f"  {col}: n_diff={int((~same).sum())} maxabs={np.nanmax(np.abs(a-b)) if (~same).any() else 0}")
print("  Loss_Comparability equal:", int((m.Loss_Comparability_C5==m.Loss_Comparability_C6).sum()), "/", len(m))
print("  Loss_Source equal:", int((m.Loss_Source_C5==m.Loss_Source_C6).sum()), "/", len(m))
print()
# C8 directories with >1 json
root = ROOT/"detailed_results"
multi=[]
sizes=[]
for dp,_,fs in os.walk(ext(root)):
    js=[f for f in fs if f.lower().endswith(".json")]
    if len(js)>1: multi.append((Path(dp).name, js))
print("dirs with >1 json:", len(multi), "extra files:", sum(len(x[1])-1 for x in multi))
for n,js in multi[:8]: print("   ", n, js)
print()
c4 = pd.read_csv(ext(ROOT/"epoch_all_ai_models.csv"), low_memory=False)
print("C4:", c4.shape)
for col in ["Model","Domain","Organization","Publication date","Parameters","Parameters notes","Training compute (FLOP)","Training dataset size (total)","Dataset size notes","Open model weights?","Confidence","Last modified","Model accessibility","Base model","Epochs"]:
    if col in c4.columns:
        print(f"  {col}: missing={int(c4[col].isna().sum())} unique={c4[col].nunique()} example={c4[col].dropna().iloc[0] if c4[col].notna().any() else ''}"[:200])
    else:
        print(f"  {col}: NOT PRESENT")
print()
print("C4 Domain top:"); print(c4.Domain.value_counts(dropna=False).head(10).to_string())
print("C4 Publication date parse:", pd.to_datetime(c4["Publication date"], errors="coerce", format="mixed").notna().sum(), "/", len(c4))
