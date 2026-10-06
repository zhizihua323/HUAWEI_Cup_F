import numpy as np, pandas as pd
from pathlib import Path
W = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace")
ROOT = W/"F题"/"real_attachments"/"C_efficiency_evolution"
def ext(p):
    p=str(Path(p).resolve()); return "\\\\?\\"+p if not p.startswith("\\\\?\\") else p
c3 = pd.read_csv(ext(ROOT/"leaderboard_extended_timeseries.csv"), low_memory=False)
print("C3 columns:", list(c3.columns), c3.shape)
print("C3 Year:", c3.Year.describe().to_dict(), "null:", int(c3.Year.isna().sum()))
print("C3 Source counts:"); print(c3.Source.value_counts(dropna=False).to_string())
print("C3 dup Model:", int(c3.Model.duplicated().sum()), "unique:", c3.Model.nunique())
print("C3 Model+Year dup:", int(c3.duplicated(["Model","Year"]).sum()))
print("C3 zero-count per col:", {c:int((c3[c]==0).sum()) for c in ["Average","IFEval","BBH","MATH_Lvl5","GPQA","MUSR","MMLU_PRO"]})
print()
c5 = pd.read_csv(ext(ROOT/"loss_benchmark_bridge.csv"), low_memory=False)
c6 = pd.read_csv(ext(ROOT/"loss_benchmark_bridge_expanded.csv"), low_memory=False)
print("C5:", c5.shape, "C6:", c6.shape)
print("C5 comparability:"); print(c5.Loss_Comparability.value_counts(dropna=False).to_string())
print("C6 comparability:"); print(c6.Loss_Comparability.value_counts(dropna=False).to_string())
print("C5 models subset of C6:", set(c5.Model).issubset(set(c6.Model)))
print("C5 unique models:", c5.Model.nunique(), "C6 unique:", c6.Model.nunique())
print("overlap:", len(set(c5.Model)&set(c6.Model)))
print("C5 Loss_Source:"); print(c5.Loss_Source.value_counts(dropna=False).to_string())
print()
print("C6 Loss_Source:"); print(c6.Loss_Source.value_counts(dropna=False).to_string())
print()
print("C5/C6 value ranges:")
for n,d in [("C5",c5),("C6",c6)]:
    for col in ["N_params_B","D_tokens_B","Val_Loss","LB_Average","LB_IFEval","LB_BBH","LB_MATH","LB_GPQA","LB_MUSR","LB_MMLU_PRO"]:
        print(f"  {n}.{col}: n={d[col].notna().sum()} min={d[col].min()} max={d[col].max()}")
print()
b = pd.read_csv(ext(W/"F题"/"real_attachments"/"B_scaling_laws"/"pythia_training_log_existing.csv"), low_memory=False)
print("B1 columns:", list(b.columns))
print()
c7 = pd.read_csv(ext(ROOT/"model_architecture_metadata.csv"), low_memory=False)
print("C7:", c7.shape); print(c7.to_string())
