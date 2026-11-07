# -*- coding: utf-8 -*-
"""加/删一条 ENV 类 register 行，并部署。用法：
  python _set_env.py STRATA_HC_Q8 1 P78 [status]
  python _set_env.py --drop P78
"""
import io, os, sys, json, time, shutil, base64, hashlib, subprocess

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
HOST = "albus@192.168.50.166"
REMOTE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"


def sh(script, timeout=400):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


def edit(pid, name, value, status, note):
    shutil.copy2(REG, REG + ".bak_hcq8_" + time.strftime("%Y%m%d_%H%M%S"))
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    hit = False
    for i, ln in enumerate(lines):
        if ln.startswith(pid + "\t"):
            f = ln.split("\t")
            f[2], f[3], f[5], f[9], f[10] = name, value, status, note, "W776 实测臂"
            lines[i] = "\t".join(f)
            hit = True
    if not hit:
        lines.append("\t".join([pid, "ENV", name, value, "decode", status, "-", "-", "-", note, "W776 实测臂"]))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def drop(pid):
    shutil.copy2(REG, REG + ".bak_hcq8d_" + time.strftime("%Y%m%d_%H%M%S"))
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(l for l in lines if not l.startswith(pid + "\t")) + "\n")


def deploy():
    p = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit(p.stdout.decode("utf-8", "replace")[-600:])
    cfg = json.load(io.open(GEN, encoding="utf-8"))
    md5 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
    b64 = base64.b64encode(open(GEN, "rb").read()).decode("ascii")
    o = sh("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (b64, REMOTE, REMOTE, REMOTE, REMOTE))
    if md5 not in o:
        raise SystemExit("push md5 mismatch")
    sh("docker restart strata166-407 >/dev/null 2>&1")
    for _ in range(45):
        if '"loaded": true' in sh("curl -s --max-time 4 http://127.0.0.1:8090/health"):
            break
        time.sleep(3)
    return cfg.get("env"), sh(
        'curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "'
        'import sys,json;e=json.load(sys.stdin)[\'engine\'];'
        'print(\'slots\',e[\'expert_slots\'],\'vram_free\',e[\'vram_free_mib\'],\'ver\',e[\'version\'])"')


if __name__ == "__main__":
    if sys.argv[1] == "--drop":
        drop(sys.argv[2]); print("dropped", sys.argv[2])
    else:
        name, value, pid = sys.argv[1], sys.argv[2], sys.argv[3]
        status = sys.argv[4] if len(sys.argv) > 4 else "ADOPTED"
        note = sys.argv[5] if len(sys.argv) > 5 else "W776 试验"
        edit(pid, name, value, status, note)
        env, m = deploy()
        print("env:", env)
        print("deployed:", m.strip())
