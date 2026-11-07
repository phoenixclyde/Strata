# 下载上游源码包 v0.1.40.4 / v0.1.40.3（gh-proxy 通道）+ sha256
import urllib.request, os, hashlib, time, sys

DEST = r"D:/workbuddy_space/strata_ws/deploy/transfer"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
opener.addheaders = [("User-Agent", "curl/8.0")]

TAGS = ["v0.1.40.4", "v0.1.40.3"]
BASE = "https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/%s.zip"

for tag in TAGS:
    out = os.path.join(DEST, "strata-src-%s.zip" % tag.lstrip("v"))
    if os.path.exists(out) and os.path.getsize(out) > 1_000_000:
        print("skip exists", out, os.path.getsize(out)); continue
    url = BASE % tag
    t0 = time.time()
    try:
        with opener.open(url, timeout=180) as r, open(out, "wb") as f:
            n = 0
            while True:
                b = r.read(1 << 16)
                if not b: break
                f.write(b); n += len(b)
        dt = time.time() - t0
        print("%s -> %d bytes in %.1fs (%.2f MB/s)" % (tag, n, dt, n / dt / 1e6))
    except Exception as e:
        print("%s FAILED %r" % (tag, e)); continue
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print("   sha256", h)
