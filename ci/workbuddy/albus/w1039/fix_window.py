import io

p = "albus/w1039/window.sh"
s = io.open(p, encoding="utf-8").read()

old = """env = d.get("env") or {}
for k in list(env):
    if k.startswith("STRATA_GFX906_"):
        del env[k]
"""
new = """env = d.get("env") or {}
# only the four OPT switches are ours; STRATA_GFX906_TUNED must survive (it is part of the baseline)
for k in ("STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
          "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP",
          "STRATA_GFX906_Q8_GATHER8"):
    env.pop(k, None)
"""
assert old in s, "anchor missing"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("apply_cfg now only clears the four OPT keys")
