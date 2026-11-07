# -*- coding: utf-8 -*-
"""Strata 0.1.40.2 bench —— 三臂 ABBA（0.1.40.2 -> 0.1.40.1 -> 0.1.40.2）

设计依据（技能 §7.8）：
  · 本机存在约 12% 的、既不能归因于配置也不能归因于 arm 序号的波动
  · 所以每臂预热 1 条丢弃，再重复 3 次取中位与极差；末臂回主臂作同条件对照
配置完全一致（同一份 /data/strata-ud-iq4_xs.json，同一 pack/weights）⇒ **唯一变量 = 引擎版本**。
"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CONF = '/data/strata-ud-iq4_xs.json'
WS = '/src'
LOG = '/data/strata-ud-iq4_xs.log'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


ARMS = [
    ('0.1.40.2', 'strata166-402'),
    ('0.1.40.1', 'strata166-401'),
    ('0.1.40.2-again', 'strata166-402'),
]

print('# ' * 35)
print('Strata bench: 三臂 ABBA  配置=%s  唯一变量=引擎版本' % CONF)
print('# ' * 35, flush=True)

offsets = {}
for label, cname in ARMS:
    print()
    print('#' * 72)
    print('# ARM %-16s 容器=%s' % (label, cname))
    print('#' * 72, flush=True)

    # --- 停掉所有占 8090 的实例 ---
    o, e = ssh(r'''
set +e
for n in strata166 strata166-401 strata166-402; do
  if docker ps -a --format '{{.Names}}' | grep -qx "$n"; then docker stop -t 20 "$n" >/dev/null 2>&1; echo "stopped $n"; fi
done
sleep 3
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata || echo "(无 strata 容器在跑)"
''', 300)
    print(o.strip(), flush=True)

    # --- 记录日志起始偏移 ---
    o, _ = ssh('stat -c %%s %s 2>/dev/null || echo 0' % LOG, 60)
    off = int((o.strip().splitlines() or ['0'])[-1] or 0)
    offsets[label] = off
    print('  [log] offset = %d' % off, flush=True)

    # --- 起目标容器 ---
    o, e = ssh('''set -e
CMD=$(docker inspect %s --format '{{.Config.Cmd}}')
echo "  Cmd=$CMD"
docker start %s >/dev/null 2>&1 || true
sleep 3
docker ps --format '{{.Names}}|{{.Status}}' | grep %s || echo "  !! 未起来"
''' % (cname, cname, cname), 300)
    print(o.strip(), flush=True)

    # 若 Cmd 不含 serve/server.py，则手动 exec 起服务
    o, _ = ssh('''set +e
CMD=$(docker inspect %s --format '{{.Config.Cmd}}')
case "$CMD" in
  *serve/server.py*) echo "  [mode] Cmd 自带 serve" ;;
  *) echo "  [mode] 需手动 exec serve"
     docker exec -d %s bash -lc 'cd %s && setsid nohup python3 serve/server.py --engine strata --config %s --port 8090 > /data/serve-run.log 2>&1 < /dev/null'
     echo "  [start] exec 已发" ;;
esac
''' % (cname, cname, WS, CONF), 300)
    print(o.strip(), flush=True)

    # --- 等就绪 ---
    ready = False
    for i in range(40):
        time.sleep(15)
        o, _ = ssh('''set +e
docker exec %s bash -lc 'curl -s -m 5 -o /dev/null -w "%%{http_code}" http://127.0.0.1:8090/v1/models; echo' 2>/dev/null
docker logs --tail 1 %s 2>&1 | tail -1
''' % (cname, cname), 120)
        lines = [x for x in o.strip().splitlines() if x.strip()]
        code = lines[0].strip() if lines else ''
        tail = (lines[-1][:95] if len(lines) > 1 else '')
        print('  [%4ds] http=%-4s %s' % ((i + 1) * 15, code, tail), flush=True)
        if code == '200':
            print('  [ready @ %ds]' % ((i + 1) * 15), flush=True)
            ready = True
            break
    if not ready:
        o, _ = ssh('docker logs --tail 25 %s 2>&1; echo ---; docker exec %s bash -lc "tail -15 %s"' % (cname, cname, LOG), 180)
        print('  [!! 未就绪]'); print(o[-1800:], flush=True)
        continue

    # --- 跑 bench ---
    o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py %s 2>&1' % (cname, label), 3600)
    print(o, flush=True)

    # --- 引擎日志切片 ---
    o, _ = ssh('''sz=$(stat -c %%s %s 2>/dev/null || echo 0)
echo "  [log] offset %d -> $sz"
tail -c +%d %s 2>/dev/null | grep -E "prompt [0-9]+ tokens|drafts accepted|expert cache hit rate|resident RAM" | tail -16
''' % (LOG, off, off + 1, LOG), 180)
    print(o.strip(), flush=True)

print()
print('=' * 72)
print('=== 汇总：引擎日志里各臂的 prompt 计时行 ===')
o, _ = ssh('grep -E "prompt [0-9]+ tokens" %s | tail -24' % LOG, 180)
print(o.strip(), flush=True)
print()
print('=== VRAM / 内存 ===')
o, _ = ssh('rocm-smi --showmeminfo vram 2>/dev/null | grep -i used; free -g | head -2; df -h / | tail -1', 120)
print(o.strip(), flush=True)
print('DONE')
