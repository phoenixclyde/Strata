"""W820: 断点续传 + 卡顿重试的下载器（GitHub 这条链路约 30-60 KB/s 且会中途停住）。

用法: dl2.py <url> <out> <total_bytes>
每次用 Range 从当前长度续；单次读 60 s 没数据就重连，保留已下载字节。
"""
import os
import sys
import time
import urllib.error
import urllib.request

url, out, total = sys.argv[1], sys.argv[2], int(sys.argv[3])
TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
tmp = out + ".part"
attempt = 0

while True:
    have = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    if have >= total:
        os.replace(tmp, out)
        print("DONE %d bytes in %d attempts" % (have, attempt), flush=True)
        break
    attempt += 1
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + TOK,
            "User-Agent": "albus",
            "Range": "bytes=%d-" % have,
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as resp, open(tmp, "ab") as f:
            if attempt == 1:
                print("  status", resp.status, flush=True)
            while True:
                b = resp.read(1 << 16)
                if not b:
                    break
                f.write(b)
                have += len(b)
                if time.time() - t0 > 20:
                    t0 = time.time()
                    print("  %5.1f%%  %.1f MB  attempt %d" % (100.0 * have / total, have / 2**20, attempt), flush=True)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print("  retry after %s (%d/%d)" % (type(e).__name__, have, total), flush=True)
        time.sleep(2)
