import os, json, collections
from pathlib import Path
import pandas as pd, numpy as np
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p = str(Path(p).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p
pq = pd.read_parquet(ext(ROOT/"data"/"train-00000-of-00001.parquet"))
print("C9 shape:", pq.shape)
print("C9 columns:", list(pq.columns))
print(pq.dtypes.to_string())
print("C9 head:")
print(pq.head(3).to_string()[:2000])
c1 = pd.read_csv(ext(ROOT/"leaderboard_cleaned.csv"), low_memory=False)
print()
print("C1 shape", c1.shape, "C9 shape", pq.shape)
print("fullname==Model identical order:", bool(pq.fullname.eq(c1.Model).all()))
TASKS = ["IFEval","BBH","MATH Lvl 5","GPQA","MUSR","MMLU-PRO"]
for t in TASKS:
    col = t + " Raw"
    print(f"  {t}: {'Raw' in col and col in pq.columns} allclose={np.allclose(pq[col].astype(float), c1[t].astype(float), equal_nan=True)}")
print()
for name in ["C1","C2","C3","C5","C6","C7"]:
    pass
for f in ["leaderboard_cleaned.csv","leaderboard_enhanced.csv","leaderboard_extended_timeseries.csv","loss_benchmark_bridge.csv","loss_benchmark_bridge_expanded.csv","model_architecture_metadata.csv"]:
    d = pd.read_csv(ext(ROOT/f), low_memory=False)
    print(f"--- {f}: rows={len(d)} cols={len(d.columns)}")
