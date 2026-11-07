# -*- coding: utf-8 -*-
"""IQ4_XS 部署 v2：确认容器真的在跑 → pack → 写配置 → 起 serve → 取数。
教训：docker start 返回 0 不等于 exec 可用；必须 poll {{.State.Running}}。
      curl 的 -w '%{http_code}' 绝不能经过 % 格式化（会被吃掉），一律用字符串拼接。
"""
import base64, json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

C = 'strata166-401'
GGUF1 = '/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
PACK = '/data/packs/ud-iq4_xs'
CONF = '/data/strata-ud-iq4_xs.json'
LOG = '/data/strata-ud-iq4_xs.log'
NAME = 'qwen3.8-flash-next-ud-iq4_xs'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def ensure_running():
    print('[1] 确保 %s 在跑（docker start + poll .State.Running）' % C, flush=True)
    ssh("docker start %s 2>&1; echo start_rc=$?" % C, 300)
    for i in range(30):
        o, _ = ssh("docker inspect -f '{{.State.Running}}' %s 2>&1" % C, 120)
        st = o.strip().splitlines()[-1].strip() if o.strip() else '?'
        if st == 'true':
            print('    Running=true @ %ds' % (i * 2), flush=True)
            # 容器内 python 就绪
            o2, _ = ssh("docker exec %s bash -lc 'python3 -c \"print(1)\"'" % C, 120)
            if '1' in o2:
                print('    exec 可用', flush=True)
                return True
        time.sleep(2)
    raise SystemExit('容器未就绪')


def http_code():
    # 注意：不用 % 格式化，%{http_code} 必须原样到达 curl
    cmd = ("docker exec " + C + " bash -lc 'curl -s -o /dev/null -w \"%{http_code}\" "
           "http://127.0.0.1:8090/v1/models; echo; tail -1 /data/serve-run.log 2>/dev/null'")
    o, _ = ssh(cmd, 120)
    lines = o.strip().splitlines()
    return (lines[0].strip() if lines else ''), (lines[-1] if lines else '')


ensure_running()

want = sys.argv[1:] or ['pack', 'conf', 'start', 'bench']

if 'pack' in want:
    print()
    print('[2] iq_pack --compat-bf16（%s）' % PACK, flush=True)
    o, e = ssh("docker exec %s bash -lc 'cd /src && STRATA_GGUF_PY=/src/third_party/llama.cpp/gguf-py "
               "python3 tools/iq_pack.py --gguf %s --out %s --compat-bf16; echo iq_pack_rc=$?'"
               % (C, GGUF1, PACK), 3600)
    print(o[-3000:])
    if e.strip():
        print('ERR', e[:400])
    o, _ = ssh("docker exec %s bash -lc 'ls -l %s; echo ---tokenizer---; ls %s/tokenizer | head -5'"
               % (C, PACK, PACK), 300)
    print(o)

if 'conf' in want:
    print()
    print('[3] 写配置 %s' % CONF, flush=True)
    cfg = {
        "exe": "/src/build-906/strata",
        "args": [
            "--pack", PACK,
            "--native", GGUF1,
            "--resident-budget-gib", "76",
            "--expert-profile", "/src/data/expert-profile.bin",
            "--expert-cache", "auto",
            "--spec", "4",
            "--spec-min-p", "0.5",
            "--mtp", "/data/mtp/rt",
            "--max-context", "131072",
            "--kv", "int8",
            "--prefill", "auto",
        ],
        "cwd": "/src",
        "tokenizer": PACK + "/tokenizer",
        "model_name": NAME,
        "log": LOG,
        "host": "0.0.0.0",
        "port": 8090,
    }
    body = json.dumps(cfg, indent=1)
    # 用 python 在容器内写，避免 shell 引号地狱
    b64 = base64.b64encode(body.encode('utf-8')).decode('ascii')
    o, e = ssh("echo %s | base64 -d | docker exec -i %s bash -lc 'cat > %s'; "
               "docker exec %s bash -lc 'cat %s; python3 -c \"import json;json.load(open(chr(39)+\\\"%s\\\"+chr(39)));print(\\\"JSON OK\\\")\"'"
               % (b64, C, CONF, C, CONF, CONF), 300)
    print(o)
    if e.strip():
        print('ERR', e[:400])

if 'start' in want:
    print()
    print('[4] 停掉可能占 8090 的容器并起 serve', flush=True)
    o, _ = ssh("for n in strata166 %s; do if docker ps --format "
               "'{{.Names}}' | grep -qx \"$n\"; then docker stop -t 20 \"$n\" >/dev/null 2>&1; echo \"stopped $n\"; fi; done; "
               "sleep 3; docker start %s >/dev/null 2>&1; echo restarted" % (C, C), 600)
    print(o)
    ensure_running()
    o, _ = ssh("docker exec -d %s bash -lc 'cd /src && setsid nohup python3 serve/server.py "
               "--engine strata --config %s --port 8090 > /data/serve-run.log 2>&1 < /dev/null'; "
               "sleep 5; docker exec %s bash -lc 'ps -eo pid,args | grep -c \"[s]erve/server.py\"'"
               % (C, CONF, C), 300)
    print('  启动后 server.py 进程数=%s' % o.strip().splitlines()[-1:])

    print()
    print('[5] 等就绪（HTTP 探针，最多 12 分钟）', flush=True)
    ready = False
    for i in range(36):
        time.sleep(20)
        code, tail = http_code()
        print('  [%3ds] http=%s  %s' % ((i + 1) * 20, code, tail[:105]), flush=True)
        if code == '200':
            ready = True
            break
    if not ready:
        o, _ = ssh("docker exec %s bash -lc 'echo \"=== serve-run 尾 30 ===\"; tail -30 /data/serve-run.log; "
                   "echo; echo \"=== 引擎日志尾 25 ===\"; tail -25 %s'" % (C, LOG), 300)
        print(o[-3500:])
        raise SystemExit('NOT READY')

if 'bench' in want:
    print()
    print('[6] 取读数（与 UD-Q4 同一脚本 /data/bench_ver.py）', flush=True)
    o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py UD-IQ4_XS 2>&1' % C, 3600)
    print(o)
    print()
    print('[7] 资源快照')
    o, _ = ssh("docker exec %s bash -lc 'grep -E \"expert cache|resident RAM|PLE on|session is up\" %s | tail -6; "
               "echo ---hit rate---; grep -E \"expert cache hit rate\" %s | tail -3' ; "
               "echo ---vram---; rocm-smi --showmemuse 2>/dev/null | grep -i vram | head -2; "
               "echo ---mem---; free -g | head -2" % (C, LOG, LOG), 300)
    print(o)
