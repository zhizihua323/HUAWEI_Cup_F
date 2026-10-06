import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
pq = pd.read_parquet(ext(ROOT/"data"/"train-00000-of-00001.parquet"))
c1 = pd.read_csv(ext(ROOT/"leaderboard_cleaned.csv"), low_memory=False)
c2 = pd.read_csv(ext(ROOT/"leaderboard_enhanced.csv"), low_memory=False)
print("dtypes c1:", c1.dtypes.to_dict())
print()
print("dtypes c2[c1.columns]:", c2[c1.columns].dtypes.to_dict())
print()
a=c1; b=c2[c1.columns]
diffs=[]
for col in c1.columns:
    if a[col].dtype != b[col].dtype:
        diffs.append(("dtype", col, str(a[col].dtype), str(b[col].dtype)))
        continue
    if a[col].dtype.kind in "fi":
        neq = ~np.isclose(a[col].astype(float), b[col].astype(float), equal_nan=True)
    else:
        neq = ~(a[col].fillna("~NA~").astype(str) == b[col].fillna("~NA~").astype(str))
    if neq.any():
        diffs.append(("value", col, int(neq.sum())))
print("diffs:", diffs)
print()
hl = pq["Hub License"].fillna("~NA~").astype(str)
hc = c1["Hub License"].fillna("~NA~").astype(str)
ne = hl != hc
print("Hub license diff count:", int(ne.sum()))
print("examples (pq | c1):")
for i in np.flatnonzero(ne.to_numpy())[:8]:
    print("   ", repr(pq["Hub License"].iloc[i]), "|", repr(c1["Hub License"].iloc[i]), "|", c1.Model.iloc[i])
print()
sd = pq["Submission Date"].fillna("~NA~").astype(str); sc = c1["Submission Date"].fillna("~NA~").astype(str)
ne2 = sd != sc
print("Submission diff count:", int(ne2.sum()))
for i in np.flatnonzero(ne2.to_numpy())[:8]:
    print("   ", repr(pq["Submission Date"].iloc[i]), "|", repr(c1["Submission Date"].iloc[i]), "|", c1.Model.iloc[i])
print()
print("pq Submit Date sample dtypes:", pq["Submission Date"].iloc[:3].tolist())
print("C1 param -1 count:", int((c1["#Params (B)"]==-1).sum()), "nan:", int(c1["#Params (B)"].isna().sum()))
print("pq param -1 count:", int((pq["#Params (B)"]==-1).sum()), "nan:", int(pq["#Params (B)"].isna().sum()))
