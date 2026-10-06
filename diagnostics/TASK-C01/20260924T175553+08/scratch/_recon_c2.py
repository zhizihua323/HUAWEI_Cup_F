import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
c1 = pd.read_csv(ext(ROOT/"leaderboard_cleaned.csv"), low_memory=False)
c2 = pd.read_csv(ext(ROOT/"leaderboard_enhanced.csv"), low_memory=False)
b = c2[c1.columns]
print("index equal:", c1.index.equals(b.index), "columns equal:", c1.columns.equals(b.columns))
for col in c1.columns:
    x, y = c1[col], b[col]
    if x.dtype.kind in "fi":
        neq = ~np.isclose(x.astype(float).to_numpy(), y.astype(float).to_numpy(), equal_nan=True)
        n = int(np.sum(neq))
    else:
        xs = x.fillna("~NA~").astype(str).to_numpy(); ys = y.fillna("~NA~").astype(str).to_numpy()
        neq = xs != ys; n = int(np.sum(neq))
    print(f"  {col!r}: dtype={x.dtype}/{y.dtype} ndiff={n}")
    if n and x.dtype.kind not in "fi":
        print("     ex:", xs[np.flatnonzero(neq)[0]], "|", ys[np.flatnonzero(neq)[0]])
    if n and x.dtype.kind in "fi":
        i = np.flatnonzero(neq)[0]; print("     ex:", x.iloc[i], "|", y.iloc[i], c1.Model.iloc[i])
# find exact float diffs
for col in ["Average ⬆️","IFEval","BBH","MATH Lvl 5","GPQA","MUSR","MMLU-PRO","#Params (B)"]:
    d = (c1[col].astype(float)-b[col].astype(float)).abs()
    print(f"  maxabs {col}: {np.nanmax(d):.12g}  n_not_equal={int((c1[col].astype(float)!=b[col].astype(float)).sum())}")
print()
print("c1 eq c2 first 12 cols: ", c1.equals(b))
print("equal via compare:", c1.compare(b).shape)
