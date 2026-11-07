#!/bin/bash
echo "===== 5 秒内各进程写字节增量 top ====="
python3 - <<'PY'
import os, time, glob
def snap():
    d = {}
    for p in glob.glob("/proc/[0-9]*/io"):
        try:
            lines = open(p).read().splitlines()
            w = int([l for l in lines if l.startswith("write_bytes")][0].split()[1])
            r = int([l for l in lines if l.startswith("read_bytes")][0].split()[1])
            pid = p.split("/")[2]
            try:
                cmd = open("/proc/%s/comm" % pid).read().strip()
            except Exception:
                cmd = "?"
            d[pid] = (cmd, r, w)
        except Exception:
            pass
    return d
a = snap(); time.sleep(5); b = snap()
out = []
for pid, (cmd, r, w) in b.items():
    if pid in a:
        dr, dw = r - a[pid][1], w - a[pid][2]
        if dr + dw > 0:
            out.append((dw, dr, pid, cmd))
for dw, dr, pid, cmd in sorted(out, reverse=True)[:8]:
    print("  %-22s pid=%-8s read=%9.2f MiB  write=%9.2f MiB" % (cmd, pid, dr/1048576.0, dw/1048576.0))
PY
echo
echo "===== 两个日志文件的 5 秒增长 ====="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
J=/var/lib/docker/containers/4f387a12e84b6cb06ada67c5ff28bffc4ac22338e5b12b1387ea16e32128d8c5/4f387a12e84b6cb06ada67c5ff28bffc4ac22338e5b12b1387ea16e32128d8c5-json.log
S1=$(stat -c %s "$L"); J1=$(stat -c %s "$J"); sleep 5; S2=$(stat -c %s "$L"); J2=$(stat -c %s "$J")
echo "  引擎日志(NVMe): $((S2-S1)) bytes/5s   size=$((S2/1048576)) MiB"
echo "  docker json(老盘): $((J2-J1)) bytes/5s   size=$((J2/1048576)) MiB"
echo
echo "===== 模型权重在 page cache 吗（Cached/arena）====="
grep -E "^(MemTotal|MemAvailable|Cached|Buffers):" /proc/meminfo
P=$(pgrep -f strata-0.1.56-090 | head -1)
sudo awk '/^(Rss|AnonHugePages):/{printf "%s=%.2fGiB ",$1,$2/1048576}' /proc/$P/smaps_rollup; echo
