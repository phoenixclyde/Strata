#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生产状态快照：镜像 / exe / args / env / health。每轮报告都用这一份。"""
import json, subprocess, urllib.request

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
C = "strata166-407"


def sh(cmd):
    p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    return (p.stdout or "").strip()


print("== 生产状态 ==")
print("容器   :", sh("docker ps --format '{{.Names}} {{.Status}}' | grep strata166 || echo DOWN"))
print("镜像   :", sh("docker inspect %s --format '{{.Config.Image}}'" % C))
c = json.load(open(CFG))
print("引擎   :", c["exe"])
print("args   :", len(c["args"]), "项 ->", " ".join(c["args"]))
print("env    :", len(c.get("env") or {}), "项")
for k in sorted(c.get("env") or {}):
    print("         %-32s %s" % (k, c["env"][k]))
print("配置md5:", sh("md5sum " + CFG).split()[0])
try:
    h = urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=5).read().decode()
    d = json.loads(h)
    print("health :", {k: d.get(k) for k in ("status", "loaded", "max_context")})
except Exception as e:                                    # noqa: BLE001
    print("health : ERR", repr(e)[:100])
