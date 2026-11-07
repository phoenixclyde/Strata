#!/bin/bash
F=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
echo "===== 强制读 64 MiB（O_DIRECT，绕开 page cache）前后 diskstats ====="
python3 - "$F" <<'PY'
import subprocess, sys, time
f = sys.argv[1]
def rd():
    for l in open("/proc/diskstats"):
        p = l.split()
        if p[2] == "nvme0n1p1":
            return int(p[5]), int(p[9])
    return 0, 0
a = rd()
r = subprocess.run(["dd", "if=" + f, "of=/dev/null", "iflag=direct", "bs=4K", "count=16384"],
                   capture_output=True, text=True)
b = rd()
print("  dd rc=%s  %s" % (r.returncode, r.stderr.strip().splitlines()[-1] if r.stderr else ""))
print("  nvme0n1p1 sectors read +%d (= %.1f MiB), written +%d" %
      (b[0]-a[0], (b[0]-a[0])*512/1048576.0, b[1]-a[1]))
PY
echo
echo "===== 老盘写入进程（sudo 读 /proc/*/io，5 秒增量）====="
sudo python3 - <<'PY'
import glob, time
def snap():
    d = {}
    for p in glob.glob("/proc/[0-9]*/io"):
        try:
            w = int([l for l in open(p).read().splitlines() if l.startswith("write_bytes")][0].split()[1])
            d[p.split("/")[2]] = w
        except Exception:
            pass
    return d
a = snap(); time.sleep(5); b = snap()
out = []
for pid, w in b.items():
    if pid in a and w - a[pid] > 0:
        try:
            cmd = open("/proc/%s/cmdline" % pid).read().replace("\0", " ")[:60]
        except Exception:
            cmd = "?"
        out.append((w - a[pid], pid, cmd))
for dw, pid, cmd in sorted(out, reverse=True)[:6]:
    print("  %8.2f MiB/5s  pid=%-8s %s" % (dw/1048576.0, pid, cmd))
if not out:
    print("  (窗口内无进程级写入增量，多为内核 journal/xfs metadata 回写)")
PY
