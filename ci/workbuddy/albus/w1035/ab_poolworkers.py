#!/usr/bin/env python3
"""P416 未结①：--pool-workers 20 vs 10 的**冷请求** decode A/B（在 166 上跑）。

为什么要三个周期：两臂都必须从「同样的冷状态」出发（VRAM 专家缓存刚填完），
否则 10 臂用的是跑了 10 小时的热缓存，20 臂是冷缓存，比的是冷热不是参数。

安全：
  · 起手断言「只有一个引擎持卡」（/sys/class/kfd/kfd/proc 计数 == 1），否则不动；
  · config 先整份备份，finally 必还原并**字节校验 md5**；
  · 每步都写 ABLOG，ssh 断了也能从日志复原过程；
  · 单次重启等待上限 300 s，超时就恢复并退出。
"""
import io
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
BAK = "/home/albus/strata166/tmp/w1035/cfg_poolworkers.bak"
ABLOG = "/home/albus/strata166/tmp/w1035/ab_progress.log"
C = "strata166-407"
ORIG_MD5 = None


def log(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    with io.open(ABLOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def sh(cmd, timeout=120):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def md5(p):
    rc, out = sh("md5sum %s" % p)
    return out.split()[0] if rc == 0 and out.strip() else ""


def kfd_count():
    try:
        return len(os.listdir("/sys/class/kfd/kfd/proc"))
    except OSError:
        return -1


def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=5) as r:
            d = json.loads(r.read())
        return d.get("status") == "ok" and d.get("loaded") is True
    except Exception:
        return False


def wait_health(limit=300):
    t0 = time.time()
    while time.time() - t0 < limit:
        if health():
            return time.time() - t0
        time.sleep(5)
    return -1


def set_workers(n):
    d = json.load(io.open(CFG, encoding="utf-8-sig"))
    a = d["args"]
    i = a.index("--pool-workers")
    a[i + 1] = str(n)
    with io.open(CFG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return int(a[i + 1])


def restart():
    sh("docker restart -t 30 %s" % C, timeout=120)
    return wait_health()


def ask(prompt, maxtok=128):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": maxtok, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    dt = time.time() - t0
    u = d.get("usage", {})
    return u.get("prompt_tokens"), u.get("completion_tokens"), dt


def last_cache_line():
    rc, out = sh("docker logs --tail 40 %s 2>&1 | grep 'expert cache' | tail -1" % C)
    return out.strip()


def parse(line):
    """done: N tokens in X s (Y tok/s) ... expert cache Z% hit"""
    import re
    m = re.search(r"\(([0-9.]+) tok/s\)", line)
    h = re.search(r"expert cache ([0-9.]+)% hit", line)
    return (float(m.group(1)) if m else None, float(h.group(1)) if h else None)


def main():
    global ORIG_MD5
    V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar "
         "papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu red green blue cyan "
         "magenta yellow black white orange purple silver golden copper north south east west up down "
         "left right front back inner outer river stone cloud forest metal glass paper cotton salt "
         "pepper sugar lemon olive coral ivory amber ruby jade onyx pearl quartz topaz cobalt indigo").split()

    if kfd_count() != 1:
        log("ABORT: KFD 持卡进程数 = %d（要求 1）" % kfd_count())
        return 1
    if not health():
        log("ABORT: 起手 /health 不是 ok")
        return 1
    shutil.copy2(CFG, BAK)
    ORIG_MD5 = md5(CFG)
    log("START backup=%s orig_md5=%s kfd=1" % (BAK, ORIG_MD5))

    results = {}
    try:
        for tag, n in (("w10", 10), ("w20", 20)):
            got = set_workers(n)
            t = restart()
            if t < 0:
                log("ABORT: %s 重启后 300 s 未健康" % tag)
                return 1
            log("%s workers=%d health_after=%.1fs cfg_md5=%s" % (tag, got, t, md5(CFG)))
            time.sleep(5)
            rows = []
            for i in range(6):
                rng = random.Random(20261107 + i)         # 两臂用**同一批**提示，内容相同
                prompt = " ".join(rng.choice(V) for _ in range(1200 // 6))
                pt, ct, dt = ask(prompt)
                line = last_cache_line()
                tps, hit = parse(line)
                rows.append((pt, ct, dt, tps, hit))
                log("  %s #%d prompt=%s gen=%s wall=%.2fs engine=%.1f tok/s hit=%.1f%%"
                    % (tag, i, pt, ct, dt, tps or -1, hit if hit is not None else -1))
            results[tag] = rows
    finally:
        shutil.copy2(BAK, CFG)
        t = restart()
        now = md5(CFG)
        log("RESTORE md5=%s (orig %s) match=%s health_after=%.1fs"
            % (now, ORIG_MD5, now == ORIG_MD5, t))

    log("==" * 12)
    for tag, rows in results.items():
        tps = [r[3] for r in rows if r[3]]
        hit = [r[4] for r in rows if r[4] is not None]
        if tps:
            mean = sum(tps) / len(tps)
            cv = (sum((x - mean) ** 2 for x in tps) / len(tps)) ** 0.5 / mean * 100
            log("%s: decode mean=%.1f tok/s  CV=%.1f%%  n=%d  min=%.1f max=%.1f  hit_mean=%.1f%%"
                % (tag, mean, cv, len(tps), min(tps), max(tps), sum(hit) / len(hit) if hit else -1))
    if len(results) == 2:
        a = [r[3] for r in results["w10"] if r[3]]
        b = [r[3] for r in results["w20"] if r[3]]
        if a and b:
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            ca = (sum((x - ma) ** 2 for x in a) / len(a)) ** 0.5 / ma * 100
            cb = (sum((x - mb) ** 2 for x in b) / len(b)) ** 0.5 / mb * 100
            band = 2 * max(ca, cb)
            log("DELTA w20 vs w10 = %+.1f%%  (2xCV band = %.1f%%)  => %s"
                % ((mb / ma - 1) * 100, band,
                   "超带" if abs((mb / ma - 1) * 100) > band else "带内（不可分辨）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
