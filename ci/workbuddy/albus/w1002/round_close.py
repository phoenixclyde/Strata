#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一轮收尾门（本机 Windows 侧）：四个 lint 一起跑，硬门不过不许发报告。

W1002 起因：机主问「你的四项报告呢 / CI-CD 呢 / 对应的门呢 / 还有个 lint」。
四个 lint 一直都在 tools/ 下，但**没有任何调用者**：report_lint 靠我"记得跑"，
plan_lint 当时正报 FAIL（4 份 PLAN 未登记）却没人看见，ledger/param_pair 的
警告债也没人汇总。门 = 有工具 + 有调用者 + 有负向自测。

用法:
  python albus/w1002/round_close.py --report albus/w1002/reply.md
  python albus/w1002/round_close.py --self-test     # 故意喂坏报告，确认会拦
"""
import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("D:/workbuddy_space/strata_ws")
PY = sys.executable
TOOLS = ROOT / "tools"

HARD = ["report_lint.py", "report_depth.py", "plan_lint.py", "audit_index.py", "plan_retired.py",
        "pointer_lint.py", "audit_scope.py", "audit_outputs.py", "plan_single_source.py",
        "handoff_check.py",  # W1034: the handoff must stay complete on every round close
        "round_ledger.py",   # W1035: a report is not enough -- the round must also reach the ledger and the daily memory
        "claim_homes.py",   # W1035: every ledger row must declare its own search keys (KW:) and actually contain them
        "report_consistency.py",  # W1037: the report's "三、本次落生产" must match the round's ledger rows (restarts / downtime)
        "ledger_lint.py",   # AUDIT29: it had no exit code and a stale 10-column rule -- 209 problems, zero blocks
        "ci_runs_lint.py"]  # AUDIT29: CI_RUNS held a 404 run id for the production exe; D7 only read the status column
# AUDIT27: audit debt / retired gate / single source; AUDIT28: verdicts / companions / plan navigation
# 仓库里的门（不在 tools/ 下）：(脚本, 参数, 期望输出末行关键词)
SCRIPT_HARD = [(ROOT / "ci/prefill_phases/kernel_curve.py", ["--check"], "KERNEL_CURVE: PASS"),
               (ROOT / "ci/bundle_budget/bundle.py", ["--check"], "BUNDLE: PASS")]
SOFT = ["param_pair_lint.py"]


def run_lint(name, extra=()):
    r = subprocess.run([PY, str(TOOLS / name), *extra], cwd=str(ROOT),
                       capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    return r.returncode, out


def close(report, post=False):
    fails = []
    if not pathlib.Path(report).is_file():
        print("ROUND_CLOSE: FAIL (report not found: %s)" % report)
        return 1
    for name in HARD:
        extra = (report,) if name in ("report_lint.py", "report_depth.py", "report_consistency.py") else ()
        rc, out = run_lint(name, extra)
        tail = out.splitlines()[-1] if out else "(no output)"
        print("  %-22s rc=%d  %s" % (name, rc, tail[:150]))
        if rc != 0:
            fails.append("%s rc=%d" % (name, rc))
    for name in SOFT:
        rc, out = run_lint(name)
        tail = out.splitlines()[-1] if out else "(no output)"
        warns = sum(1 for l in out.splitlines() if l.strip().startswith(("W8", "W9", "↑", "[")))
        print("  %-22s rc=%d  warn_lines=%-3d %s" % (name, rc, warns, tail[:110]))
        if rc != 0:
            fails.append("%s rc=%d" % (name, rc))
    for path, args, want in SCRIPT_HARD:
        r = subprocess.run([PY, str(path), *args], cwd=str(ROOT), capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        tail = out.splitlines()[-1] if out else "(no output)"
        print("  %-22s rc=%d  %s" % (path.name, r.returncode, tail[:110]))
        if r.returncode != 0 or want not in out:
            fails.append("%s rc=%d" % (path.name, r.returncode))
    # W1003 新增：权威件「本机主拷贝 ↔ 166 镜像」逐字节一致（不是可选项）
    # 起因：W882 之后 18 轮的回写全在本机，166 那份 §6.5 冻结了两天没人发现。
    r = subprocess.run([PY, str(ROOT / "albus/w1003/mirror_check.py")], cwd=str(ROOT),
                       capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or ["(no output)"]
    print("  %-22s rc=%d  %s" % ("mirror_check.py", r.returncode, tail[0][:150]))
    if r.returncode != 0:
        fails.append("mirror_check rc=%d" % r.returncode)

    if fails:
        print("ROUND_CLOSE: FAIL (%d): %s" % (len(fails), ", ".join(fails)))
        return 1
    print("ROUND_CLOSE: PASS (report_lint + plan_lint hard; ledger/param_pair rc=0, warnings recorded above)")
    if post:
        # W1015: the report has exactly one copy.  Two rounds went out with the file passing
        # every gate and the message rewritten (8 rows, no 3a/3b); the gate never saw it.
        import hashlib
        b = open(report, "rb").read()
        txt = b.decode("utf-8")
        print("POST: md5=%s chars=%d  <- send the block below verbatim, checksum line included"
              % (hashlib.md5(b).hexdigest(), len(txt)))
        print("=" * 20 + " BEGIN reply.md " + "=" * 20)
        print(txt, end="" if txt.endswith("\n") else "\n")
        print("=" * 21 + " END reply.md " + "=" * 21)
    return 0


def self_test():
    bad = ROOT / "albus" / "w1002" / "_bad_report.md"
    bad.write_text("只有结论，没有四件套\n", encoding="utf-8")
    rc, _ = run_lint("report_lint.py", (str(bad),))
    bad.unlink(missing_ok=True)
    ok = rc != 0
    print("  negative self-test: broken report rejected = %s (rc=%d)" % (ok, rc))
    print("ROUND_CLOSE: %s" % ("PASS" if ok else "FAIL (lint is not rejecting)"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true",
                    help="after PASS, print POST: md5=... chars=... and then the report verbatim (the only copy that may be sent)")
    ap.add_argument("--report")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.report:
        ap.error("--report is required (or --self-test)")
    sys.exit(close(a.report, a.post))
