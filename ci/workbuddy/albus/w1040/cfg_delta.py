#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: build the exact config delta (exe + --kv-grow) from the live 166 config, and prove the
round-trip is byte-stable (otherwise a restore can never be byte-exact)."""
import io, json, os, sys, hashlib
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1040"
LIVE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
BASE = os.path.join(W, "cfg_base.json")
NEW = os.path.join(W, "cfg_new.json")

rc, raw, err = _sshutil.run_remote("cat " + LIVE, timeout=60)
assert rc == 0, err
data = raw.encode("utf-8") if isinstance(raw, str) else raw
print("live bytes", len(data), "md5", hashlib.md5(data).hexdigest())

txt = data.decode("utf-8")
d = json.loads(txt)
rt = json.dumps(d, ensure_ascii=False, indent=1)
print("round-trip identical:", rt == txt, "| round-trip md5", hashlib.md5(rt.encode()).hexdigest())
if rt != txt:
    print("  (diff head)", [i for i in range(min(len(rt), len(txt))) if rt[i] != txt[i]][:5], "len", len(rt), len(txt))
io.open(BASE, "w", encoding="utf-8", newline="\n").write(rt + ("\n" if txt.endswith("\n") else ""))

# --- the sanctioned delta
d2 = json.loads(rt)
assert d2["exe"] == "/data/bin/strata-0.1.57-b12180", d2["exe"]
d2["exe"] = "/data/bin/strata-0.1.57-kvg"
assert "--kv-grow" not in d2["args"]
d2["args"] = d2["args"] + ["--kv-grow"]
assert "STRATA_KV_GROW" not in (d2.get("env") or {})
body = json.dumps(d2, ensure_ascii=False, indent=1) + ("\n" if txt.endswith("\n") else "")
io.open(NEW, "w", encoding="utf-8", newline="\n").write(body)
print("new  bytes", len(body.encode()), "md5", hashlib.md5(body.encode()).hexdigest())
print("exe:", d2["exe"], "| args", len(d2["args"]), "| env", len(d2["env"]))

# --- what exactly changed
a, b = json.loads(rt), d2
print("\nkeys:", sorted(set(a) | set(b)))
print("exe:", a["exe"], "->", b["exe"])
print("args added:", [x for x in b["args"] if x not in a["args"]], "| removed:", [x for x in a["args"] if x not in b["args"]])
print("env same:", a["env"] == b["env"])
