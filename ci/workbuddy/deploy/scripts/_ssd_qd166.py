# -*- coding: utf-8 -*-
"""166：SSD 队列深度扫描 —— 判「盘真退化」还是「QD1 延迟高但吞吐够」"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
cat > /home/albus/strata166/data/qd.py <<'PYEOF'
import os, mmap, random, time, threading

P = '/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf'
sz = os.path.getsize(P)
BS = 4096
TOT = 4000

def worker(fd, offs, out, idx):
    buf = mmap.mmap(-1, BS)
    lat = []
    for off in offs:
        t = time.perf_counter()
        os.preadv(fd, [buf], off)
        lat.append(time.perf_counter() - t)
    out[idx] = lat

for qd in (1, 4, 16, 64):
    per = TOT // qd
    fd = os.open(P, os.O_RDONLY | os.O_DIRECT)
    offs = [random.randrange(0, (sz - BS) // BS) * BS for _ in range(TOT)]
    out = [None] * qd
    ths = [threading.Thread(target=worker, args=(fd, offs[i*per:(i+1)*per], out, i)) for i in range(qd)]
    t0 = time.perf_counter()
    for t in ths: t.start()
    for t in ths: t.join()
    dt = time.perf_counter() - t0
    os.close(fd)
    lat = sorted(x for l in out if l for x in l)
    n = len(lat)
    print('QD=%-3d  n=%-5d  %.0f IOPS  %.2f MB/s  p50=%.0fus  p95=%.0fus  mean=%.0fus'
          % (qd, n, n/dt, n*BS/dt/1e6, lat[n//2]*1e6, lat[int(n*0.95)]*1e6, sum(lat)/n*1e6), flush=True)
PYEOF
docker exec strata166 python3 -u /data/qd.py 2>&1
echo
echo "=== 文件系统与挂载（看是否 ext4 / 有无 barrier 等）==="
findmnt -no SOURCE,FSTYPE,OPTIONS / 2>/dev/null
echo "--- /home 所在 ---"
findmnt -no SOURCE,FSTYPE,OPTIONS /home 2>/dev/null
echo
echo "=== 盘型号与 SATA 链路速率 ==="
sudo -n hdparm -I /dev/sda 2>/dev/null | egrep -i "Model Number|Firmware|Transport|speed|Nominal" | head -8
cat /sys/block/sda/queue/rotational /sys/block/sda/queue/scheduler 2>/dev/null
echo "--- 链路 ---"
dmesg 2>/dev/null | grep -iE "ata[0-9]+: SATA link|ata[0-9]+\.00: configured" | tail -4
sudo -n smartctl -H -A /dev/sda 2>/dev/null | egrep -i "result|Reallocated|Pending|Uncorrect|Temperature|Wear|Percent|Media|Power_On" | head -12
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:600])
