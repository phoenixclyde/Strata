"""Conformance test for skill `workbuddy-round-gate-hooks` §4.

Corrected after the first run failed: the marker only decides *whether* to run the gates;
the gates always inspect `albus/<round>/reply.md`, where <round> comes from
`HANDOFF.md` `> SNAPSHOT: … round=W####`. So the negative case must damage *that* file,
not some arbitrary marked file.
"""
import json
import os
import shutil
import subprocess
import sys

WS = os.getcwd().replace("\\", "/")
ROOT = WS.lower()
MARK = os.path.join(WS, ".workbuddy", ".round_dirty")
GATE = os.path.join(WS, "tools", "stop_guard.py")
REP = os.path.join(WS, "albus", "w1035", "reply.md")
BAK = REP + ".conform.bak"


def gate(payload=None):
    p = payload if payload is not None else {"cwd": WS, "last_assistant_message": "x"}
    r = subprocess.run([sys.executable, GATE], input=json.dumps(p),
                       capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


def mark(path):
    with open(MARK, "w", encoding="utf-8") as f:
        f.write("Write " + path)


def main():
    if not os.path.isfile(BAK):
        print("FATAL: backup missing, refusing to touch the report")
        return 1
    res = []

    # 1) 正常：真报告 + 标记→ 三门应全过、放行、清标记
    mark(os.path.abspath(REP))
    out = gate()
    res.append(("正常报告（放行）", out, out in ("", "{}"), not os.path.exists(MARK)))

    # 2) 负向：把真报告换成 50 字占位 → report_lint / report_depth 必须红 ⇒ block
    try:
        with open(REP, "w", encoding="utf-8") as f:
            f.write("只有结论，没有四件套，也没有账本行。\n")
        mark(os.path.abspath(REP))
        out = gate()
        blocked = '"block"' in out.replace(" ", "")
        res.append(("报告缩水（block）", out[:160], blocked, os.path.exists(MARK)))
    finally:
        shutil.copyfile(BAK, REP)

    # 3) 负向：报告整个不见 → round_ledger/report_lint 报 missing ⇒ block
    try:
        os.replace(REP, REP + ".hidden")
        mark(os.path.abspath(REP))
        out = gate()
        blocked = '"block"' in out.replace(" ", "")
        res.append(("报告缺失（block）", out[:160], blocked, os.path.exists(MARK)))
    finally:
        if os.path.exists(REP + ".hidden"):
            os.replace(REP + ".hidden", REP)

    # 4) fail-open：payload 缺 last_assistant_message 且报告正常 → 放行
    mark(os.path.abspath(REP))
    out = gate({"cwd": WS})
    res.append(("缺 msg 字段（fail-open）", out, out in ("", "{}"), not os.path.exists(MARK)))

    # 5) 只拦一次：stop_hook_active=True → 放行
    mark(os.path.abspath(REP))
    out = gate({"cwd": WS, "last_assistant_message": "x", "stop_hook_active": True})
    res.append(("stop_hook_active（放行）", out, out in ("", "{}"), True))

    # 6) 工程文件不受牵连：标 tools/ → 放行且清标记
    mark(os.path.join(WS, "tools", "stop_guard.py"))
    out = gate()
    res.append(("改 tools/（放行）", out, out in ("", "{}"), not os.path.exists(MARK)))

    if os.path.exists(MARK):
        os.remove(MARK)
    bad = 0
    for name, out, ok, mark_clean in res:
        if not ok:
            bad += 1
        print("%s  %-28s marker_cleared=%s  %s" %
              ("PASS" if ok else "FAIL", name, mark_clean, out[:90]))
    print("\nSKILL_CONFORMANCE_HOOK: %s (%d/%d)" % ("PASS" if not bad else "FAIL", len(res) - bad, len(res)))
    print("report restored:", os.path.getsize(REP), "bytes (backup", os.path.getsize(BAK), "bytes)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
