import pandas as pd, numpy as np, json, io, os
B = r"diagnostics\TASK-C01\20260924T175553+08"
files = sorted(os.listdir(B))
print("C01 dir file count:", len(files))
m = json.load(io.open(os.path.join(B, "output_manifest.json"), encoding="utf-8"))
print("manifest entries:", m["artifact_count"], "self-listed:", any(a["file"] == "output_manifest.json" for a in m["artifacts"]))
print("scratch entries:", sum(1 for a in m["artifacts"] if a["file"].startswith("scratch/")))
print("root entries:", sum(1 for a in m["artifacts"] if not a["file"].startswith("scratch/")))
# leaf nonnumeric reconciliation
leaf = pd.read_csv(B + r"\c8_leaf_metrics.csv.gz", encoding="utf-8-sig")
print("leaf rows:", len(leaf))
print("nonnumeric total:", int(leaf.nonnumeric.sum()))
print("nonnumeric excl alias:", int(((leaf.nonnumeric == 1) & (leaf.metric != "alias")).sum()))
print("nonnumeric alias only:", int(((leaf.nonnumeric == 1) & (leaf.metric == "alias")).sum()))
print("metric slots total:", int((leaf.metric != "alias").sum()))
ti = pd.read_csv(B + r"\c8_task_inventory.csv", encoding="utf-8-sig")
print("inventory nonnumeric:", int(ti.nonnumeric_metric_values.sum()), "numeric slots:", int(ti.numeric_metric_value_slots.sum()))
print("value_raw_type:", leaf.value_raw_type.value_counts().to_dict())
