import json, re, os, subprocess

SRC = "/home/albus/strata166/src0271/src"
INC = "/home/albus/strata166/src0271/include"
CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"

d = json.load(open(CFG))
envs = sorted(d["env"])

# 关键词：源码里声明"会改输出/逐位相同/近似"的措辞
KW = re.compile(
    r"changes the output|change the output|bitwise|bit-exact|identical|"
    r"exact same|same answer|approximat|rounding|renormal|lower precision|"
    r"not the same|differs|different (?:answer|result|value)",
    re.I,
)

hits = {}
for root in (SRC, INC):
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith((".cpp", ".cu", ".hpp", ".h")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except Exception:
                continue
            for i, ln in enumerate(lines):
                if not ln.lstrip().startswith(("//", "/*", "*", "#")) and "//" not in ln:
                    pass
                for e in envs:
                    name = e.replace("STRATA_", "")
                    if name in ln and KW.search(ln) and "//" in ln:
                        hits.setdefault(e, []).append(
                            (p.replace("/home/albus/strata166/src0271/", ""), i + 1,
                             ln.strip()[:230])
                        )

for e in envs:
    print("=" * 10, e)
    hs = hits.get(e, [])
    if not hs:
        print("   (没找到带判据措辞的注释)")
        continue
    seen = set()
    for path, ln_no, txt in hs:
        k = txt[:80]
        if k in seen:
            continue
        seen.add(k)
        print("   %s:%d" % (path, ln_no))
        print("      " + txt)
