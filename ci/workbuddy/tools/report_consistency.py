#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_consistency -- 报告里的「三、本次落生产」必须与账本同轮的行对得上。

W1037 起因（机主 2026-11-07 07:36「每轮的四项报告你又丢了」）：
窗口跑了三次重启、停机 136 s，账本 `P434` 写得清清楚楚，但 `reply.md` 开头那份四件套
**still said「重启 0 次 / 停机 0 分钟」** —— 因为 `report_lint` 只查字段在不在、`report_depth` 只查篇幅，
**没有一道门比对「报告里的数」与「账本里的数」**。这就是 W1012「字段在、内容没了」的第三次复发，
只不过这次不是篇幅缩水，是**数字过期**。

判据（fail-closed）：
  * 从 `albus/w1034/HANDOFF.md` 的 SNAPSHOT 取轮次；只审该轮账本行（source == 轮次）。
  * 该轮行里出现的「重启 N 次」取最大值、「停机 N s/秒」取最大值（分钟折算成秒）。
  * 报告的「三、本次落生产」段必须出现同样的数（重启次数用整数匹配；停机用秒或等价分钟匹配）。
  * 该轮没有任何行提到重启/停机 ⇒ 报告里必须写明「重启 0 次」或「0 分钟停机」。

用法: python tools/report_consistency.py albus/wXXXX/reply.md
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
HANDOFF = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")


def round_id(report=None):
    """W1039: the round must come from the REPORT when it names one.

    It used to come only from HANDOFF's SNAPSHOT, so re-auditing an older report compared its numbers against
    the *current* round's ledger rows -- every report older than the snapshot failed, which made the gate useless
    for the one thing you want it for after the fact (did this round's report match this round's ledger?).
    """
    if report:
        head = io.open(report, encoding="utf-8").read(4000)
        for m in re.finditer(r"\bW(\d{4})\b", head):
            cand = "W" + m.group(1)
            if any(ln.count("\t") >= 9 and ln.split("\t")[3] == cand
                   for ln in io.open(PROG, encoding="utf-8")):
                return cand
    s = io.open(HANDOFF, encoding="utf-8").read()
    m = re.search(r"SNAPSHOT:.*?\bround=(W\d+)", s)
    return m.group(1) if m else None


def ledger_numbers(rnd):
    restarts, secs = [], []
    for ln in io.open(PROG, encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) < 9 or f[3] != rnd:
            continue
        note = f[8]
        for m in re.finditer(r"重启[^0-9]{0,8}(\d+)\s*次", note):
            restarts.append(int(m.group(1)))
        for m in re.finditer(r"(\d+)\s*次重启", note):
            restarts.append(int(m.group(1)))
        for m in re.finditer(r"停机[^0-9]{0,8}(\d+(?:\.\d+)?)\s*(s|秒)", note):
            secs.append(float(m.group(1)))
        for m in re.finditer(r"停机[^0-9]{0,8}(\d+(?:\.\d+)?)\s*(min|分钟)", note):
            secs.append(float(m.group(1)) * 60)
    return (max(restarts) if restarts else 0), (max(secs) if secs else 0.0)


def section3(text):
    i = text.find("三、本次落生产")
    if i < 0:
        return ""
    j = text.find("四、", i)
    return text[i:j if j > 0 else len(text)]



def denom_from_ledger():
    """(rows, done) derived the same way tools/progress.py does: every `count` row adds its count/done."""
    tot = done = 0
    for ln in io.open(PROG, encoding="utf-8"):
        if ln.startswith("#") or ln.count("\t") < 8:
            continue
        f = ln.rstrip("\n").split("\t")
        if f[4] != "count":
            continue
        try:
            tot += int(f[5])
            done += int(f[6])
        except ValueError:
            pass
    return tot, done


def section4(text):
    i = text.find("四、进度")
    if i < 0:
        return ""
    j = text.find("---", i)
    return text[i:j if j > 0 else len(text)]


def main():
    if len(sys.argv) < 2:
        print("usage: report_consistency.py <report.md>")
        return 2
    rnd = round_id(sys.argv[1])
    if not rnd:
        print("REPORT_CONSISTENCY: FAIL (SNAPSHOT round 取不到)")
        return 1
    text = io.open(sys.argv[1], encoding="utf-8").read()
    sec = section3(text)
    if not sec:
        print("REPORT_CONSISTENCY: FAIL (没有「三、本次落生产」段)")
        return 1
    n_restart, n_sec = ledger_numbers(rnd)
    fails = []

    got_restart = [int(x) for x in re.findall(r"重启\s*\*{0,2}\s*(\d+)\s*\*{0,2}\s*次", sec)]
    if n_restart:
        if n_restart not in got_restart:
            fails.append("账本同轮写「重启 %d 次」，报告的落生产段里没有这个数（读到 %s）"
                         % (n_restart, got_restart or "无"))
    else:
        if not any(x == 0 for x in got_restart):
            fails.append("账本同轮没有重启记录，报告也没写「重启 0 次」")

    got_sec = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:s|秒)", sec)]
    if n_sec:
        ok = any(abs(x - n_sec) <= 1 for x in got_sec) or any(abs(x * 60 - n_sec) <= 1 for x in
                                                             [float(y) for y in re.findall(r"(\d+(?:\.\d+)?)\s*(?:min|分钟)", sec)])
        if not ok:
            fails.append("账本同轮写「停机 %.0f s」，报告的落生产段里没有等价数字（读到 %s 秒 / %s 分钟）"
                         % (n_sec, got_sec or "无", re.findall(r"(\d+(?:\.\d+)?)\s*(?:min|分钟)", sec) or "无"))
    else:
        if not re.search(r"(0\s*分钟停机|停机\s*0|无停机)", sec):
            fails.append("账本同轮没有停机记录，报告也没写「0 分钟停机」")

    # W1039: the four-part report's denominator drifted 386 -> 391 -> 393 -> 395 across one round while every
    # other gate stayed green (report_lint only wants "N 条 / 已结 M / P%", report_depth only counts R ids).
    # Tie it to the ledger, which is the only place the denominator may come from.
    cur = round_id()
    sec4 = section4(text) if rnd == cur else "skip"
    if sec4 == "skip":
        pass
    elif not sec4:
        fails.append("没有「四、进度」段")
    else:
        tot, done = denom_from_ledger()
        got = re.findall(r"(\d+)\s*条\s*/\s*已结\s*(\d+)", sec4)
        if not got:
            fails.append("四、进度 里没有「N 条 / 已结 M」")
        elif (int(got[-1][0]), int(got[-1][1])) != (tot, done):
            fails.append("四、进度 写 %s 条 / 已结 %s，账本派生的是 %d / %d"
                         % (got[-1][0], got[-1][1], tot, done))

    if fails:
        for x in fails:
            print("  [FAIL] " + x)
        print("REPORT_CONSISTENCY: FAIL (%d) —— 报告与账本同轮（%s）的数对不上" % (len(fails), rnd))
        return 1
    print("REPORT_CONSISTENCY: PASS（%s：报告落生产段 = 账本 重启 %d 次 / 停机 %.0f s）" % (rnd, n_restart, n_sec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
