#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claim_homes.py -- W1035：一条结论能不能被下一个人「按词」找到。

问题（实测过两次）：
  · `P408` 最初是「有观测、没编号」→ 补号后才被当账认；
  · §9 的 decode 归因寄居在 `P265` 第 10 列，按 `decode 不稳` 检索账本 **0 命中**——
    数字全在，但要先知道它挂在「--pool-workers」这条参数下才找得到。

做法（不加新文件，只给账本加第 11 列）：
  每条账本行的第 11 列写成  `KW:词1|词2|...`，由作者声明「下一轮该按哪些词搜到这条」。
  门只查一件事：**声明的每个词，必须真的出现在这一行自己的文本里**（标题 + 备注 + 第 10 列）。
  词不在行里，就说明这行没有按那个说法写下来 ⇒ 下一个人按那个词搜不到 ⇒ 当场红。

三条附加判据（防作弊）：
  A. 本轮每行都必须有 `KW:`，且 >= 2 个词（一个词太容易被随手糊过去）。
  B. 词长 >= 3 字符；纯数字或 `166`/`配置` 这类「满账本都是」的词直接拒（>25 行命中即拒）。
  C. 本轮没有任何账本行 ⇒ FAIL（防止"没写就没事"的空转）。

用法：
  python tools/claim_homes.py                 # 用 HANDOFF 的当前轮次
  python tools/claim_homes.py --round W1035
  python tools/claim_homes.py --self-test     # 三条负向：无 KW / 词不在行里 / 词太泛
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
HANDOFF = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")

MIN_TERM = 3
GENERIC_LIMIT = 25          # 一个词命中超过这么多行，就不是检索键


def rows():
    out = []
    for ln in io.open(PROG, encoding="utf-8").read().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        out.append(ln.split("\t"))
    return out


def current_round():
    try:
        h = io.open(HANDOFF, encoding="utf-8", errors="replace").read()
        m = re.search(r"^> SNAPSHOT:.*?\bround=(W\d{4})", h, re.M)
        return m.group(1) if m else ""
    except OSError:
        return ""


def check(round_id=None):
    rid = round_id or current_round()
    all_rows = rows()
    fails, info = [], []
    if not rid:
        return ["无法确定本轮轮次（HANDOFF 里没有 SNAPSHOT round=）"], []
    mine = [f for f in all_rows if len(f) > 3 and f[3] == rid]
    if not mine:
        return ["本轮（%s）在账本里没有任何行 —— 结论无处可查" % rid], []
    for f in mine:
        pid = f[1]
        body = " ".join([f[2]] + f[8:10])   # 标题 + 备注 + 第10列；**不含第11列 KW 自身**
        kw = f[10].strip() if len(f) > 10 else ""
        if not kw:
            fails.append("%s: 缺第 11 列 KW:（没人声明该按什么词搜到它）" % pid)
            continue
        if not kw.startswith("KW:"):
            fails.append("%s: 第 11 列必须以 `KW:` 开头，实际 `%s`" % (pid, kw[:24]))
            continue
        terms = [t.strip() for t in kw[3:].split("|") if t.strip()]
        if len(terms) < 2:
            fails.append("%s: 只声明了 %d 个检索词（要 >=2）" % (pid, len(terms)))
        for t in terms:
            if len(t) < MIN_TERM:
                fails.append("%s: 检索词 `%s` 太短（>=%d 字符）" % (pid, t, MIN_TERM))
                continue
            spread = sum(1 for g in all_rows if len(g) > 1 and t in "\t".join(g))
            if spread > GENERIC_LIMIT:
                fails.append("%s: 检索词 `%s` 太泛（全账本 %d 行都有，不是检索键）" % (pid, t, spread))
                continue
            if t not in body:
                fails.append("%s: 声明了 `%s`，但本行文本里没有这个词（下一个人按它搜不到）" % (pid, t))
        info.append("%s %s" % (pid, ",".join(terms[:4])))
    return fails, info


def self_test():
    """三条负向用例，直接对 check 的判据函数体做，不碰真文件。"""
    cases = []

    def fake(pid, note, kw):
        f = ["B8工程", pid, "标题占位", "W9999", "count", "1", "1", "DONE", note]
        if kw is not None:
            f.append("")
            f.append(kw)
        return f

    # 用真账本当背景，但把「本轮行」换成伪行
    backup_rows = rows()
    try:
        import builtins
        for label, r, want_fail in (
            ("无 KW 列", fake("PX1", "结论写在备注里", None), True),
            ("KW 词不在行内", fake("PX2", "备注只写了 A 说法", "KW:A 说法|完全没提的词"), True),
            ("KW 太泛", fake("PX3", "166 配置 166 配置", "KW:166|配置"), True),
            ("KW 正常", fake("PX4", "decode 不稳 与 corr 0.49", "KW:decode 不稳|corr 0.49"), False),
        ):
            # 临时把 PROG 指向一份只含该行的临时文件
            tmp = os.path.join(ROOT, ".workbuddy", "_claim_selftest.tsv")
            os.makedirs(os.path.dirname(tmp), exist_ok=True)
            with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\t".join(r) + "\n")
            global PROG
            keep, PROG = PROG, tmp
            # 需要 25 行以上的背景才能判"太泛"，临时补一些
            with io.open(tmp, "a", encoding="utf-8", newline="\n") as fh:
                for i in range(30):
                    fh.write("B9\tB%02d\t占位 %d\tW9998\tcount\t1\t1\tDONE\t166 配置\t\tKW:166|配置\n" % (i, i))
            fails, _ = check("W9999")
            PROG = keep
            got = bool(fails)
            cases.append((label, want_fail, got, fails[:2]))
    finally:
        PROG = PROG
    bad = 0
    for label, want, got, sample in cases:
        ok = (want == got)
        bad += 0 if ok else 1
        print("%s  %-18s want_fail=%-5s got=%-5s %s" % ("PASS" if ok else "FAIL", label, want, got, sample))
    print("CLAIM_HOMES SELF_TEST: %s (%d/%d)" % ("PASS" if not bad else "FAIL", len(cases) - bad, len(cases)))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    fails, info = check(a.round)
    rid = a.round or current_round()
    for x in info:
        pass
    if fails:
        print("CLAIM_HOMES: FAIL (%d) round=%s" % (len(fails), rid))
        for x in fails[:20]:
            print("  - " + x)
        return 1
    print("CLAIM_HOMES: PASS round=%s rows=%d 全部声明词都能在本行文本里找到" % (rid, len(info)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
