import io, json, subprocess, sys, hashlib, shutil

SRC = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
TMP = "/home/albus/strata166/tmp/w1037/cfgtest.json"
SW = ["STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
      "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP", "STRATA_GFX906_Q8_GATHER8"]


def md5(p):
    return hashlib.md5(io.open(p, "rb").read()).hexdigest()


def rewrite(p, exe, kv):
    d = json.load(io.open(p, encoding="utf-8-sig"))
    d["exe"] = exe
    env = d.get("env") or {}
    for k in SW:
        env.pop(k, None)
    for item in kv:
        k, _, v = item.partition("=")
        env[k] = v
    d["env"] = env
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
    return d


shutil.copyfile(SRC, TMP)
base = json.load(io.open(SRC, encoding="utf-8-sig"))
d = rewrite(TMP, "/data/bin/strata-0.1.57-pa1", ["STRATA_GFX906_ATTN_DP4A=1"])
print("keys same:", list(d) == list(base), "| args same:", d["args"] == base["args"],
      "| model:", d["model_name"] == base["model_name"], "| port:", d["port"] == base["port"])
print("exe:", d["exe"], "| env n:", len(d["env"]), "| added:", [k for k in d["env"] if k not in base["env"]])
print("moved env:", {k: (d["env"].get(k), base["env"].get(k)) for k in base["env"] if d["env"].get(k) != base["env"].get(k)})
d2 = rewrite(TMP, "/data/bin/strata-0.1.57-001", [])
print("revert exe:", d2["exe"], "| env n:", len(d2["env"]), "| leftover switches:", [k for k in SW if k in d2["env"]])
print("content-equal to original (semantic):", d2 == base)
