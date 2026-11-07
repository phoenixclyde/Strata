import io, re, sys
def load(p):
    rows = {}
    ver = None
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        ln = ln.split("#")[0].strip()
        if not ln: continue
        f = ln.split()
        if f[0] == "STRATA_ROCBLAS_TUNING_V1":
            ver = f[2]; continue
        # f16o N K ldy T solution
        rows[(int(f[1]), int(f[2]), int(f[3]), int(f[4]))] = f[5]
    return ver, rows

D = "/home/albus/strata166/data/"
v57, t57 = load(D + "gfx906-rocblas-5.7.0.txt")
v55n, t55n = load(D + "gfx906-rocblas-5.5.0-6b.txt")
v55o, t55o = load(D + "gfx906-rocblas-5.5.0.txt")

print("版本: 5.7新=%s  5.5新=%s  5.5旧=%s" % (v57, v55n, v55o))
print("行数: 5.7新=%d  5.5新=%d  5.5旧=%d" % (len(t57), len(t55n), len(t55o)))

def cmp(a, b, na, nb, only_shared=True):
    keys = set(a) & set(b) if only_shared else set(a) | set(b)
    both_def = both_tun = conf = 0
    diff = []
    for k in sorted(keys):
        va, vb = a.get(k), b.get(k)
        if va is None or vb is None:
            diff.append((k, va, vb, "only-one")); continue
        da, db = (va == "default"), (vb == "default")
        if da and db: both_def += 1
        elif not da and not db: both_tun += 1
        else:
            conf += 1; diff.append((k, va, vb, "verdict-flip"))
    print("\n== %s vs %s ==  共同行 %d" % (na, nb, len(keys)))
    print("   两边都 default : %d" % both_def)
    print("   两边都有解     : %d" % both_tun)
    print("   判定相反       : %d" % conf)
    for k, va, vb, why in diff[:12]:
        print("     N=%d K=%d T=%d  %s vs %s  (%s)" % (k[0], k[1], k[3], va, vb, why))
    # 解索引是否相同（不同 build 索引不同，正常）
    same_idx = sum(1 for k in keys if a.get(k) and b.get(k) and a[k] == b[k] and a[k] != "default")
    print("   解索引相同     : %d" % same_idx)

cmp(t57, t55n, "5.7新", "5.5新")
cmp(t55n, t55o, "5.5新(6桶)", "5.5旧(4桶)")

print("\n== 5.5 新表里 T=256/512 的 28 行 == ")
for k in sorted(t55n):
    if k[3] in (256, 512):
        print("   N=%-6d K=%-6d T=%-4d %s" % (k[0], k[1], k[3], t55n[k]))
