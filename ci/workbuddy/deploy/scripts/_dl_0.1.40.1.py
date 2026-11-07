# -*- coding: utf-8 -*-
"""后台下载 Strata v0.1.40.1 源码 zip（多镜像重试），供 166 上电后升级用"""
import os, sys, time, urllib.request, socket
sys.stdout.reconfigure(encoding='utf-8')
socket.setdefaulttimeout(60)

DST = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
TAG = 'v0.1.40.1'
URLS = [
    'https://codeload.github.com/Niko1221/Strata/zip/refs/tags/%s' % TAG,
    'https://ghproxy.net/https://github.com/Niko1221/Strata/archive/refs/tags/%s.zip' % TAG,
    'https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/%s.zip' % TAG,
    'https://hub.gitmirror.com/https://github.com/Niko1221/Strata/archive/refs/tags/%s.zip' % TAG,
    'https://github.com/Niko1221/Strata/archive/refs/tags/%s.zip' % TAG,
]
UA = {'User-Agent': 'Mozilla/5.0'}

def try_one(url, dst, budget=240):
    t0 = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get('Content-Length') or 0)
        got = 0
        with open(dst, 'wb') as f:
            while True:
                if time.time() - t0 > budget:
                    raise RuntimeError('budget exceeded at %.1f MB' % (got / 1e6))
                c = r.read(1 << 18)
                if not c:
                    break
                f.write(c); got += len(c)
    dt = max(time.time() - t0, 1e-3)
    return got, total, dt

os.makedirs(os.path.dirname(DST), exist_ok=True)
for u in URLS:
    tag = u.split('/')[2]
    print('--- trying %s ---' % tag, flush=True)
    tmp = DST + '.part'
    try:
        got, total, dt = try_one(u, tmp)
        if total and got != total:
            print('  SIZE MISMATCH got=%d total=%d -> 丢弃' % (got, total), flush=True)
            os.remove(tmp); continue
        os.replace(tmp, DST)
        print('  OK %d bytes (%.1f MB) in %.1fs = %.2f MB/s' % (got, got / 1e6, dt, got / 1e6 / dt), flush=True)
        print('  saved -> %s' % DST, flush=True)
        break
    except Exception as e:
        print('  FAIL %s' % str(e)[:160], flush=True)
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass
else:
    print('ALL MIRRORS FAILED', flush=True)
