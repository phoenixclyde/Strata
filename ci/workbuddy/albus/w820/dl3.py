"""W820: 稳健下载器 v3 —— 处理 codeload 有时忽略 Range 的情况。

规则：
  * 每次请求带 `Range: bytes=<have>-`；
  * 回 206 => 追加；回 200 => 说明服务端没理 Range，**清空重下**（这正是 v2 把包写坏的原因）；
  * 总量从 `Content-Range: bytes a-b/total` 或 200 的 `Content-Length` 里读，不硬编码；
  * 收尾必须 大小==总量 且 gzip 能完整解开，否则继续。
"""
import gzip
import os
import sys
import time
import urllib.error
import urllib.request

URL = sys.argv[1]
OUT = sys.argv[2]
TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
tmp = OUT + ".part"
total = None


def parse_range(hdr):
    # "bytes 100-200/31148786"
    try:
        return int(hdr.split("/")[-1])
    except Exception:
        return None


def compress_ok(path):
    try:
        with gzip.open(path, "rb") as f:
            while f.read(1 << 20):
                pass
        return True
    except Exception as e:
        print("  gzip check failed:", type(e).__name__, e, flush=True)
        return False


attempt = 0
while True:
    have = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    if total is not None and have == total and os.path.getsize(tmp) and compress_ok(tmp):
        os.replace(tmp, OUT)
        print("DONE %d bytes, %d attempts" % (have, attempt), flush=True)
        break
    attempt += 1
    req = urllib.request.Request(
        URL, headers={"Authorization": "Bearer " + TOK, "User-Agent": "albus", "Range": "bytes=%d-" % have}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            if resp.status == 200 and have:
                print("  server ignored Range (200): restarting from 0", flush=True)
                have = 0
                mode = "wb"
            else:
                mode = "ab"
            cr = resp.headers.get("Content-Range")
            if cr:
                total = parse_range(cr) or total
            elif resp.status == 200:
                total = int(resp.headers.get("Content-Length") or 0) or total
            with open(tmp, mode) as f:
                while True:
                    b = resp.read(1 << 16)
                    if not b:
                        break
                    f.write(b)
                    have += len(b)
                    if time.time() - t0 > 20:
                        t0 = time.time()
                        print("  %.1f%%  %.1f MB  (total %s)" % (100.0 * have / (total or 1), have / 2**20, total), flush=True)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print("  retry after %s at %d" % (type(e).__name__, have), flush=True)
        time.sleep(2)
        continue
    if total is None:
        total = os.path.getsize(tmp)
