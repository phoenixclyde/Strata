#!/usr/bin/env python3
"""Conformance run of skill `engine-io-attribution` S1-S6, executed on 166 as root.

Read-only except for the two inference requests it sends (same prompt twice: cold then warm).
Prints each step's raw output so the skill's claims can be checked against numbers.
"""
import json
import os
import subprocess
import time
import urllib.request

ENGINE_RX = "/data/bin/strata-0.1"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def disks():
    d = {}
    for line in open("/proc/diskstats"):
        p = line.split()
        name = p[2]
        if name.startswith(("nvme", "sd")) and not name[-1].isdigit():
            d[name] = int(p[5]) * 512
    return d


def engine_pid():
    out = sh("pgrep -f '%s' | head -1" % ENGINE_RX)
    return int(out) if out.isdigit() else 0


def io(pid):
    d = {}
    for line in open("/proc/%d/io" % pid):
        k, _, v = line.partition(":")
        d[k] = int(v)
    return d


def smaps(pid):
    """S3: aggregate Rss per backing file (KernelPageSize-independent, kB)."""
    agg, cur = {}, ""
    for line in open("/proc/%d/smaps" % pid, errors="replace"):
        if "-" in line.split()[0] and line[0] in "0123456789abcdef":
            parts = line.rstrip("\n").split()
            cur = parts[5] if len(parts) >= 6 else "[anon]"
        elif line.startswith("Rss:"):
            agg[cur] = agg.get(cur, 0) + int(line.split()[1])
    return agg


def ask(prompt, maxtok=8):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": maxtok, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return d.get("usage", {}), time.time() - t0


def main():
    print("== S1 空闲基线（10 s） ==")
    a = disks()
    time.sleep(10)
    b = disks()
    idle = {k: (b[k] - a.get(k, 0)) for k in b}
    for k, v in idle.items():
        print("   %-8s %8.1f KB/s" % (k, v / 10240.0))
    idle_total = sum(idle.values())
    print("   -> 空闲读总量 %.3f MB ⇒ %s" % (idle_total / 1e6,
          "请求驱动" if idle_total < 2e6 else "有后台在读，后续归因无效"))

    pid = engine_pid()
    print("\n== pid = %d ==" % pid)
    if not pid:
        return 1

    import random
    rng = random.Random()
    V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november "
         "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu red green "
         "blue cyan magenta yellow black white orange purple silver golden copper north south east "
         "west up down left right front back inner outer").split()
    prompt = " ".join(rng.choice(V) for _ in range(4000 // 6))

    for label in ("COLD", "WARM"):
        s0, i0, r0 = smaps(pid), io(pid), time.time()
        u, dt = ask(prompt)
        s1, i1, r1 = smaps(pid), io(pid), time.time()
        rb = i1["read_bytes"] - i0["read_bytes"]
        rc = i1["rchar"] - i0["rchar"]
        dk = disks().get("nvme0n1", 0)
        delta = sorted(((v - s0.get(k, 0), k) for k, v in s1.items()), reverse=True)[:3]
        print("\n== %s 请求 ==" % label)
        print("   prompt_tokens=%s wall=%.2fs" % (u.get("prompt_tokens"), dt))
        print("   S2 engine read_bytes=%.2f MB  rchar=%.2f MB  ⇒ %s"
              % (rb / 1e6, rc / 1e6, "mmap 缺页" if rb > 5e6 and rc < 0.2e6 else
                 ("read() 系统调用" if rc > 1e6 else "几乎无读")))
        print("   S3 smaps Rss 增量 top3:")
        for dkb, name in delta:
            print("      %+9.1f MiB  %s" % (dkb / 1024.0, name[:90]))
        top = delta[0][1] if delta and delta[0][0] > 1024 else ""
        if top and os.path.isfile(top):
            rss = s1.get(top, 0) * 1024
            size = os.path.getsize(top)
            print("   S4 驻留率: %s = %.1f MiB / %.2f GiB = %.1f%%"
                  % (os.path.basename(top), rss / 2**20, size / 2**30, 100.0 * rss / size))

    print("\n== S6 对账 ==")
    up = sh("awk '{print int($1)}' /proc/uptime")
    nreq = sh("docker logs strata166-407 2>&1 | grep -c 'expert cache .* hit'")
    total = sh("grep -E 'read_bytes' /proc/%d/io" % pid).split()[-1]
    print("   uptime=%ss requests=%s engine累计 read_bytes=%.1f GB"
          % (up, nreq, int(total) / 1e9))
    print("   -> 平均 %.2f MB/s（= 请求数×每次读数 / 运行秒数 的量级核对）"
          % (int(total) / 1e6 / max(int(up), 1)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
