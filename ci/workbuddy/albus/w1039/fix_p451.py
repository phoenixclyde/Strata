import io

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
i = s.find("\tP451\t")
assert i > 0
start = s.rfind("\n", 0, i) + 1
j = s.find("\n", i)
row = s[start:j]
f = row.split("\t")
print("cols", len(f), "| status", f[7], "| last", f[-1][:60])

add = " **W1041 数值门判否（P453）**：KL 0.04130（阈值 0.0139，3.0 倍）、top-1 93.55%（阈值 99%）⇒ 速度收益不成立，不装机。"
if len(f) == 11:
    kw = f[10]
    bad = kw[len("KW:warp-per-group|1982"):]
    f[10] = "KW:warp-per-group|1982"
    if "W1041 数值门判否" not in f[8]:
        f[8] = f[8].rstrip() + add
    new_row = "\t".join(f)
    s = s[:start] + new_row + s[j:]
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("P451 repaired; kw =", f[10], "| dropped junk chars:", len(bad))
else:
    print("unexpected column count", len(f))
