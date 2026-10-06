import json, os, collections
from pathlib import Path

def ext(p):
    p = str(Path(p).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p

root = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\F题\real_attachments\C_efficiency_evolution\detailed_results")
confc = collections.Counter(); conf_missing = collections.Counter()
n = 0; old = []
for dirpath, _, files in os.walk(ext(root)):
    for f in sorted(x for x in files if x.lower().endswith(".json")):
        p = Path(dirpath)/f
        try:
            with open(p,"r",encoding="utf-8") as h: d=json.load(h)
        except Exception: continue
        n += 1
        c = d.get("config")
        if isinstance(c, dict):
            for k in c: confc[k]+=1
            for k in ["model_num_parameters","model_sha","model_revision","model_name","model_args","model_dtype"]:
                if k not in c: conf_missing[k]+=1
        else:
            conf_missing["<no config dict>"] += 1
        if "leaderboard_ifeval" not in d.get("results",{}): old.append((Path(dirpath).name, f, sorted(d.get("results",{}).keys())[:6]))
print("parseable:", n)
print("config keys:")
for k,v in sorted(confc.items()): print(f"  {v:5d}  {k}")
print()
print("missing among parseable:", dict(conf_missing))
print()
print("files lacking leaderboard_ifeval:", len(old))
for o in old[:5]: print("  ", o)
print()
print("samples of config (first 2 parseable):")
cnt=0
for dirpath, _, files in os.walk(ext(root)):
    for f in sorted(x for x in files if x.lower().endswith(".json")):
        p = Path(dirpath)/f
        try:
            with open(p,"r",encoding="utf-8") as h: d=json.load(h)
        except Exception: continue
        print("  ", Path(dirpath).name, sorted(d.get("config",{}).items())[:20])
        cnt+=1
        break
    if cnt>=2: break
