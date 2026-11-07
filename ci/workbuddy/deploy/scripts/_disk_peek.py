# -*- coding: utf-8 -*-
"""166：第五轮进度 + 磁盘/温度/负载（查基线漂移的原因）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
echo "=== 第五轮已完成的读数（最后 6 条）==="
docker exec strata166 bash -lc 'grep -E "prompt 18074 tokens = 0 reused" /data/strata-ud-q4_k_xl.log | tail -6'
echo
echo "=== 当前 arm 的配置 ==="
docker exec strata166 bash -lc 'python3 -c "
import json;a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"];print(\" \".join(map(str,a)))"'
docker exec strata166 bash -lc 'ps -eo pid,etimes,args | grep -E "serve/[s]erver.py" | head -1'
echo
echo "=== 磁盘：块设备与累计读写（查 SSD 状态）==="
lsblk -d -o NAME,ROTA,SIZE,MODEL 2>/dev/null | head -8
echo "--- 累计扇区读写 / 队列深度 / 等时 ---"
for d in /sys/block/sd* /sys/block/nvme*; do
  [ -e "$d/stat" ] || continue
  n=$(basename $d)
  set -- $(cat $d/stat)
  echo "$n  read_sectors=$3 write_sectors=$7 io_ms=$10"
done
echo "--- 当前 I/O 负载 ---"
head -1 /proc/loadavg
echo
echo "=== 温度 ==="
sensors 2>/dev/null | grep -iE "Composite|Temp|Tctl|fan" | head -10 || echo "(sensors 不可用)"
for h in /sys/class/hwmon/hwmon*/; do
  n=$(cat $h/name 2>/dev/null)
  t=$(cat $h/temp1_input 2>/dev/null)
  [ -n "$t" ] && echo "$n temp1=$((t/1000))C"
done
echo
echo "=== docker exec 内的 free / 宿主可用内存 ==="
docker exec strata166 bash -lc 'free -g | head -2'
echo
echo "=== 当前 8090 ==="
docker exec strata166 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''

b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('--- STDERR ---'); print(e[:400])
