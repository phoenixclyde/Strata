#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""round_mark.py -- PreToolUse hook: remember that this turn touched project files.

Stop 钩子（tools/stop_guard.py）靠这个标记区分「只是回答了一个问题」和「干了活」。
只对 Write / Edit / MultiEdit 且路径在工作区内时打标记；其他一律放行。
"""
import json
import os
import sys


def main():
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.stdout.write("{}\n")
        return 0
    try:
        name = str(d.get("tool_name") or "")
        if name not in ("Write", "Edit", "MultiEdit"):
            sys.stdout.write("{}\n")
            return 0
        ti = d.get("tool_input") or {}
        path = str(ti.get("file_path") or ti.get("path") or "").replace("\\", "/").lower()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/").lower()
        if path.startswith(root + "/"):
            mark = os.path.join(root, ".workbuddy", ".round_dirty")
            os.makedirs(os.path.dirname(mark), exist_ok=True)
            with open(mark, "w") as f:
                f.write(name + " " + path + "\n")
    except Exception:
        pass
    sys.stdout.write("{}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
