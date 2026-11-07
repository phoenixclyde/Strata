# W715：落盘新 config -> 推 166（config + register）-> 单测 strata-vision 能否 READY
import base64, hashlib, io, json, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-huihui-ud-iq4_xs.json")
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SH1 = ("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/"
       "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf")
MM = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/mmproj-Qwen3.8-Flash-Next-BF16.gguf"


def run(sc, t=600):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(sc.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("===== 1) 本机落盘 config =====")
r = subprocess.run([r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe", "-u",
                    os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "")
print("rc=%d" % r.returncode)
cfg_md5 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
reg_md5 = hashlib.md5(open(REG, "rb").read()).hexdigest()
print("本机 config md5 = %s  (%d B)" % (cfg_md5, os.path.getsize(GEN)))
print("本机 register md5 = %s" % reg_md5)

print()
print("===== 2) 推 166：config 与 register =====")
scfg = base64.b64encode(open(GEN, "rb").read()).decode("ascii")
sreg = base64.b64encode(open(REG, "rb").read()).decode("ascii")
sc = ("set -u\nD=/home/albus/strata166\n"
      "cp -f $D/params/PARAM_REGISTER.tsv $D/params/PARAM_REGISTER.tsv.bak_w715_$(date +%Y%m%d_%H%M%S)\n"
      "base64 -d > $D/params/PARAM_REGISTER.tsv <<'__R__'\n@R@\n__R__\n"
      "base64 -d > $D/data/strata-huihui-ud-iq4_xs.json <<'__C__'\n@C@\n__C__\n"
      "mkdir -p $D/data/profiles\n"
      "echo reg_md5=$(md5sum $D/params/PARAM_REGISTER.tsv | cut -d' ' -f1)\n"
      "echo cfg_md5=$(md5sum $D/data/strata-huihui-ud-iq4_xs.json | cut -d' ' -f1)\n"
      "echo '--- 166 上现有 config 文件 ---'\n"
      "ls -l $D/data/*.json\n").replace("@R@", sreg).replace("@C@", scfg)
rc, out, err = run(sc, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])
print("两侧一致: register %s | config %s"
      % (reg_md5 in out, cfg_md5 in out))

print()
print("===== 3) 单测 strata-vision（在现役容器里跑，看能否 READY）=====")
sc2 = ("set -u\nC=strata166-406\n"
       "docker exec $C sh -c 'timeout 40 /data/vision/strata-vision --mmproj %s --model %s; echo \"exit=$?\"' 2>&1 | head -20\n"
       % (MM, SH1))
rc, out, err = run(sc2, 120)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])
