# C1 推送 + 重启 + 验收（166）
import subprocess, base64, time, sys, hashlib, os

HOST = "albus@192.168.50.166"
LOCAL = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
REMOTE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"


def run(script, timeout=180):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


md5 = hashlib.md5(open(LOCAL, "rb").read()).hexdigest()
print("local md5:", md5, "bytes:", os.path.getsize(LOCAL))

# 1) 备份远端 config
rc, o, e = run("cp -a %s %s.bak_w776c1_$(date +%%Y%%m%%d_%%H%%M%%S) && ls -1 %s.bak_w776c1_* | tail -2" % (REMOTE, REMOTE, REMOTE))
print("[backup] rc=%d\n%s%s" % (rc, o, e))

# 2) 推送（base64 走 stdin，远端 base64 -d 精确还原字节，无尾部换行）
payload = base64.b64encode(open(LOCAL, "rb").read()).decode("ascii")
script = "echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s && wc -c %s" % (
    payload, REMOTE, REMOTE, REMOTE, REMOTE, REMOTE)
rc, o, e = run(script)
print("[push] rc=%d\n%s%s" % (rc, o, e))
if md5 not in o:
    print("!! md5 不符，中止（不重启）")
    sys.exit(2)

# 3) 重启
rc, o, e = run("docker restart strata166-407 && echo RESTARTED", timeout=120)
print("[restart] rc=%d %s%s" % (rc, o, e))

# 4) 等 ready
for i in range(40):
    rc, o, e = run("curl -s --max-time 4 http://127.0.0.1:8090/health", timeout=30)
    if '"loaded": true' in o or '"loaded":true' in o:
        print("[health] ready after ~%ds: %s" % (i * 3, o.strip()[:200]))
        break
    time.sleep(3)
else:
    print("[health] NOT READY in 120s:", o, e)

# 5) 关键读数
rc, o, e = run(r'''
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); e=d['engine']; hw=d['hardware']
print('version',e['version'],'| kv',e['kv'],'| slots',e['expert_slots'],'| cache_mib',e['expert_cache_mib'])
print('vram_free',e['vram_free_mib'],'| pool_workers',e['pool_workers'],'| prefill_cap',e['prefill_cap'],'| context',e['context'])
print('arena_mib',e['arena_mib'],'| spec',e['spec'],'| gpu_util',hw['gpu_util'])
"
echo '--- startup lines ---'
docker logs strata166-407 2>&1 | grep -E "pool workers|aux cpus|VRAM free with everything|expert cache [0-9]+ slots|below 512|prefill chunk" | tail -8
''', timeout=60)
print("[metrics]\n" + o + e)
