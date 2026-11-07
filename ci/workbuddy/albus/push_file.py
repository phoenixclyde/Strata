# -*- coding: utf-8 -*-
"""push_file.py —— 把一个本地文件写到 166 的指定路径（走 rs.py 的 stdin 通道，绕开 argv 8KB 限制）。

用法: python albus/push_file.py <local> <remote_abs_path> [mode]
"""
import base64
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rs  # noqa: E402


def main():
    local, remote = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "644"
    data = io.open(local, "rb").read()
    b64 = base64.b64encode(data).decode()
    script = (
        "set -e\n"
        "mkdir -p \"$(dirname '%s')\"\n"
        "printf '%%s' '%s' | base64 -d > '%s'\n"
        "chmod %s '%s'\n"
        "wc -c '%s'\n" % (remote, b64, remote, mode, remote, remote)
    )
    print(rs.run(script, 120))


if __name__ == "__main__":
    main()
