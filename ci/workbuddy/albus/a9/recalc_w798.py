"""AUDIT9 重算器：把 W798 的 `decode GPU stages` 逐行解析，按臂/按请求重算相位差。"""
import re, statistics as st, sys, glob, os

KEYS = ["q8+qkv/q-idx gemv", "rec", "out-proj", "shared+quant", "VRAM hits", "waitB", "waitCPU",
        "PCIe grp", "Q:VRAM hits", "attention", "scores+topk"]

def parse_line(ln):
    """返回 dict：GDN 段的 key->val，QSA 段的 'Q:'+key->val，total。"""
    d = {}
    m = re.search(r"total ([0-9.]+) ms/window over (\d+) windows", ln)
    if m:
        d["total"] = float(m.group(1)); d["windows"] = int(m.group(2))
    ln2 = ln.replace("q8+", "qEIGHT+")
    gdn, qsa = ln2.split("| QSA layers:")
    gdn = gdn.split("GDN layers:")[1]
    for seg, pre in ((gdn, ""), (qsa, "Q:")):
        seg = seg.split("total ")[0]
        cur = 0
        for km in re.finditer(r"([0-9]+(?:\.[0-9]+)?)", seg):
            k = seg[cur:km.start()].strip()
            cur = km.end()
            if k:
                d[pre + k.replace("qEIGHT+", "q8+")] = float(km.group(1))
    return d

def load(path):
    arms, cur = {}, None
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"=== ARM (\w+)", ln)
        if m:
            cur = m.group(1); arms.setdefault(cur, []); continue
        if "decode GPU stages" in ln and cur:
            arms[cur].append(parse_line(ln))
    return arms

def med(vals):
    return st.median(vals) if vals else float("nan")

def main(path, base="A", rng=(1, 4)):
    arms = load(path)
    print("文件 %s" % os.path.basename(path))
    for a, rows in arms.items():
        print("  ARM %-2s 阶段行 %d，windows=%s" % (a, len(rows), [r.get("windows") for r in rows]))
    if base not in arms:
        return
    b = arms[base][rng[0]:rng[1]]
    print("\n%-22s %10s %10s %8s" % ("key", "base中位", "arm中位", "Δ%"))
    for a, rows in arms.items():
        if a == base:
            continue
        sel = rows[rng[0]:rng[1]]
        if not sel:
            continue
        print("--- ARM %s (n=%d) ---" % (a, len(sel)))
        for k in KEYS:
            bv = [r[k] for r in b if k in r]
            av = [r[k] for r in sel if k in r]
            if not bv or not av:
                continue
            bm, am = med(bv), med(av)
            print("%-22s %10.2f %10.2f %+7.1f%%" % (k, bm, am, 100.0 * (am - bm) / bm if bm else 0))
        bt = [r["total"] for r in b if "total" in r]
        at = [r["total"] for r in sel if "total" in r]
        if bt and at:
            print("%-22s %10.2f %10.2f %+7.1f%%" % ("total", med(bt), med(at), 100.0 * (med(at) - med(bt)) / med(bt)))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "A")
