"""audit_recheck.py —— 把最新审计件的「整改复核命令」逐条跑一遍（审计整改的可验证闭合）。

用法: python tools/audit_recheck.py [AUDIT16_W844_W853.md]
判据: 表格第 1 列是 finding id，最后一列里反引号包的命令会被执行；**全部 PASS 才 exit 0**。
最后一列写 `—` 的行计入 SKIP（不算失败，但会打印，避免用 — 滥竽充数）。
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "AUDIT16_W844_W853.md"
    path = os.path.join(ROOT, "deploy", name)
    t = io.open(path, encoding="utf-8").read()
    if "## 10 整改台账" not in t:
        print("no 整改台账 section in", name)
        return 1
    sec = t[t.index("## 10 整改台账"):]
    checks = []
    for ln in sec.splitlines():
        if not ln.startswith("| P"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        fid, tail = cells[0], cells[-1]
        m = re.search(r"`([^`]+)`", tail)
        checks.append((fid, m.group(1) if m else None))

    fails = skips = 0
    for fid, cmd in checks:
        if not cmd or cmd.strip() in ("—", "-"):
            skips += 1
            print("%-6s SKIP  (无本地复核)" % fid)
            continue
        cmd = cmd.replace("\\|", "|")
        try:
            r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                               text=True, timeout=25, stdin=subprocess.DEVNULL)
            ok = r.returncode == 0
            out = r.stdout
        except subprocess.TimeoutExpired:
            ok, out = False, "TIMEOUT"
        fails += 0 if ok else 1
        print("%-6s %s  %s" % (fid, "PASS" if ok else "FAIL", cmd[:88]), flush=True)
        if not ok and out.strip():
            print("        out: " + out.strip().splitlines()[0][:100])
    print("\n%d 条：PASS %d / FAIL %d / SKIP %d"
          % (len(checks), len(checks) - fails - skips, fails, skips))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
