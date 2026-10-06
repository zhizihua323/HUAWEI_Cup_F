import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
pq = pd.read_parquet(ext(ROOT/"data"/"train-00000-of-00001.parquet"))
c1 = pd.read_csv(ext(ROOT/"leaderboard_cleaned.csv"), low_memory=False)
T = ["IFEval","BBH","MATH Lvl 5","GPQA","MUSR","MMLU-PRO"]
print("fullname==Model:", bool(pq.fullname.eq(c1.Model).all()))
for t in T:
    same = np.allclose(pq[t].astype(float), c1[t].astype(float), equal_nan=True)
    mx = np.nanmax(np.abs(pq[t].astype(float)-c1[t].astype(float))) if not same else 0.0
    print(f"  {t}: allclose={same} maxabs={mx:.6g}  pq[{t}] range=({pq[t].min():.4f},{pq[t].max():.4f})  raw range=({pq[t+' Raw'].min():.4f},{pq[t+' Raw'].max():.4f}) c1 range=({c1[t].min():.4f},{c1[t].max():.4f})")
print("Average allclose:", np.allclose(pq["Average ⬆️"], c1["Average ⬆️"], equal_nan=True))
print("#Params allclose:", np.allclose(pq["#Params (B)"], c1["#Params (B)"], equal_nan=True))
print("Submission Date equal:", bool(pq["Submission Date"].astype(str).eq(c1["Submission Date"].astype(str)).all()))
print("Hub License equal:", bool(pq["Hub License"].fillna("~NA~").astype(str).eq(c1["Hub License"].fillna("~NA~").astype(str)).all()))
print("Type equal:", bool(pq["Type"].astype(str).eq(c1["Type"].astype(str)).all()))
print()
print("ratio check raw*100 vs norm (mean):")
for t in T:
    r = (pq[t+" Raw"].astype(float)*100) / pq[t].astype(float)
    print(f"  {t}: median ratio={r.median():.10f} min={r.min():.6f} max={r.max():.6f}")
