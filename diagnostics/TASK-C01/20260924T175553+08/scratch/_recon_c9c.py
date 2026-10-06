import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
pq = pd.read_parquet(ext(ROOT/"data"/"train-00000-of-00001.parquet"))
c1 = pd.read_csv(ext(ROOT/"leaderboard_cleaned.csv"), low_memory=False)
c2 = pd.read_csv(ext(ROOT/"leaderboard_enhanced.csv"), low_memory=False)
print("c1.equals(c2[c1.columns]):", c1.equals(c2[c1.columns]))
print()
nd_p = ~np.isclose(pq["#Params (B)"].astype(float), c1["#Params (B)"].astype(float), equal_nan=True)
print("#Params differ rows:", int(nd_p.sum()))
if nd_p.sum():
    print(pd.DataFrame({"Model":c1.Model[nd_p], "C1":c1["#Params (B)"][nd_p], "C9":pq["#Params (B)"][nd_p]}).head(10).to_string())
sd = pq["Submission Date"].astype(str) != c1["Submission Date"].astype(str)
print()
print("Submission Date differ rows:", int(sd.sum()))
if sd.sum():
    print(pd.DataFrame({"Model":c1.Model[sd], "C1":c1["Submission Date"][sd], "C9":pq["Submission Date"][sd]}).head(10).to_string())
hl_p = pq["Hub License"].fillna("~NA~").astype(str) != c1["Hub License"].fillna("~NA~").astype(str)
print()
print("Hub License differ rows:", int(hl_p.sum()))
if hl_p.sum():
    print(pd.DataFrame({"Model":c1.Model[hl_p], "C1":c1["Hub License"][hl_p], "C9":pq["Hub License"][hl_p]}).head(10).to_string())
print()
print("C1 dup Model:", int(c1.Model.duplicated().sum()), "unique:", c1.Model.nunique())
print("C2 dup Model:", int(c2.Model.duplicated().sum()), "unique:", c2.Model.nunique())
print("C9 dup fullname:", int(pq.fullname.duplicated().sum()), "unique:", pq.fullname.nunique())
print("C9 dup eval_name:", int(pq.eval_name.duplicated().sum()), "unique:", pq.eval_name.nunique())
print("C1 vs C9 full set equal:", set(c1.Model)==set(pq.fullname))
print()
print("exact dup rows C1:", int(c1.duplicated().sum()), " C2:", int(c2.duplicated().sum()), " C9:", int(pq.duplicated().sum()))
