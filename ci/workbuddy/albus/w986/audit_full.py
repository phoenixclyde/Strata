# -*- coding: utf-8 -*-
"""全面审计：轮次面 + 参数册-生产一致性。"""
import io, os, re, json, glob

BASE = "D:/workbuddy_space/strata_ws/albus"
REG = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
LIVE = json.load(open("D:/workbuddy_space/strata_ws/albus/w985/live.json"))

print("=" * 96)
print("A. 轮次面：W952–W985（31 轮）")
print("=" * 96)
rows = []
for d in sorted(glob.glob(BASE + "/w9*"), key=lambda x: int(os.path.basename(x)[1:])):
    n = int(os.path.basename(d)[1:])
    if n < 952:
        continue
    files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
    txt = ""
    for f in files:
        try:
            txt += io.open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
        except Exception:
            pass
    has_verdict = bool(re.search(r"判据|结论|总判|采纳|判否|REJECT|ROLLBACK", txt))
    has_ledger = bool(re.search(r"PROGRESS|台账|PARAM_REGISTER", txt))
    has_prod = bool(re.search(r"docker restart|cfg_apply|config|部署|上线", txt))
    neg = bool(re.search(r"判否|REJECT|ROLLBACK|回滚|DONE_NEG|不采纳", txt))
    rows.append((n, len(files), has_verdict, has_ledger, has_prod, neg))

print("%-6s %5s %6s %6s %6s %6s   %s" % ("round", "files", "结论", "落账", "动生产", "含负面", "标记"))
for n, f, v, l, p, g in rows:
    flag = ""
    if v and not l:
        flag += "结论未落账 "
    if p and not l:
        flag += "动过生产未记账 "
    if g and not l:
        flag += "负面未记 "
    print("%-6s %5d %6s %6s %6s %6s   %s" % ("W%d" % n, f, "Y" if v else "-", "Y" if l else "-",
                                             "Y" if p else "-", "Y" if g else "-", flag or "ok"))

print()
print("=" * 96)
print("B. 参数册 vs 生产：ADOPTED 但值不一致 / 用了但未登记")
print("=" * 96)
reg = [l.split("\t") for l in io.open(REG, encoding="utf-8", errors="replace").read().splitlines()[1:]]
live_args = {}
a = LIVE["args"]
for i, t in enumerate(a):
    if t.startswith("--"):
        live_args[t] = a[i + 1] if (i + 1 < len(a) and not a[i + 1].startswith("--")) else True
live_env = LIVE["env"]

for r in reg:
    if len(r) < 6:
        continue
    pid, scope, name, val, status = r[0], r[1], r[2], r[3], r[5]
    flag = name.split("=")[0].strip()
    if status == "ADOPTED":
        if scope == "CLI" and flag.startswith("--"):
            live = live_args.get(flag)
            if live is None:
                print("  [ADOPTED 但生产没有] %-6s %-26s 册=%s" % (pid, flag, val[:24]))
            elif str(live) != str(val).strip() and val not in ("(flag)", "-"):
                print("  [ADOPTED 值不一致]   %-6s %-26s 册=%s 产=%s" % (pid, flag, val[:24], live))
        elif scope == "ENV":
            k = name.split("=")[0].strip()
            live = live_env.get(k)
            if live is not None and str(live) != str(val).strip():
                print("  [ADOPTED env 值不一致] %-6s %-26s 册=%s 产=%s" % (pid, k, val[:24], live))
            elif live is None:
                print("  [ADOPTED env 生产没有] %-6s %-26s 册=%s" % (pid, k, val[:24]))
