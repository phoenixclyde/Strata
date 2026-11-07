#!/usr/bin/env python3
"""R95 窗口 A：STRATA_MMQ_DEBUG_J=1 数 launch，判「665 ms 固定项是不是调度/建表」。

纯日志开关，不改数值行为；config 整份备份，finally 还原并字节校验 md5。
发一条与相位表同形状的提示（~2083 tok），取该次请求的 gemm 相位耗时 + pick_J 行数。
"""
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
BAK = "/home/albus/strata166/tmp/w1035/cfg_debugj.bak"
ABLOG = "/home/albus/strata166/tmp/w1035/debugj_progress.log"
C = "strata166-407"


def log(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    with io.open(ABLOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def sh(cmd, timeout=180):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def md5(p):
    rc, out = sh("md5sum %s" % p)
    return out.split()[0] if rc == 0 and out.strip() else ""


def kfd():
    try:
        return len(os.listdir("/sys/class/kfd/kfd/proc"))
    except OSError:
        return -1


def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=5) as r:
            return json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


def wait_health(limit=300):
    t0 = time.time()
    while time.time() - t0 < limit:
        if health():
            return time.time() - t0
        time.sleep(5)
    return -1


def main():
    if kfd() != 1:
        log("ABORT: KFD 持卡进程 %d != 1" % kfd())
        return 1
    shutil.copy2(CFG, BAK)
    orig = md5(CFG)
    log("START orig_md5=%s" % orig)
    try:
        d = json.load(io.open(CFG, encoding="utf-8-sig"))
        d.setdefault("env", {})["STRATA_MMQ_DEBUG_J"] = "1"
        with io.open(CFG, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        log("env 已加 STRATA_MMQ_DEBUG_J=1，重启")
        t = wait_health_after_restart()
        if t < 0:
            log("ABORT: 300 s 未健康")
            return 1
        log("health_after=%.1fs" % t)
        time.sleep(5)

        # 一条与相位表同形状的请求
        V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november "
             "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu red green blue "
             "cyan magenta yellow black white orange purple silver golden copper north south east west up "
             "down left right front back inner outer river stone cloud forest metal glass paper cotton").split()
        rng = random.Random(20261107)
        prompt = " ".join(rng.choice(V) for _ in range(1600))   # ~2K token（上轮 347 词只到 485）
        t0 = time.time()
        body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 4, "temperature": 0.0}).encode()
        req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=300).read())
        log("request prompt_tokens=%s wall=%.2fs" % (r.get("usage", {}).get("prompt_tokens"), time.time() - t0))
        time.sleep(1)
        rc0, out0 = sh("docker logs --since 2m %s 2>&1 | grep -c pick_J" % C)
        log("2K 请求后 pick_J 累计=%s" % out0.strip())
        prompt2 = " ".join(rng.choice(V) for _ in range(3200))   # ~4K token
        body2 = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt2}],
                            "max_tokens": 4, "temperature": 0.0}).encode()
        req2 = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body2,
                                      headers={"Content-Type": "application/json"})
        r2 = json.loads(urllib.request.urlopen(req2, timeout=300).read())
        log("request2 prompt_tokens=%s" % r2.get("usage", {}).get("prompt_tokens"))
        time.sleep(1)
        rc1, out1 = sh("docker logs --since 2m %s 2>&1 | grep -c pick_J" % C)
        log("4K 请求后 pick_J 累计=%s" % out1.strip())

        rc, out = sh("docker logs --since 3m %s 2>&1" % C)
        lines = out.splitlines()
        pj = [l for l in lines if "pick_J" in l]
        js = []
        for l in pj:
            m = re.search(r"pick_J.*?J=(\d+)", l)
            if m:
                js.append(int(m.group(1)))
        log("pick_J 行数=%d  解析到 J 的=%d" % (len(pj), len(js)))
        if js:
            from collections import Counter
            log("J 分布: %s" % dict(Counter(js).most_common(6)))
        phase = [l for l in lines if "gate" in l and ("ms" in l or "phase" in l)]
        for l in phase[-6:]:
            log("PHASE " + l.strip()[:200])
        if len(pj) > 0 and js:
            log("=> 固定项 665 ms / %d 次 pick_J = %.3f ms/launch" % (len(js), 665.0 / len(js)))
    finally:
        shutil.copy2(BAK, CFG)
        t = wait_health_after_restart()
        now = md5(CFG)
        log("RESTORE md5=%s match=%s health_after=%.1fs" % (now, now == orig, t))
    return 0


def wait_health_after_restart():
    sh("docker restart -t 30 %s" % C, timeout=120)
    return wait_health()


if __name__ == "__main__":
    sys.exit(main())
