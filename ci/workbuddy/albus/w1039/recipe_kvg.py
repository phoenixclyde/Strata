import io

P = "deploy/REBUILD_RECIPE.tsv"
s = io.open(P, encoding="utf-8").read()
line = ("strata-0.1.57-kvg\ta85743d7f554159e8ac1e2d432d2e5ea\t43214976\tgfx906/lcpp-k10 @ af797b90\t"
        "b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5\t4c1004c49221b07c3b8108977e3d1991fc9f45cc\t"
        "build-masterp（/src=pr/k10, /llama.cpp=tmp/w1037/llama-master）\t"
        "W1039/R104 候选：gfx906 的 HIP VMM 路径（vmm.cpp 两处条件改 OR）+ STRATA_KV_GROW=1；`nm -D` 有 4 个 VMM 符号、在产 b12180 为 0；**未装机**，见 P474/P478\n")
assert "strata-0.1.57-kvg" not in s
if not s.endswith("\n"):
    s += "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(s + line)
print("recipe row added for kvg")
