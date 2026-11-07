# -*- coding: utf-8 -*-
"""166：删 UD-Q4_K_XL 权重 → 为 UD-IQ4_XS 出 pack → 写配置 → 起 serve → 取读数。

阶段（按顺序，可用 argv 只跑某一段）：
  del   删 /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf（先列清单再删）
  pack  iq_pack --compat-bf16 -> /data/packs/ud-iq4_xs
  start 写 /data/strata-ud-iq4_xs.json 并起 serve（端口 8090）
  bench 跑 /data/bench_ver.py UD-IQ4_XS
默认：全部按序执行。
"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

CONTAINER = 'strata166-401'          # 用 0.1.40.1 镜像（对拍会告诉我们哪版更好）
NEW_GGUF1 = '/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
PACK = '/data/packs/ud-iq4_xs'
CONF = '/data/strata-ud-iq4_xs.json'
LOG = '/data/strata-ud-iq4_xs.log'
MODEL_NAME = 'qwen3.8-flash-next-ud-iq4_xs'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


stages = sys.argv[1:] or ['del', 'pack', 'start', 'bench']

# ---------------- del ----------------
if 'del' in stages:
    print('#' * 72)
    print('# 阶段 1：删除 166 上的 UD-Q4_K_XL 权重（不可逆；本机留有副本可回传）')
    print('#' * 72)
    o, e = ssh(r'''
echo "=== 待删清单（删前）==="
ls -l /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf 2>/dev/null
echo "小计:"; du -ch /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf 2>/dev/null | tail -1
echo
echo "=== 删 ==="
rm -f /home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf
echo "rm rc=$?"
echo
echo "=== 删后 weights 目录 ==="
ls -l /home/albus/strata166/weights/ 2>&1
echo
echo "=== 磁盘 ==="
df -h / | tail -1
''', 900)
    print(o)
    if e.strip():
        print('ERR', e[:400])

# ---------------- pack ----------------
if 'pack' in stages:
    print('#' * 72)
    print('# 阶段 2：iq_pack --compat-bf16（UD-IQ4_XS）')
    print('#' * 72)
    o, e = ssh(r'''
docker exec %s bash -lc '
cd /src
STRATA_GGUF_PY=/src/third_party/llama.cpp/gguf-py python3 tools/iq_pack.py \
  --gguf %s \
  --out %s --compat-bf16
echo "iq_pack rc=$?"
'
echo "=== pack 产物 ==="
docker exec %s bash -lc 'ls -l %s 2>&1; echo "--- tokenizer ---"; ls %s/tokenizer 2>&1; echo "--- index 前 3 行 ---"; head -3 %s/index.txt 2>&1'
''' % (CONTAINER, NEW_GGUF1, PACK, CONTAINER, PACK, PACK, PACK), 2400)
    print(o[-4000:])
    if e.strip():
        print('ERR', e[:400])

# ---------------- start ----------------
if 'start' in stages:
    print('#' * 72)
    print('# 阶段 3：写配置并起 serve（%s，端口 8090）' % MODEL_NAME)
    print('#' * 72)
    o, e = ssh(r'''
docker exec %(c)s bash -lc 'cat > %(conf)s <<JSONEOF
{
  "exe": "/src/build-906/strata",
  "args": [
    "--pack", "%(pack)s",
    "--native", "%(g)s",
    "--resident-budget-gib", "76",
    "--expert-profile", "/src/data/expert-profile.bin",
    "--expert-cache", "auto",
    "--spec", "4",
    "--spec-min-p", "0.5",
    "--mtp", "/data/mtp/rt",
    "--max-context", "131072",
    "--kv", "int8",
    "--prefill", "auto"
  ],
  "cwd": "/src",
  "tokenizer": "%(pack)s/tokenizer",
  "model_name": "%(name)s",
  "log": "%(log)s",
  "host": "0.0.0.0",
  "port": 8090
}
JSONEOF
echo "--- 写入内容 ---"; cat %(conf)s; python3 -c "import json;json.load(open(\"%(conf)s\"));print(\"JSON OK\")"'
echo
echo "=== 停掉占 8090 的实例 ==="
for n in strata166 strata166-401; do
  if docker ps --format "{{.Names}}" | grep -qx "$n"; then docker stop -t 20 "$n" >/dev/null 2>&1; echo "stopped $n"; fi
done
sleep 3
echo "=== 起 %(c)s ==="
docker start %(c)s >/dev/null 2>&1
sleep 2
docker exec -d %(c)s bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata --config %(conf)s --port 8090 > /data/serve-run.log 2>&1 < /dev/null'
echo launched
''' % {'c': CONTAINER, 'conf': CONF, 'pack': PACK, 'name': MODEL_NAME, 'log': LOG, 'g': NEW_GGUF1}, 600)
    print(o)
    if e.strip():
        print('ERR', e[:400])

    print()
    print('[等待就绪：容器内 HTTP 探针，最多 12 分钟]')
    ready = False
    for i in range(36):
        time.sleep(20)
        o, _ = ssh("docker exec %s bash -lc 'curl -s -o /dev/null -w %%s "
                   "http://127.0.0.1:8090/v1/models; echo; tail -1 /data/serve-run.log'" % CONTAINER, 120)
        lines = o.strip().splitlines()
        code = (lines or [''])[0].strip()
        last = (lines or ['', ''])[-1]
        print('  [%3ds] http=%s  %s' % ((i + 1) * 20, code, last[:110]), flush=True)
        if code == '200':
            ready = True
            break
    if not ready:
        o, _ = ssh("docker exec %s bash -lc 'echo \"=== serve-run 尾 30 ===\"; tail -30 /data/serve-run.log; "
                   "echo; echo \"=== 引擎日志尾 25 ===\"; tail -25 %s'" % (CONTAINER, LOG), 300)
        print(o[-3500:])
        sys.exit('NOT READY')

# ---------------- bench ----------------
if 'bench' in stages:
    print('#' * 72)
    print('# 阶段 4：读读数（与 UD-Q4 完全同一套脚本 /data/bench_ver.py）')
    print('#' * 72)
    o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py UD-IQ4_XS 2>&1' % CONTAINER, 3600)
    print(o)
    print()
    print('=== 显存/内存 ===')
    o, _ = ssh(r'''
rocm-smi --showmemuse 2>/dev/null | grep -i vram | head -2
free -g | head -2
docker exec %s bash -lc 'grep -E "expert cache|resident RAM|PLE on|ready: http" %s | tail -6'
''' % (CONTAINER, LOG), 300)
    print(o)
