"""下载上游 0.2.7 源码包（Windows 侧），带进度落盘，供后台运行。"""
import os
import sys
import time
import urllib.request

TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
URL = "https://api.github.com/repos/Niko1221/Strata/tarball/v0.2.7"
OUT = "albus/w820/strata-0.2.7.tar.gz"
tmp = OUT + ".part"

req = urllib.request.Request(URL, headers={"Authorization": "Bearer " + TOK, "User-Agent": "albus"})
t0 = time.time()
n = 0
with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as f:
    while True:
        b = resp.read(1 << 20)
        if not b:
            break
        f.write(b)
        n += len(b)
        if n % (20 << 20) < (1 << 20):
            print("  %5.1f MB  %4.1f s" % (n / 2**20, time.time() - t0), flush=True)

os.replace(tmp, OUT)
print("DONE bytes=%d MB=%.1f sec=%.1f" % (n, n / 2**20, time.time() - t0))
