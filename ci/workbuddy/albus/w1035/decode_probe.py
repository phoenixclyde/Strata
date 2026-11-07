#!/usr/bin/env python3
"""Decode probe: is decode slow/unstable, and does it read the disk?

  sudo -n python3 decode_probe.py [runs] [max_tokens]

Fixed tiny prompt (so prefill is negligible), identical request repeated: the spread of
tok/s IS the instability, and read_bytes tells whether the reads live in the decode段.
"""
import json
import os
import sys
import time
import urllib.request

PID = os.popen("pgrep -f '^/data/bin/strata-0\\.1'").read().split()[0]


def io():
    d = {}
    for line in open("/proc/%s/io" % PID):
        k, _, v = line.partition(":")
        d[k] = int(v)
    return d


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    mt = int(sys.argv[2]) if len(sys.argv) > 2 else 128
    ts, rb = [], []
    for i in range(runs):
        a = io()
        body = json.dumps({"model": "x",
                           "messages": [{"role": "user", "content": "Count from 1 to 200, one number per line."}],
                           "max_tokens": mt, "temperature": 0.0}).encode()
        r = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                   headers={"Content-Type": "application/json"})
        t0 = time.time()
        d = json.loads(urllib.request.urlopen(r, timeout=600).read())
        dt = time.time() - t0
        b = io()
        ct = d.get("usage", {}).get("completion_tokens") or 0
        ts.append(ct / dt)
        rb.append((b["read_bytes"] - a["read_bytes"]) / 1e6)
        print("run %d: %3d tok in %6.2f s = %5.1f tok/s   read %6.2f MB" % (i + 1, ct, dt, ts[-1], rb[-1]))
    m = sum(ts) / len(ts)
    sd = (sum((x - m) ** 2 for x in ts) / len(ts)) ** 0.5
    print("\nmean %.1f tok/s  sd %.1f  CV %.1f%%   read mean %.2f MB  total %.2f MB"
          % (m, sd, 100 * sd / m, sum(rb) / len(rb), sum(rb)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
