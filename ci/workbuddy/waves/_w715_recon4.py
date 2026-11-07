# 第四轮：PLE 表落在哪个分片、vision 段 schema、setup 生成 pack 的命令
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

PY = r'''
import sys, glob
sys.path.insert(0, "/src/tools")
import gguf_reader as G
print("GGUFFile 属性:", [n for n in dir(G.GGUFFile) if not n.startswith("_")])
groups = [
    ("huihui", "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/*.gguf"),
    ("base(unsloth)", "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/*.gguf"),
]
for lab, pat in groups:
    print("=====", lab)
    for p in sorted(glob.glob(pat)):
        if "mmproj" in p:
            continue
        try:
            f = G.GGUFFile(p)
            ts = [t.name for t in f.tensors]
            ple = [n for n in ts if "per_layer_token_embd" in n or "ple" in n.lower()]
            print("  %-58s tensors=%4d  PLE=%s" % (p.split("/")[-1], len(ts), ple[:6]))
        except Exception as e:
            print("  %-58s err=%s" % (p.split("/")[-1], repr(e)[:120]))
'''

SC = r'''set -u
C=strata166-406
echo "===== 1) PLE 表所在分片 ====="
docker exec -i $C sh -c 'cat > /tmp/_ple.py' <<'__PY__'
@PY@
__PY__
docker exec $C python3 /tmp/_ple.py 2>&1 | head -30
echo
echo "===== 2) config 的 vision 段 schema（docs 示例）====="
docker exec $C sh -c "grep -rn -A18 '\"vision\"' /src/docs/*.md | head -70"
echo
echo "===== 3) runconfig.py 里 vision 的处理 ====="
docker exec $C sh -c "grep -n -B3 -A18 'vision' /src/serve/runconfig.py | head -70"
echo
echo "===== 4) setup.py 生成 pack 的命令（iq_pack 调用点）====="
docker exec $C sh -c "grep -n -B6 -A12 'iq_pack' /src/setup.py | head -60"
echo
echo "===== 5) vision 相关 docs 的 config 片段（INSTALL/DETAILS）====="
docker exec $C sh -c "grep -rn -B4 -A14 'mmproj' /src/docs/DETAILS.md | sed -n '60,140p'"
'''
SC = SC.replace("@PY@", PY)
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_recon4.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
