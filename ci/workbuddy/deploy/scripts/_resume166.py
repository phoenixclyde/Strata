# -*- coding: utf-8 -*-
"""① 上游 0.1.40.1 取件情况 ② 核实 166 是否真在线 + 只读盘点（含 Z0 三件现值）"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

# ---------- ① 上游取件 ----------
print('=' * 76)
print('① 上游 v0.1.40.1 取件')
print('=' * 76)
D = r'D:\strata166\upstream\v0.1.40.1'
for f in ['_fetch.txt', '_listing.txt']:
    p = os.path.join(D, f)
    if os.path.exists(p):
        print('--- %s ---' % f)
        print(open(p, encoding='utf-8', errors='replace').read())
print('--- 下载整包进度 ---')
p = r'D:\strata166\logs\_dl_0.1.40.1.txt'
print(open(p, encoding='utf-8', errors='replace').read()[-1200:] if os.path.exists(p) else '(无日志)')
zp = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
print('zip exists=%s size=%s' % (os.path.exists(zp), os.path.getsize(zp) if os.path.exists(zp) else '-'))

# ---------- ② 166 在线核实 + 只读盘点 ----------
print()
print('=' * 76)
print('② 166 在线核实 + 只读盘点')
print('=' * 76)
import socket
for pt in (22, 4096, 8090):
    s = socket.socket(); s.settimeout(3)
    rc = s.connect_ex(('192.168.50.166', pt)); s.close()
    print('  tcp %-5d -> %s' % (pt, 'OPEN' if rc == 0 else 'DOWN(rc=%d)' % rc))

SC = r'''
set +e
echo "--- 谁在线 / 开机时刻 / boot_id ---"
uptime -s; cat /proc/sys/kernel/random/boot_id; uptime
echo
echo "--- 开机闸门：sdma1 / page1 / ring ---"
CNT=$(sudo -n dmesg 2>/dev/null | grep -c "IB test failed on sdma1")
if [ -z "$CNT" ]; then echo "sdma1=FAIL_EMPTY"; else echo "sdma1=$CNT"; fi
echo
echo "--- 显存（干净地板应是 10,862,592 B 左右）---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Total"
echo
echo "--- Z0 三件现值（只读，不改）---"
echo -n "perflevel: "; rocm-smi -d 0 --showperflevel 2>/dev/null | grep -iE "Performance Level" | tail -1
echo -n "governor : "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
echo -n "thp      : "; head -1 /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null
echo
echo "--- 容器 ---"
docker ps -a --format "{{.Names}}|{{.Status}}|{{.Image}}" | head -12
echo
echo "--- 我们的资产是否还在 ---"
ls -l /home/albus/strata166/transfer/ 2>/dev/null | tail -6
sudo -n docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}" 2>/dev/null | grep -i strata
echo
echo "--- 磁盘 ---"
df -h / | tail -1
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
try:
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=180)
    print(r.stdout.decode('utf-8', 'replace'))
    e = r.stderr.decode('utf-8', 'replace')
    if e.strip():
        print('  [stderr]', e.strip()[:300])
except Exception as ex:
    print('  SSH 失败:', str(ex)[:200])
