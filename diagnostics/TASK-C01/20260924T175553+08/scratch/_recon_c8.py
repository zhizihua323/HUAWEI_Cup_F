import json, os, sys, collections
from pathlib import Path

def ext(p):
    p = str(Path(p).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p

root = Path(r"C:\Users\28762\Desktop\The Huawei Cup National Postgraduate Mathematical Modeling Contest\GPT_Workspace\F题\real_attachments\C_efficiency_evolution\detailed_results")
n=0; bad=[]; keyc=collections.Counter(); samples=[]
for dirpath, dirnames, files in os.walk(ext(dirname:=root)):
    js = sorted(f for f in files if f.lower().endswith(".json"))
    if not js: continue
    for f in js:
        n+=1
        p = Path(dirpath)/f
        try:
            with open(p, "r", encoding="utf-8") as h: d=json.load(h)
            keyc.update(d.keys())
            if len(samples)<3: samples.append((str(p), sorted(d.keys())))
        except Exception as e:
            bad.append((str(p), type(e).__name__, str(e)[:120]))
print("files:", n)
print("bad:", len(bad))
for b in bad: print("BAD", b[0].replace(str(root),"..."), b[1], b[2])
print("top-level keys count:")
for k,v in keyc.most_common(40): print("  ", k, v)
print("samples:")
for s in samples: print("  ", s[0].replace(str(root),"<root>"), s[1])
