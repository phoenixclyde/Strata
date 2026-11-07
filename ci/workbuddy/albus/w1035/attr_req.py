#!/usr/bin/env python3
"""Name the file behind a request's disk reads.  Needs root (smaps of another uid's process).

  sudo -n python3 attr_req.py [prompt_chars] [max_tokens]

Method (no guessing): snapshot every VMA's Rss from /proc/<engine>/smaps, fire one cold prompt,
snapshot again.  The mapping whose Rss grew by ~the same number of bytes that /proc/<pid>/io
reports for read_bytes IS the file that was read.  Nothing else is asserted.
"""
import json
import os
import random
import sys
import time
import urllib.request


def engine_pid():
    for line in os.popen("pgrep -f '^/data/bin/strata-0\\.1'").read().split():
        return int(line)
    return 0


def io(pid):
    d = {}
    for line in open("/proc/%d/io" % pid):
        k, _, v = line.partition(":")
        d[k] = int(v)
    return d


def rss_map(pid):
    """path -> total Rss (KiB)"""
    out = {}
    name = None
    with open("/proc/%d/smaps" % pid) as f:
        for line in f:
            if line[0].isdigit() or (line[0] in "abcdef" and "-" in line[:20] and " " in line[:20]):
                parts = line.split()
                name = parts[5] if len(parts) >= 6 else "[anon]"
            elif line.startswith("Rss:"):
                out[name] = out.get(name, 0) + int(line.split()[1])
    return out


def disk():
    r = {}
    for line in open("/proc/diskstats"):
        p = line.split()
        if p[2] in ("nvme0n1", "sda"):
            r[p[2]] = int(p[5]) * 512
    return r


def main():
    nch = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    mt = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    pid = engine_pid()
    prompt = " ".join(random.choice(
        "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november "
        "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu red green "
        "blue cyan magenta yellow black white orange purple silver golden copper north south east "
        "west up down left right front back inner outer".split()) for _ in range(nch // 6))

    a_io, a_rss, a_disk = io(pid), rss_map(pid), disk()
    t0 = time.time()
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mt, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    dt = time.time() - t0
    b_io, b_rss, b_disk = io(pid), rss_map(pid), disk()

    rb = b_io["read_bytes"] - a_io["read_bytes"]
    print("request: %s prompt tokens, wall %.2fs" % (d.get("usage", {}).get("prompt_tokens"), dt))
    print("engine read_bytes = %.2f MB   rchar = %.2f MB" % (rb / 1e6, (b_io["rchar"] - a_io["rchar"]) / 1e6))
    for k in b_disk:
        print("disk %-8s read = %+.2f MB" % (k, (b_disk[k] - a_disk[k]) / 1e6))

    print("\n%-64s %10s" % ("mapping (Rss growth)", "MiB"))
    rows = []
    for k, v in b_rss.items():
        dv = v - a_rss.get(k, 0)
        if abs(dv) > 512:                 # >0.5 MiB
            rows.append((dv, k))
    for dv, k in sorted(rows, reverse=True)[:12]:
        print("%-64s %10.1f" % (k[:64], dv / 1024))
    tot = sum(dv for dv, _ in rows) / 1024
    print("\nsum of mapping growth: %.1f MiB" % tot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
