import io
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:/workbuddy_space/strata_ws")
DEPLOY = ROOT / "deploy"
CFG = DEPLOY / "tmp" / "prod_config_now.json"
REG = DEPLOY / "params" / "PARAM_REGISTER.tsv"
RX_W = re.compile(r"\bW(\d{3})\b")

cfg = json.loads(CFG.read_text(encoding="utf-8"))
args = cfg["args"]
params = []
i = 0
while i < len(args):
    if args[i].startswith("--"):
        if i + 1 < len(args) and not args[i + 1].startswith("--"):
            params.append((args[i], args[i + 1]))
            i += 2
        else:
            params.append((args[i], "(switch)"))
            i += 1
    else:
        i += 1
params += list(cfg["env"].items())

rows = []
for line in REG.read_text(encoding="utf-8", errors="replace").splitlines():
    f = line.split("\t")
    if len(f) >= 6 and f[0].startswith("P"):
        body = "\t".join(f[2:])
        rows.append({
            "pid": f[0], "name": f[2], "status": f[5], "body": body,
            "ws": sorted({int(x) for x in RX_W.findall(body)}),
        })

used = defaultdict(set)
print("== current params ==")
for key, val in params:
    name = key.lstrip("-")
    hits = [r for r in rows if name and name in r["name"]]
    hits.sort(key=lambda r: max(r["ws"]) if r["ws"] else 0, reverse=True)
    if not hits:
        print(f"{key:34} {str(val)[:18]:20} UNREGISTERED")
        continue
    r = hits[0]
    maxw = max(r["ws"]) if r["ws"] else 0
    print(f"{key:34} {str(val)[:18]:20} {r['pid']:5} {r['status']:12} maxW={maxw:<4} refs={len(r['ws'])}")
    for w in r["ws"]:
        if 700 <= w < 800:
            used[w].add(r["pid"])

print("\n== W7xx docs cited by current params, ranked ==")
for w, pids in sorted(used.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    docs = sorted(DEPLOY.glob(f"W{w}*.md"))
    sz = sum(p.stat().st_size for p in docs)
    print(f"W{w:<4} cited_by={len(pids):2} pids={','.join(sorted(pids)):28} docs={len(docs):2} bytes={sz}")
    for p in docs:
        print(f"      {p.name}")
