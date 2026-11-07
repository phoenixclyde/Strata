# -*- coding: utf-8 -*-
"""rs.py —— 到 166 跑一段 shell 的通用通道（base64 走 stdin，规避 argv 长度与吃字符）。

用法：
    python albus/rs.py <local_script.sh> [timeout_s]
    python albus/rs.py -c "<一句话>" [timeout_s]

输出原样打印（stdout+stderr 合并）。远端路径一律 /home/albus/strata166/...
"""
import base64
import subprocess
import sys

HOST = "albus@192.168.50.166"


def run(script, timeout=120):
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "base64 -d | bash"],
        input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "-c":
        body = a[1]
        to = int(a[2]) if len(a) > 2 else 120
    else:
        body = open(a[0], encoding="utf-8").read()
        to = int(a[1]) if len(a) > 1 else 120
    try:
        print(run(body, to))
    except subprocess.TimeoutExpired:
        print("[TIMEOUT after %ds]" % to)
