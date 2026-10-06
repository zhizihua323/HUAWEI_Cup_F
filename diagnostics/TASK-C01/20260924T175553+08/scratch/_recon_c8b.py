import json, os, collections
from pathlib import Path

def ext(p):
    p = str(Path(p).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p

root = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\F题\real_attachments\C_efficiency_evolution\detailed_results")
taskc = collections.Counter(); metricc = collections.Counter(); group_sub = collections.Counter()
nsamples_types = collections.Counter()
per_task_metric_examples = {}
nm = collections.Counter()
for dirpath, _, files in os.walk(ext(root)):
    for f in sorted(x for x in files if x.lower().endswith(".json")):
        p = Path(dirpath)/f
        try:
            with open(p,"r",encoding="utf-8") as h: d=json.load(h)
        except Exception: continue
        res = d.get("results")
        if not isinstance(res, dict): continue
        for k,v in res.items():
            taskc[k]+=1
            if isinstance(v, dict):
                for m in v: metricc[m]+=1
        gs = d.get("group_subtasks")
        if isinstance(gs, dict):
            for k in gs: group_sub[k]+=1
        ns = d.get("n-samples")
        if isinstance(ns, dict):
            for k,v in list(ns.items()):
                nsamples_types[type(v).__name__]+=1
        nm[str(d.get("model_name"))]+=1
print("distinct result task keys:", len(taskc))
for k,v in sorted(taskc.items()): print(f"  {v:5d}  {k}")
print()
print("distinct metric keys:", len(metricc))
for k,v in sorted(metricc.items()): print(f"  {v:5d}  {k}")
print()
print("group_subtasks keys:", len(group_sub), dict(group_sub))
print("n-samples value types:", dict(nsamples_types))
print("distinct model_name:", len(nm))
print("top model_name:", nm.most_common(5))
