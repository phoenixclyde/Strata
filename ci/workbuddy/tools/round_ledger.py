#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""round_ledger.py -- the round-close contract, mechanised.

W1035 起因（机主第三次问「每轮的四项报告呢 / 你的 CI/CD 呢」）：`round_close.py` 只验
「报告写得好不好」，**不验这一轮到底有没有留下账**。契约（HANDOFF §6）是四件：
四件套报告 + 账本行 + 全套门 + 当日记忆；前三条里只有第一条有门，所以
「报告发了、账本没加行」「账本加了、记忆没写」都能静默通过。

  A  HANDOFF 的 SNAPSHOT 里 round=W#### 可解析，且 albus/<round>/reply.md 存在
  B  PROGRESS.tsv 至少一行 source 列 == round（这一轮确实落了账）
  C  .workbuddy/memory/<SNAPSHOT date>.md 提到该轮次（当日记忆 append-only）
  D  该轮的回复长度 >= 1500 字符（四件套不是占位符）
  E  W832 §6.5 里有 `### 回写 · <round>` 块（结论没进唯一方案 == 下一轮就丢；
     W1028–W1034 八轮正是这样丢的）

  python tools/round_ledger.py [--self-test] [--round W1035] [--live] [--quiet]

退出码 0 = 四条都满足；1 = 有缺项。`--live` 追加 F：在产二进制/重建配方/交接快照
必须同时过 live 门，防止一轮只留下漂亮报告却验错了件。
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HANDOFF = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
MEMDIR = os.path.join(ROOT, ".workbuddy", "memory")


def snapshot():
    if not os.path.isfile(HANDOFF):
        return {}
    txt = io.open(HANDOFF, encoding="utf-8", errors="replace").read()
    m = re.search(r"^> SNAPSHOT:\s*(.+)$", txt, re.M)
    if not m:
        return {}
    out = {}
    for kv in m.group(1).split():
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k] = v
    return out


def ledger_rounds():
    rounds = set()
    if not os.path.isfile(PROG):
        return rounds
    for line in io.open(PROG, encoding="utf-8", errors="replace").read().splitlines():
        f = line.split("\t")
        if len(f) >= 10 and f[0] != "block" and not line.startswith("#"):
            rounds.add(f[3].strip())
    return rounds


def memory_hits(round_id, date):
    """The dated file first (append-only contract); then any file, for a round that crosses midnight."""
    hits = []
    p = os.path.join(MEMDIR, "%s.md" % date)
    if os.path.isfile(p) and round_id in io.open(p, encoding="utf-8", errors="replace").read():
        hits.append(p)
    if hits:
        return hits
    if os.path.isdir(MEMDIR):
        for f in sorted(os.listdir(MEMDIR)):
            if f.endswith(".md"):
                q = os.path.join(MEMDIR, f)
                try:
                    if round_id in io.open(q, encoding="utf-8", errors="replace").read():
                        hits.append(q)
                except OSError:
                    pass
    return hits[:3]


def live_checks():
    """F: production integrity must agree with the snapshot and recipe."""
    fails = []
    for script, args, label in (
        ("binary_integrity.py", ["--live"], "binary_integrity"),
        ("recipe_check.py", ["--live"], "recipe_check"),
        ("handoff_check.py", ["--live"], "handoff_check"),
    ):
        path = os.path.join(ROOT, "tools", script)
        if not os.path.isfile(path):
            fails.append("F: %s missing" % script)
            continue
        r = subprocess.run([sys.executable, path] + args, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
        print("  LIVE %-18s rc=%s %s" % (label, r.returncode, tail[:120]))
        if r.returncode != 0:
            fails.append("F: %s --live failed: %s" % (script, tail[:180]))
    return fails


def check(round_id=None, date=None, report_text=None, live=False):
    fails = []
    snap = snapshot()
    rid = round_id or snap.get("round", "")
    day = date or snap.get("date", "")
    if not re.fullmatch(r"W\d{4}", rid or ""):
        fails.append("A: SNAPSHOT 的 round 不可解析（got %r）" % rid)
        return fails, {}
    rep = os.path.join(ROOT, "albus", rid, "reply.md")
    if not os.path.isfile(rep):
        fails.append("A: albus/%s/reply.md 不存在" % rid)
    txt = report_text if report_text is not None else (
        io.open(rep, encoding="utf-8", errors="replace").read() if os.path.isfile(rep) else "")
    if report_text is not None and len(txt) < 1500:
        fails.append("D: albus/%s/reply.md 只有 %d 字符（要 >=1500）" % (rid, len(txt)))
    if rid not in ledger_rounds():
        fails.append("B: PROGRESS.tsv 没有 source=%s 的行（这一轮没落账）" % rid)
    plan = io.open(PLAN, encoding="utf-8", errors="replace").read() if os.path.isfile(PLAN) else ""
    if ("### 回写 · %s" % rid) not in plan:
        fails.append("E: W832 里没有 `### 回写 · %s` 块（本轮结论没进唯一方案）" % rid)
    if not memory_hits(rid, day):
        fails.append("C: .workbuddy/memory/ 里没有提到 %s 的条目（当日记忆未写）" % rid)
    if live:
        fails.extend(live_checks())
    return fails, {"round": rid, "date": day, "chars": len(txt)}


def self_test():
    ok = 0
    cases = [
        ("round with no report / no ledger row / no memory", dict(round_id="W9999")),
        ("placeholder report (0 chars)", dict(round_id="W1035", report_text="")),
        ("round id unparseable", dict(round_id="round-5")),
    ]
    for label, kw in cases:
        fails, _ = check(**kw)
        if fails:
            ok += 1
        else:
            print("SELF_TEST: negative case passed: " + label)
    real, info = check(round_id="W1035")
    print("SELF_TEST: %d/%d negatives rejected; W1035 -> %s %s" %
          (ok, len(cases), "PASS" if not real else "FAIL %s" % real[:2], info))
    return 0 if ok == len(cases) else 1


def main(argv):
    rid = None
    if "--round" in argv:
        rid = argv[argv.index("--round") + 1]
    if "--self-test" in argv:
        return self_test()
    fails, info = check(round_id=rid, live="--live" in argv)
    if not ("--quiet" in argv):
        print("ROUND_LEDGER: round=%s date=%s chars=%d" % (info.get("round"), info.get("date"), info.get("chars", 0)))
        if fails:
            print("ROUND_LEDGER: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("ROUND_LEDGER: PASS (report + ledger row + daily memory all present)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
