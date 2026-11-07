import io

P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

anchor = "→ ~~R103（attn 一支结案：）~~"
assert s.count(anchor) == 1, s.count(anchor)
add = "→ **R105（新，`P479`：把 93 处 `STRATA_HIP_GFX906` 分成硬件事实 / 假设 / workaround 三类，零停机、探针法）** " + anchor
s = s.replace(anchor, add, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("R105 inserted:", io.open(P, encoding="utf-8").read().count("R105"))
