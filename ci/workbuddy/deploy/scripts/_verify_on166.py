# -*- coding: utf-8 -*-
"""权重传输收尾：读本机日志的 size 核对结果 + 在 166 后台启动 sha256 全量校验。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

print('=== 本机：传输日志尾部 ===')
t = open(r'D:\strata166\logs\_push_weights.txt', encoding='utf-8', errors='replace').read()
print('\n'.join(t.strip().splitlines()[-14:]))
print()

# 166 上后台跑 sha256 全量校验（expected 值来自 setup.py 的 UNSLOTH_SHARDS）
EXPECT = {
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf': '4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082',
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf': '3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9',
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf': '56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3',
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf': '753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a',
}
lines = []
for n, s in EXPECT.items():
    lines.append('printf "%s " "%s"; sha256sum "/home/albus/strata166/weights/%s" | cut -d" " -f1'
                 % (n, n, n))
body = '\n'.join(lines)

script = '''set +e
LOG=/home/albus/strata166/logs/verify-weights.log
cat > /tmp/_vfix.sh <<'EOF'
%s
EOF
setsid nohup bash /tmp/_vfix.sh > $LOG 2>&1 < /dev/null &
echo "sha256 pid=$!"
sleep 3
echo "--- 当前 ---"; cat $LOG
echo
echo "--- 权重 size 一览 ---"
ls -l /home/albus/strata166/weights/
echo
echo "--- 与 setup.py 钉死值比对（size）---"
for kv in %s; do
  f=${kv%%=*}; want=${kv##*=}
  have=$(stat -c %%s "/home/albus/strata166/weights/$f" 2>/dev/null)
  if [ "$have" = "$want" ]; then echo "  OK      $f  $have"; else echo "  BAD     $f  have=$have want=$want"; fi
done
''' % (body, ' '.join('%s=%d' % (n, int(s2, 0)) for n, s2 in [
    ('Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf', '10946624'),
    ('Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf', '49859583136'),
    ('Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf', '49376141504'),
    ('Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf', '12087983520'),
]))

b64 = base64.b64encode(script.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=600)
print('=== 166 ===')
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
