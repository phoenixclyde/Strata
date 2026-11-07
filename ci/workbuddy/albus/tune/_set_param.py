# -*- coding: utf-8 -*-
"""通用：登记/修改一条 CLI 参数 -> 生成 config -> 推 166 -> 重启 -> 等 ready -> 回读关键读数。
用法：
  python _set_param.py <id> <name> <value> [status] [note]
  python _set_param.py --drop <id>        # 删除该行（回到不设）
value 为 (flag) 时作为无值开关。
"""
import io, os, sys, json, time, shutil, base64, hashlib, subprocess

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
HOST = "albus@192.168.50.166"
REMOTE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"


def sh(script, timeout=240):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


def edit_register(pid, name, value, status, note):
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    found = False
    for i, ln in enumerate(lines):
        if ln.startswith(pid + "\t"):
            f = ln.split("\t")
            f[2], f[3], f[5], f[9] = name, value, status, note
            lines[i] = "\t".join(f)
            found = True
            break
    if not found:
        lines.append("\t".join([pid, "CLI", name, value, "prefill", status, "-", "-", "-", note, "W776 扫描中"]))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def drop_register(pid):
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    out = [l for l in lines if not l.startswith(pid + "\t")]
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


def gen_write():
    p = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise SystemExit("gen_config failed: " + p.stdout.decode("utf-8", "replace")[-800:])
    return json.load(io.open(GEN, encoding="utf-8"))


def deploy():
    md5 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
    b64 = base64.b64encode(open(GEN, "rb").read()).decode("ascii")
    o = sh("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (b64, REMOTE, REMOTE, REMOTE, REMOTE))
    if md5 not in o:
        raise SystemExit("push md5 mismatch: " + o)
    o = sh("docker restart strata166-407 >/dev/null 2>&1 && echo OK")
    for _ in range(45):
        h = sh("curl -s --max-time 4 http://127.0.0.1:8090/health")
        if '"loaded": true' in h:
            break
        time.sleep(3)
    m = sh(r'''curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;d=json.load(sys.stdin);e=d['engine']
print('slots=%s vram_free=%s workers=%s' % (e['expert_slots'],e['vram_free_mib'],e['pool_workers']))
"''')
    return m.strip()


if __name__ == "__main__":
    if sys.argv[1] == "--drop":
        drop_register(sys.argv[2])
        gen_write()
        print("dropped", sys.argv[2], "->", deploy())
    else:
        pid, name, value = sys.argv[1], sys.argv[2], sys.argv[3]
        status = sys.argv[4] if len(sys.argv) > 4 else "ADOPTED"
        note = sys.argv[5] if len(sys.argv) > 5 else "W776 扫描臂"
        edit_register(pid, name, value, status, note)
        cfg = gen_write()
        args = cfg.get("args", [])
        present = name in args
        print("register ->", pid, name, value, "| in config:", present)
        if not present:
            raise SystemExit("参数没进 config，中止（不重启）")
        print("deployed:", deploy())
