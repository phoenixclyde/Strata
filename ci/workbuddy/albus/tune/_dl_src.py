#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载四份源码到本地 deploy/tmp/_src/ ：routeK 仓库 / llama.cpp pin / llama.cpp master / Strata 0.2.4.2"""
import os, sys, time, tarfile

BASE = r"D:/workbuddy_space/strata_ws/deploy/tmp/_src"
os.makedirs(BASE, exist_ok=True)

PROXY = "https://gh-proxy.com/"
DIRECT = ""

TARGETS = [
    ("rk_repo.tar.gz",
     "https://codeload.github.com/KIntegrated/vllm-gfx906-mobydick/tar.gz/refs/heads/gfx906/main"),
    ("llm_pin.tar.gz",
     "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/3cf03257f219afbe7334045ff7c6a06ac68c627d"),
    ("llm_master.tar.gz",
     "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/36e36e63a54f"),
    ("strata024.tar.gz",
     "https://codeload.github.com/Niko1221/Strata/tar.gz/refs/tags/v0.2.4.2"),
]

def human(n):
    return "%.1f MB" % (n / 1e6)

def fetch(url, out):
    last = None
    for prefix in (PROXY, DIRECT):
        u = prefix + url if prefix else url
        for attempt in range(2):
            try:
                t0 = time.time()
                # 用 curl 拿（本机 curl 可用，python urllib 大文件慢）
                rc = os.system('curl -sL --max-time 900 -o "%s.part" "%s"' % (out, u))
                sz = os.path.getsize(out + ".part") if os.path.exists(out + ".part") else 0
                if rc == 0 and sz > 100000:
                    with tarfile.open(out + ".part", "r:gz") as tf:
                        n = sum(1 for _ in tf)
                    os.replace(out + ".part", out)
                    return sz, n, time.time() - t0, u[:60]
                last = "rc=%s size=%s %s" % (rc, sz, u[:60])
            except Exception as e:
                last = "ERR %s %s" % (e, u[:60])
        print("   retry next channel; last=%s" % last, flush=True)
    raise RuntimeError(last)

for name, url in TARGETS:
    out = os.path.join(BASE, name)
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        print("[skip] %s already %s" % (name, human(os.path.getsize(out))), flush=True)
        continue
    print("[get ] %s" % name, flush=True)
    try:
        sz, n, dt, u = fetch(url, out)
        print("[ok  ] %-18s %-9s %d members  %.1fs  via %s" % (name, human(sz), n, dt, u), flush=True)
    except Exception as e:
        print("[FAIL] %s -> %s" % (name, e), flush=True)
print("DONE")
