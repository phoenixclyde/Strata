# 步骤1：/models 完整性抽验 -> register P01 改指 /models -> gen_config -> 推 166 -> 建容器 -406（挂 /models，去掉 weights）
import base64, collections, hashlib, io, os, shutil, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
D = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
S = "/home/albus/strata166/weights"


def run(script, t=600):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== 1) /models 链接数 + 抽样哈希（对 /weights）===")
sh = ["Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
      "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf",
      "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf"]
TMPL = '''echo "== @F@"
stat -c 'link=%h size=%s path=%n' "@D@/@F@" "@S@/@F@"
for off in 0 50 99; do
  a=$(dd if="@S@/@F@" bs=1M skip=$off count=16 2>/dev/null | md5sum | cut -d' ' -f1)
  b=$(dd if="@D@/@F@" bs=1M skip=$off count=16 2>/dev/null | md5sum | cut -d' ' -f1)
  echo "   off=${off}MB weights=$a models=$b $([ "$a" = "$b" ] && echo SAME || echo DIFF)"
done'''
script = "set -u\n" + "\n".join(
    TMPL.replace("@D@", D).replace("@S@", S).replace("@F@", f) for f in sh)
rc, out, err = run(script, 900)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== 2) register P01 改指 /models ===")
raw = open(REG, "rb").read()
print("register md5(before) =", hashlib.md5(raw).hexdigest())
shutil.copy2(REG, REG + ".bak_w714_" + time.strftime("%Y%m%d_%H%M%S"))
t = raw.decode("utf-8")
old = "/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
new = D + "/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
assert t.count(old) == 1, "P01 锚点命中 %d 次" % t.count(old)
io.open(REG, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
raw2 = open(REG, "rb").read()
print("register md5(after)  =", hashlib.md5(raw2).hexdigest())
b4 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
r = subprocess.run([r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe", "-u",
                    os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
af = hashlib.md5(open(GEN, "rb").read()).hexdigest()
print("gen_config rc=%d generated %s -> %s" % (r.returncode, b4[:12], af[:12]))
print("新 config args:", " ".join(__import__("json").loads(open(GEN, encoding="utf-8").read())["args"])[:220])

print("=== 3) 推 config + register 到 166 ===")
sim = base64.b64encode(raw2).decode("ascii")
sgen = base64.b64encode(open(GEN, "rb").read()).decode("ascii")
sc = ("set -u\nD=/home/albus/strata166\n"
      "cp -f $D/params/PARAM_REGISTER.tsv $D/params/PARAM_REGISTER.tsv.bak_w714_$(date +%%Y%%m%%d_%%H%%M%%S)\n"
      "base64 -d > $D/params/PARAM_REGISTER.tsv <<'__R__'\n%s\n__R__\n"
      "base64 -d > $D/params/generated/strata-ud-iq4_xs.json <<'__G__'\n%s\n__G__\n"
      "cp -f $D/params/generated/strata-ud-iq4_xs.json $D/data/strata-ud-iq4_xs.json\n"
      "echo reg_md5=$(md5sum $D/params/PARAM_REGISTER.tsv | cut -d' ' -f1)\n"
      "echo live_md5=$(md5sum $D/data/strata-ud-iq4_xs.json | cut -d' ' -f1)\n") % (sim, sgen)
rc, out, err = run(sc, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== 4) 建容器 -406（挂 /models，去掉 weights）===")
sc2 = """set -u
if docker inspect strata166-406 >/dev/null 2>&1; then
  docker inspect -f 'exists: status={{.State.Status}} image={{.Config.Image}}' strata166-406
else
  docker create --name strata166-406 --restart unless-stopped \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --ulimit memlock=-1 \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -p 8090:8090 \
    -v /home/albus/strata166/data:/data \
    -v /models:/models:ro \
    strata-gfx906:0.1.41 \
    bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-ud-iq4_xs.json --port 8090'
  docker inspect strata166-406 --format 'created: status={{.State.Status}} Binds={{json .HostConfig.Binds}} Ports={{json .HostConfig.PortBindings}}'
fi
"""
rc, out, err = run(sc2, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])
