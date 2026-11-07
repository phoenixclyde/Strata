"""台账对账：登记表里的"未结项" 是否都在 PROGRESS.tsv 里被认领。

用法: python tools/ledger_audit.py
退出码: 0 = 全部认领；1 = 有欠账（每轮收工前必须 0）
"""
import io
import os
import re
import sys

ROOT = "D:/workbuddy_space/strata_ws"
REG = ROOT + "/deploy/params/PARAM_REGISTER.tsv"
PROG = ROOT + "/deploy/PROGRESS.tsv"
OPEN_STATUS = {"CANDIDATE", "PENDING", "DEFERRED", "UNRESOLVED", "PARTIAL", "PROPOSED"}


def read_tsv(p, key):
    lines = [l for l in io.open(p, encoding="utf-8-sig").read().splitlines() if l.strip() and not l.startswith("#")]
    hdr = lines[0].split("\t")
    out = []
    for l in lines[1:]:
        f = l.split("\t")
        if len(f) < len(hdr):
            f += [""] * (len(hdr) - len(f))
        out.append(dict(zip(hdr, f)))
    return out


def main():
    reg = read_tsv(REG, "id")
    prog = read_tsv(PROG, "block")
    refs = set()
    for r in prog:
        for t in re.split(r"[,/ ]+", r.get("ref", "")):
            t = t.strip()
            if t:
                refs.add(t)
    openp = [r for r in reg if r["status"] in OPEN_STATUS]
    un = [r for r in openp if r["id"] not in refs]
    print("登记表未结 %d 条；PROGRESS 已认领 %d 条；**欠账 %d 条**"
          % (len(openp), len(openp) - len(un), len(un)))
    for r in un:
        print("  欠账 %-5s %-10s %s" % (r["id"], r["status"], r["name"][:60]))

    # 反向：PROGRESS 里引用了登记表不存在的 P 号
    bad = [t for t in refs if t.startswith("P") and t[1:].isdigit()
           and t not in {r["id"] for r in reg}]
    if bad:
        print("  !! PROGRESS 引用了不存在的 P 号: %s" % ", ".join(sorted(bad)))

    # 轻量：dsec 里有「下一步/待办」标题、但该文件从未在任何账本行出现
    srcs = " ".join(r.get("source", "") for r in prog)
    lonely = []
    for fn in os.listdir(ROOT + "/deploy"):
        if not fn.endswith(".md") or ".bak" in fn:
            continue
        txt = io.open(ROOT + "/deploy/" + fn, encoding="utf-8", errors="replace").read()
        if re.search(r"(已冻结|SUPERSEDED|已被取代)", txt[:600]):
            continue                                  # 历史件，不算欠账
        if re.search(r"^#+\s*(下一步|待办|后续|TODO)", txt, re.M) and fn.split(".")[0] not in srcs:
            lonely.append(fn)
    if lonely:
        print("  提示：以下文档有「下一步/待办」段但未被账本引用（人工判断是否已废弃）：")
        for f in sorted(lonely)[:12]:
            print("    - " + f)
    return 1 if un or bad else 0


if __name__ == "__main__":
    sys.exit(main())
