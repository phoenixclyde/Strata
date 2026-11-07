#!/usr/bin/env python3
# 按文件汇总 smaps 的 Rss（宿主机上跑）
import re, subprocess, sys, collections

pid = subprocess.run("pgrep -f strata-0.1.56-090 | head -1", shell=True, capture_output=True, text=True).stdout.strip()
sm = subprocess.run(["sudo", "cat", "/proc/%s/smaps" % pid], capture_output=True, text=True).stdout
cur = None
agg = collections.Counter()
sizes = collections.Counter()
for line in sm.splitlines():
    m = re.match(r"^([0-9a-f]+)-([0-9a-f]+) .*?\s(\S+)$", line)
    if m:
        cur = m.group(3)
        sizes[cur] += (int(m.group(2), 16) - int(m.group(1), 16)) / 1048576.0
        continue
    if cur and line.startswith("Rss:"):
        agg[cur] += int(line.split()[1]) / 1048576.0

print("%-70s %8s %8s" % ("file", "Rss GiB", "map GiB"))
for f, v in agg.most_common(8):
    print("%-70s %8.2f %8.2f" % (f[-70:], v, sizes[f]))
print()
print("sum Rss(file) = %.2f GiB" % sum(agg.values()))
