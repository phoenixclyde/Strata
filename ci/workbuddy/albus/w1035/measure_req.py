#!/usr/bin/env python3
"""Attribute the disk reads to one inference request.  Read-only except for the request itself.

  python3 measure_req.py [prompt_chars] [max_tokens]

Samples, around a single /v1/chat/completions call:
  engine  read_bytes (block-layer bytes actually fetched) / rchar / majflt
  disk    nvme0n1 sectors read
and prints bytes-per-request, so a "1-2 MB/s while chatting" observation can be turned into
"X MB per request" and compared with the expert-cache miss statistics in the engine log.
"""
import json
import os
import sys
import time
import urllib.request

ENGINE_RX = "^/data/bin/strata-0\\.1"


def engine_pid():
    for line in os.popen("pgrep -f '%s'" % ENGINE_RX).read().split():
        return int(line)
    return 0


def io(pid):
    d = {}
    for line in open("/proc/%d/io" % pid):
        k, _, v = line.partition(":")
        d[k] = int(v)
    return d


def majflt(pid):
    """field 12 of /proc/<pid>/stat (not present in /proc/<pid>/io)."""
    parts = open("/proc/%d/stat" % pid).read().rsplit(") ", 1)[1].split()
    return int(parts[9])          # minflt is parts[7], majflt parts[9] after the comm split


def disk_read():
    for line in open("/proc/diskstats"):
        p = line.split()
        if p[2] == "nvme0n1":
            return int(p[5]) * 512
    return 0


def main():
    nch = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    mt = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    pid = engine_pid()
    if not pid:
        print("engine not found")
        return 1
    if len(sys.argv) > 3 and sys.argv[3] == "rand":
        import random
        rng = random.Random()
        V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
             "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu "
             "red green blue cyan magenta yellow black white orange purple silver golden copper "
             "north south east west up down left right front back inner outer").split()
        prompt = " ".join(rng.choice(V) for _ in range(nch // 6))
    else:
        prompt = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet " * 200)[:nch]
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mt, "temperature": 0.0}).encode()

    i0, d0, t0, f0 = io(pid), disk_read(), time.time(), majflt(pid)
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    dt = time.time() - t0
    i1, d1, f1 = io(pid), disk_read(), majflt(pid)

    pt = d.get("usage", {}).get("prompt_tokens")
    ct = d.get("usage", {}).get("completion_tokens")
    rb = i1["read_bytes"] - i0["read_bytes"]
    rc = i1["rchar"] - i0["rchar"]
    mf = f1 - f0
    dk = d1 - d0
    print("request: prompt_tokens=%s completion_tokens=%s wall=%.2fs" % (pt, ct, dt))
    print("engine  read_bytes=%.2f MB   rchar=%.2f MB   majflt=%d" % (rb / 1e6, rc / 1e6, mf))
    print("disk    nvme0n1 read=%.2f MB" % (dk / 1e6))
    if pt:
        print("per prompt token: read_bytes=%.1f KB  rchar=%.1f KB" % (rb / 1e3 / pt, rc / 1e3 / pt))
    print("per request:      read_bytes=%.2f MB  wall=%.2fs  => %.2f MB/s during the request"
          % (rb / 1e6, dt, rb / 1e6 / max(dt, 1e-9)))
    print("for comparison: the engine's expert-cache line for this request is in `docker logs`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
