# -*- coding: utf-8 -*-
"""通用 KL 配对：kl_pair.py <dir> <tpl> <off-arms> <on-arms>
   tpl = 文件名模板，含 %s 作为臂名，例如 "w805_logpos_%s.tsv"
   off 通常是确定性基线（一条即可）；on 可以多条（同配置两遍 => 底噪）
输出每一对的 KL 均值/中位/p90/p99/argmax/KL=0 占比，并把「变更对」与「同配置对」并列。
"""
import io, itertools, math, os, statistics as st, sys

D, TPL = sys.argv[1], sys.argv[2]
OFF = sys.argv[3].split(",")
ON = sys.argv[4].split(",")


def load(a):
    p = os.path.join(D, TPL % a)
    if not os.path.isfile(p):
        return None
    rows = {}
    for line in io.open(p, encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if len(c) < 9:
            continue
        tk = {}
        for x in c[8:]:
            if ":" in x:
                i, v = x.split(":", 1)
                tk[int(i)] = float(v)
        rows[int(c[0])] = {"tgt": int(c[1]), "lp": float(c[2]), "top": int(c[3]), "tk": tk}
    return rows


def kl(P, Q):
    sp, sq = set(P["tk"]), set(Q["tk"])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P["tk"][t]) for t in sp}
    qq = {t: math.exp(Q["tk"][t]) for t in sq}
    rq = max(0.0, 1.0 - sum(qq.values()))
    miss = sp - sq
    sm = sum(pp[t] for t in miss)
    v = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        q = qq[t] if t in sq else (rq * pp[t] / sm if sm > 0 else rq / max(1, len(miss)))
        v += p * math.log(p / max(q, 1e-300))
    return v


arms = {}
for a in OFF + ON:
    z = load(a)
    if z is None:
        print("ARM %s MISSING" % a)
    else:
        arms[a] = z
        print("ARM %-2s rows=%-5d uniq=%-5d pos[%d..%d]" % (a, len(z), len(z), min(z), max(z)))
pos = sorted(set.intersection(*[set(v) for v in arms.values()])) if arms else []
print("配对位置 n=%d\n" % len(pos))
print("%-10s %-8s %-6s %-10s %-10s %-9s %-9s %-8s %-7s" %
      ("对", "类型", "n", "KL均值", "KL中位", "p90", "p99", "argmax", "KL=0"))
onon, offon = [], []
for f, g in itertools.combinations(list(arms), 2):
    if (f in OFF) == (g in OFF):
        kind = "on-vs-on" if f in ON else "off-vs-off"
    else:
        kind = "off-vs-on"
    v, ag = [], 0
    for p in pos:
        if arms[f][p]["tgt"] != arms[g][p]["tgt"]:
            continue
        z = kl(arms[f][p], arms[g][p])
        if z is None:
            continue
        v.append(z)
        ag += 1 if arms[f][p]["top"] == arms[g][p]["top"] else 0
    if not v:
        continue
    sv = sorted(v)
    rec = {"mean": st.mean(v), "med": st.median(v), "n": len(v),
           "argmax": 100.0 * ag / len(v), "zero": 100.0 * sum(1 for x in v if x == 0) / len(v)}
    if kind == "on-vs-on":
        onon.append(rec)
    elif kind == "off-vs-on":
        offon.append(rec)
    print("%-10s %-8s %-6d %-10.6f %-10.6f %-9.5f %-9.4f %-8.2f %-7.1f" %
          ("%s||%s" % (f, g), kind, rec["n"], rec["mean"], rec["med"],
           sv[int(.9 * len(sv))], sv[int(.99 * len(sv))], rec["argmax"], rec["zero"]))

if onon and offon:
    print("\n== 把「对」当样本 ==")
    for tag, grp in (("变更（off-vs-on）", offon), ("同配置（on-vs-on）", onon)):
        ms = [r["mean"] for r in grp]
        md = [r["med"] for r in grp]
        print("  %-16s n_pairs=%d  KL均值 %.6f..%.6f（中位 %.6f）  KL中位 %.6f..%.6f"
              % (tag, len(grp), min(ms), max(ms), st.median(ms), min(md), max(md)))
    mo, mu = [r["mean"] for r in offon], [r["mean"] for r in onon]
    print("  区间重叠: %s" % ("是 => 变更落在同配置浮动内" if min(mo) <= max(mu) else "否"))
