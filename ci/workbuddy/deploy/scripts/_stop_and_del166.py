# -*- coding: utf-8 -*-
"""166：先停掉占着权重的容器，再删 UD-Q4_K_XL 权重（删前列清单，删后核磁盘）。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "=== 1) 停掉占 8090 / 持有权重的容器 ==="
for n in strata166 strata166-401; do
  if docker ps --format '{{.Names}}' | grep -qx "$n"; then docker stop -t 30 "$n" >/dev/null 2>&1; echo "  stopped $n"; else echo "  $n 未运行"; fi
done
sleep 3
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata || echo "  (无 strata 容器在跑)"
echo
echo "=== 2) 删前清单（UD-Q4_K_XL） ==="
ls -l /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf 2>/dev/null
du -ch /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf 2>/dev/null | tail -1
echo "  删前磁盘:"; df -h / | tail -1
echo
echo "=== 3) 删除 ==="
rm -f /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf
echo "  rm rc=$?"
echo
echo "=== 4) 删后核对 ==="
ls -l /home/albus/strata166/weights/ 2>&1
echo "  删后磁盘:"; df -h / | tail -1
echo
echo "=== 5) 保留项（未删，说明理由） ==="
echo "  pack（~2G，派生件，重传权重即可复用）:"; du -sh /home/albus/strata166/data/packs/ud-q4_k_xl 2>/dev/null
echo "  配置（原样留着）:"; ls -l /home/albus/strata166/data/strata-ud-q4_k_xl.json
echo "  MTP（两版共用，base 模型的 MTP 张量，与量化无关）:"; du -sh /home/albus/strata166/data/mtp 2>/dev/null
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=1200)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:400])
