#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stop_guard.py -- Stop hook. 第三版：不再只看"消息里有没有四段"，改为**跑轻门**。

W1035 演进：
  v1  看 `last_assistant_message` 里有没有四段 —— 形式检查，贴一段报告就能骗过。
  v2  乱码修复（ensure_ascii）+ fail-open + 探针日志。
  v3（本版）标记里记着「这一回合最后改的是哪个文件」：
      · 改的是 `albus/` 或 `deploy/`（= 真在写结论/账本/方案）⇒ **跑三个快门**
        （report_lint · report_depth · round_ledger），任一 FAIL 就 block，并把门输出当理由；
      · 改的是 `tools/` 等工程文件 ⇒ 不强制报告，直接放行（改个脚本不该补一份四件套）。
      · 门跑不动 / 超时 / 任何异常 ⇒ fail-open（坏钩子卡死所有对话，比漏一次严重）。

契约：stdin 收 JSON，stdout 回 JSON，`{"decision":"block"}` 阻止结束；`{}` = 放行。
输出一律 `ensure_ascii=True`（中文用 unicode 转义），任何代码页都不会读成乱码。
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = HERE.replace("\\", "/").lower()
MARK = os.path.join(HERE, ".workbuddy", ".round_dirty")
DISABLE = os.path.join(HERE, ".workbuddy", "disable_stop_guard")
SEEN = os.path.join(HERE, ".workbuddy", ".hook_seen.log")
PY = sys.executable
GATES = [("report_lint.py", True), ("report_depth.py", True), ("round_ledger.py", False)]
STERN_DIRS = ("albus/", "deploy/")


def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
    return 0


def allow():
    return out({})


def note(s):
    try:
        with io.open(SEEN, "a", encoding="utf-8", newline="\n") as f:
            f.write(s + "\n")
    except OSError:
        pass


def round_id():
    try:
        h = io.open(os.path.join(HERE, "albus", "w1034", "HANDOFF.md"), encoding="utf-8", errors="replace").read()
        m = re.search(r"^> SNAPSHOT:.*?\bround=(W\d{4})", h, re.M)
        return m.group(1) if m else ""
    except OSError:
        return ""


def marked_path():
    try:
        return io.open(MARK, encoding="utf-8", errors="replace").read().strip()
    except OSError:
        return ""


def run_gates(rid):
    rep = os.path.join(HERE, "albus", rid, "reply.md") if rid else None
    fails = []
    for name, needs_report in GATES:
        cmd = [PY, os.path.join(HERE, "tools", name)]
        if needs_report:
            if not (rep and os.path.isfile(rep)):
                fails.append("%s: no albus/%s/reply.md" % (name, rid))
                continue
            cmd.append(rep)
        try:
            r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=60)
        except Exception as e:
            note("  gate %s EXC %r (fail-open)" % (name, e))
            return []
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).strip().splitlines()
            fails.append("%s: %s" % (name, tail[-1][:120] if tail else "rc=%d" % r.returncode))
    return fails


def main():
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        note("PARSE-FAIL %r" % (e,))
        return allow()
    try:
        cwd = str(d.get("cwd") or os.getcwd()).replace("\\", "/").lower().rstrip("/")
        msg = d.get("last_assistant_message")
        note("call cwd=%s stop_hook_active=%s msg_len=%s"
             % (cwd, d.get("stop_hook_active"), "None" if msg is None else len(str(msg))))

        if d.get("stop_hook_active"):
            note("  -> allow (already blocked once)")
            return allow()
        if os.path.exists(DISABLE):
            return allow()
        if cwd != ROOT:
            return allow()
        if not os.path.exists(MARK):
            return allow()

        marked = marked_path()
        st = (marked.split()[-1] if marked else "").replace("\\", "/").lower()
        rel = st[len(ROOT) + 1:] if st.startswith(ROOT + "/") else st
        note("  marked=%s" % rel[:90])
        if not rel.startswith(STERN_DIRS):
            note("  -> allow (touched %r, not a conclusion/ledger file)" % rel[:40])
            try:
                os.remove(MARK)          # 这一回合已经结束，别把标记留给下一回合
            except OSError:
                pass
            return allow()

        rid = round_id()
        fails = run_gates(rid)
        if not fails:
            try:
                os.remove(MARK)
            except OSError:
                pass
            note("  -> allow (three quick gates PASS)")
            return allow()

        note("  -> BLOCK gates: %s" % fails)
        return out({
            "decision": "block",
            "reason": ("This turn wrote under albus/ or deploy/ but the round does not close cleanly: "
                       + " | ".join(fails)
                       + ". Fix them (four sections in the reply, ledger row, daily memory, 6.5 write-back "
                         "block, then python albus/w1002/round_close.py --report <file>)."),
        })
    except Exception as e:
        note("EXC %r" % (e,))
        return allow()


if __name__ == "__main__":
    sys.exit(main())
