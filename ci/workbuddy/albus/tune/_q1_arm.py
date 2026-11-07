# -*- coding: utf-8 -*-
"""Q1 三臂实验（kv-grow）：base = 现行；nores = 去 --resident-experts；kv = 去 resident + 开 --kv-grow。
走 register(P66/P32) -> gen_config --write -> 推送 -> 重启 -> 健康 -> 读数。
用法：python _q1_arm.py base|nores|kv
健康失败会自动回滚 base。
"""
import io, os, re, sys, time, json, shutil, base64, subprocess

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py"
PUSH = r"D:/workbuddy_space/strata_ws/albus/tune/_c1_push.py"
PY = sys.executable
HOST = "albus@192.168.50.166"

ARMS = {
    "base": {"P66": "ADOPTED", "P32": "REJECTED"},
    "nores": {"P66": "REJECTED", "P32": "REJECTED"},
    "kv": {"P66": "REJECTED", "P32": "ADOPTED"},
}


def sh(script, timeout=600):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15",
                        "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


def set_arm(arm):
    st = ARMS[arm]
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    out = []
    for ln in lines:
        f = ln.split("\t")
        if len(f) > 5 and f[0] in st:
            f[5] = st[f[0]]
            ln = "\t".join(f)
        out.append(ln)
    shutil.copy2(REG, REG + ".bak_q1_" + time.strftime("%Y%m%d_%H%M%S"))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


def gen_and_push():
    subprocess.run([PY, GEN, "--write"], cwd=os.path.dirname(GEN), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([PY, PUSH], capture_output=True, text=True, timeout=900)
    return r.stdout


def health_and_read():
    script = r'''
for i in $(seq 1 100); do
  H=$(curl -s --max-time 4 http://127.0.0.1:8090/health 2>/dev/null)
  case "$H" in *'"loaded": true'*) echo "READY after $((i*3))s"; break;; esac
  sleep 3
done
echo "--- metrics ---"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); e=d['engine']; h=d['hardware']
print('slots=%s cache_mib=%s vram_free=%s kv_resident=%s' % (e['expert_slots'], e['expert_cache_mib'], e['vram_free_mib'], e['kv_resident']))
print('ram_used_mib=%.0f ram_total_mib=%.0f' % (h['ram_used']/1048576.0, h['ram_total']/1048576.0))
"
echo "--- meminfo ---"
grep -E "^(MemAvailable|SwapTotal|SwapFree):" /proc/meminfo
echo "--- kv-grow line ---"
docker logs strata166-407 2>&1 | grep -iE "kv-grow|kv grow" | tail -3
'''
    return sh(script, timeout=700)


def main():
    arm = sys.argv[1]
    assert arm in ARMS, arm
    print("=== ARM %s (P66=%s P32=%s) ===" % (arm, ARMS[arm]["P66"], ARMS[arm]["P32"]), flush=True)
    set_arm(arm)
    out = gen_and_push()
    print(out[-900:], flush=True)
    res = health_and_read()
    ok = "READY" in res
    print(res, flush=True)
    if not ok:
        print("!! 健康失败 -> 回滚 base", flush=True)
        set_arm("base")
        print(gen_and_push()[-400:], flush=True)
        print(health_and_read(), flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
