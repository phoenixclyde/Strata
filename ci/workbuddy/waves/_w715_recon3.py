# 第三轮侦察：docs/setup.py 里 --ple-gguf 与 --vision/mmproj 的权威用法；查 GGUF 里的 PLE 张量
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

PY = r'''
import sys, glob, json
sys.path.insert(0, "/src/tools")
try:
    import gguf_reader as G
except Exception as e:
    print("import gguf_reader 失败:", e); sys.exit(0)
print("gguf_reader 接口:", [n for n in dir(G) if not n.startswith("_")][:40])
paths = sorted(glob.glob("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/*.gguf"))
paths += sorted(glob.glob("/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/*.gguf"))
for p in paths:
    print("==", p)
    try:
        r = G.GGUFReader(p)
        fn = None
        for cand in ("tensor_names", "names", "tensors"):
            if hasattr(r, cand):
                fn = getattr(r, cand)
                break
        names = fn() if callable(fn) else fn
        names = list(names) if names else []
        ple = [n for n in names if "ple" in str(n).lower() or "per_layer" in str(n).lower()]
        print("   tensors=%d, ple-like=%s" % (len(names), ple[:12]))
    except Exception as e:
        print("   err:", repr(e)[:160])
'''

SC = r'''set -u
C=strata166-406
echo "===== 1) docs: ple-gguf 用法 ====="
docker exec $C sh -c "grep -rn -B3 -A7 'ple-gguf' /src/docs/ | head -80"
echo
echo "===== 2) docs: --vision / mmproj 用法 ====="
docker exec $C sh -c "grep -rn -B3 -A8 'mmproj' /src/docs/ | head -80"
echo
echo "===== 3) setup.py 里 ple / vision 的命令行构造 ====="
docker exec $C sh -c "grep -n -B4 -A12 'ple-gguf\|PLE_GGUF\|ple_gguf' /src/setup.py | head -70"
echo
echo "===== 4) serve 侧 vision / ple 参数 ====="
docker exec $C sh -c "grep -n -iE 'vision|ple[-_]|mmproj' /src/serve/server.py | head -30"
echo
echo "===== 5) strata_inspect.py 用法 ====="
docker exec $C python3 /src/tools/strata_inspect.py --help 2>&1 | head -25
echo
echo "===== 6) GGUF 张量里的 PLE ====="
docker exec -i $C sh -c 'cat > /tmp/_pleprobe.py' <<'__PY__'
@PY@
__PY__
docker exec $C python3 /tmp/_pleprobe.py 2>&1 | head -40
'''
SC = SC.replace("@PY@", PY)
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_recon3.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
