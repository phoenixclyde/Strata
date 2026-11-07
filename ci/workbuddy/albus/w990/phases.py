#!/usr/bin/env python3
# 解析 prefill timing 行：相位 ms 与 每千 token 的 ms
import re, subprocess, sys

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
lines = subprocess.run(["grep", "-a", "prefill timing: .* tokens, GPU timeline", LOG],
                       capture_output=True, text=True).stdout.strip().splitlines()
want = [2056, 15757]

def parse(line):
    head = re.match(r".*?(\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms: (.*)$", line)
    if not head:
        return None
    n, gpu, wall, staging, rest = head.groups()
    phases = {}
    for m in re.finditer(r"([a-z0-9+: /]+?) (\d+) \((\d+\.\d)%\)", rest):
        phases[m.group(1).strip()] = int(m.group(2))
    return int(n), int(gpu), int(wall), int(staging), phases

for w in want:
    for line in reversed(lines):
        r = parse(line)
        if r and r[0] == w:
            n, gpu, wall, staging, ph = r
            print("\n=== %d tokens | GPU %d ms (%.3f ms/tok) | wall %d | staging %d ===" % (n, gpu, gpu / n, wall, staging))
            top = sorted(ph.items(), key=lambda x: -x[1])[:10]
            for k, v in top:
                print("  %-22s %6d ms  %5.3f ms/tok" % (k, v, v / n))
            break
