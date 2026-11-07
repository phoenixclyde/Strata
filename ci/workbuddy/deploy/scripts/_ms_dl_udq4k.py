# -*- coding: utf-8 -*-
"""ModelScope 分片下载（通用版）：Content-Range 硬校验 + 断点续传 + 8 并发。用于 unsloth UD-Q4_K_XL。"""
import os, re, sys, time, socket, shutil, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0'}
REPO = 'unsloth/Qwen3.8-Flash-Next-GGUF'
BASE = 'https://www.modelscope.cn/models/%s/resolve/master/' % REPO
DSTDIR = r'D:\idm\Strata-UDQ4KXL'
SUB = 'UD-Q4_K_XL/'
FILES = ['Qwen3.8-Flash-Next-UD-Q4_K_XL-0000%d-of-00004.gguf' % i for i in range(1, 5)]
PARTS = int(os.environ.get('SD_PARTS', '8'))
socket.setdefaulttimeout(45)
CR_RE = re.compile(r'bytes\s+(\d+)-(\d+)/(\d+)')
os.makedirs(DSTDIR, exist_ok=True)


def say(s):
    print(s, flush=True)


def size_of(url):
    h = dict(UA); h['Range'] = 'bytes=0-0'
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=45) as r:
        m = CR_RE.match(r.headers.get('Content-Range') or '')
        if not m:
            cl = r.headers.get('Content-Length')
            return int(cl) if cl else None
        return int(m.group(3))


t_all = time.time()
for NAME in FILES:
    URL = BASE + SUB + NAME
    DST = os.path.join(DSTDIR, NAME)
    say('=' * 72)
    say('### %s' % NAME)
    if os.path.exists(DST):
        say('  已存在 %.2f GB，跳过' % (os.path.getsize(DST) / 1e9))
        continue
    try:
        TOTAL = size_of(URL)
    except Exception as e:
        say('  取大小失败: %s' % str(e)[:120]); continue
    if not TOTAL:
        say('  拿不到总长'); continue
    say('  大小 %.2f GB (%d bytes)' % (TOTAL / 1e9, TOTAL))

    seg = TOTAL // PARTS
    BOUNDS = [(i * seg, TOTAL - 1 if i == PARTS - 1 else (i + 1) * seg - 1) for i in range(PARTS)]
    TMP = [DST + '.p%02d' % i for i in range(PARTS)]
    done0 = sum(os.path.getsize(p) for p in TMP if os.path.exists(p))
    t0 = time.time()
    if done0:
        say('  已有 %.2f GB，续传' % (done0 / 1e9))

    def fetch(i):
        a, b = BOUNDS[i]
        need = b - a + 1
        p = TMP[i]
        have = os.path.getsize(p) if os.path.exists(p) else 0
        if have > need:
            os.remove(p); have = 0
        err = ''
        for _ in range(10):
            if have >= need:
                return i, 'ok'
            try:
                h = dict(UA); h['Range'] = 'bytes=%d-%d' % (a + have, b)
                with urllib.request.urlopen(urllib.request.Request(URL, headers=h), timeout=45) as r:
                    if r.status != 206:
                        raise RuntimeError('status %d' % r.status)
                    m = CR_RE.match(r.headers.get('Content-Range') or '')
                    if not m or int(m.group(1)) != a + have:
                        raise RuntimeError('bad CR %r' % (r.headers.get('Content-Range'),))
                    with open(p, 'ab') as f:
                        while True:
                            c = r.read(1 << 20)
                            if not c:
                                break
                            f.write(c); have += len(c)
                            if have > need:
                                raise RuntimeError('overrun')
                if have >= need:
                    return i, 'ok'
            except Exception as e:
                err = str(e)[:50]; time.sleep(2)
        return i, 'fail(%s) %.0f%%' % (err, have * 100.0 / need)

    stop = [False]

    def mon():
        while not stop[0]:
            time.sleep(20)
            cur = sum(os.path.getsize(p) for p in TMP if os.path.exists(p))
            say('    [%s] %.1f%%  %.2f/%.2f GB  avg %.1f MB/s'
                % (time.strftime('%H:%M:%S'), cur * 100.0 / TOTAL, cur / 1e9, TOTAL / 1e9,
                   (cur - done0) / 1048576 / max(time.time() - t0, 1)))

    threading.Thread(target=mon, daemon=True).start()
    with ThreadPoolExecutor(max_workers=PARTS) as ex:
        res = list(ex.map(fetch, range(PARTS)))
    stop[0] = True
    allok = all(os.path.exists(p) and os.path.getsize(p) == (BOUNDS[i][1] - BOUNDS[i][0] + 1) for i, p in enumerate(TMP))
    say('  分片: ' + ', '.join(s for _, s in res))
    if allok:
        say('  合并中...')
        with open(DST, 'wb') as out:
            for p in TMP:
                with open(p, 'rb') as f:
                    shutil.copyfileobj(f, out, 16 << 20)
        for p in TMP:
            os.remove(p)
        sz = os.path.getsize(DST)
        say('  完成 %.3f GB  match=%s  用时 %.1f 分钟' % (sz / 1e9, sz == TOTAL, (time.time() - t0) / 60))
    else:
        say('  未完成，保留分片可续传')
    say('')

say('=' * 72)
say('目录: %s' % DSTDIR)
tot = 0
for n in sorted(os.listdir(DSTDIR)):
    q = os.path.join(DSTDIR, n)
    if os.path.isfile(q):
        tot += os.path.getsize(q)
        say('  %-62s %8.2f GB' % (n, os.path.getsize(q) / 1e9))
say('TOTAL %.2f GB   总用时 %.1f 分钟' % (tot / 1e9, (time.time() - t_all) / 60))
