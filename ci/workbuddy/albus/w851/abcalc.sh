set +e
cat > /tmp/abc.py <<'PY'
import io, re, glob, statistics
f = sorted(glob.glob("/home/albus/strata166/data/w851_abtbl2_*.txt"))[-1]
arms, cur = {}, None
pat = re.compile(r"prompt (\d+) tokens = 0 reused \+ \d+ read in (\d+) ms")
for ln in io.open(f, encoding="utf-8", errors="replace"):
    m = re.match(r"^===== ARM (\S+)", ln)
    if m:
        cur = m.group(1); arms[cur] = []; continue
    m = pat.search(ln)
    if m and cur:
        arms[cur].append((int(m.group(1)), int(m.group(2))))
print("帧数:", {k: len(v) for k, v in arms.items()})
A, B, A2, B2 = arms.get("A", []), arms.get("B", []), arms.get("A2", []), arms.get("B2", [])
print("\n  tok    A(旧)  A2(旧)   B(新)  B2(新)   旧均值   新均值     Δ")
rows = []
for i in range(min(len(A), len(B), len(A2), len(B2))):
    ta, da = A[i]; tb, db = B[i]; ta2, da2 = A2[i]; tb2, db2 = B2[i]
    if not (ta == tb == ta2 == tb2):
        print("  !! 第 %d 帧尺寸不一致: %d %d %d %d" % (i, ta, tb, ta2, tb2)); continue
    o = (da + da2) / 2; n = (db + db2) / 2
    rows.append((ta, o, n))
    print("  %-5d %6d %6d  %6d %6d  %7.1f  %7.1f  %+6.1f%%" % (ta, da, da2, db, db2, o, n, (n/o-1)*100))
# 分组：<1024 (小桶) vs >=1024 (对照)
small = [r for r in rows if r[0] < 1024]
big = [r for r in rows if r[0] >= 1024]
def agg(name, rs):
    if not rs: return
    o = sum(r[1] for r in rs)/len(rs); n = sum(r[2] for r in rs)/len(rs)
    print("  %-22s 旧 %.1f ms -> 新 %.1f ms   %+.1f%%  (n=%d)" % (name, o, n, (n/o-1)*100, len(rs)))
print()
agg("<1024 tok（256/512 桶）", small)
agg(">=1024 tok（对照，1024 桶）", big)
PY
python3 /tmp/abc.py
