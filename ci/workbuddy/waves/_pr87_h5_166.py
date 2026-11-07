import os, io, json, base64, urllib.request, urllib.error, sys

print("=== [1] H5 锚点：0.1.40.2 的 CMakeLists.txt ===")
REPO, REF = "Niko1221/Strata", "v0.1.40.2"
OUT = r"D:/strata166/upstream/v0.1.40.2"
os.makedirs(OUT, exist_ok=True)
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def fetch(path, ref):
    url = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, path, ref)
    rq = urllib.request.Request(url, headers={"User-Agent": "routek-client",
                                             "Accept": "application/vnd.github+json"})
    with op.open(rq, timeout=60) as resp:
        d = json.loads(resp.read().decode())
    return base64.b64decode(d["content"])

raw = fetch("CMakeLists.txt", REF)
open(os.path.join(OUT, "CMakeLists.txt"), "wb").write(raw)
t = raw.decode("utf-8", "replace")
print("  0.1.40.2 CMakeLists.txt = %d B" % len(raw))

def chk(txt, tag):
    for pat in ["STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906",
                "STRATA_Q6K_EXPERTS"]:
        print("    %-38s count=%d" % (tag + ":" + pat[:30], txt.count(pat)))
    L = txt.split("\n")
    for i, l in enumerate(L):
        if "STRATA_Q6K_EXPERTS" in l:
            for j in range(max(0, i - 2), min(len(L), i + 3)):
                print("      %6d| %s" % (j + 1, L[j][:126]))
            print("      ----")

chk(t, "new")

old_p = r"D:/strata166/tmp/dryrun_0_1_40_1/CMakeLists.txt"
if os.path.isfile(old_p):
    to = io.open(old_p, encoding="utf-8", errors="replace").read()
    print("  --- 0.1.40.1 对照 (%d B) ---" % os.path.getsize(old_p))
    chk(to, "old")

print()
print("=== [2] 166 现状 ===")
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

script = r'''
echo "--- 镜像 ---"
docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}' 2>&1 | grep -iE 'strata|rocm-gfx906' | head -10
echo "--- 容器 ---"
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1 | grep -iE 'strata' | head -10
echo "--- 运行中（全部）---"
docker ps --format '{{.Names}} | {{.Status}}' 2>&1 | head -12
echo "--- 磁盘 ---"
df -h / /home 2>&1 | head -5
echo "--- /data 挂载 ---"
ls -la /home/albus/routeK/strata 2>&1 | head -12
echo "--- 现有 systemd unit ---"
ls -la /etc/systemd/system/ 2>&1 | grep -viE '\.wants|\.requires|snap|^total|^d' | head -20
echo "--- 启动脚本痕迹 ---"
ls -la /home/albus/routeK/run/ 2>/dev/null | grep -iE 'strata|serve' | head -12
echo "--- 端口 8090 ---"
(curl -s -m 4 http://127.0.0.1:8090/v1/models 2>&1 | head -c 300) || echo "8090 no answer"
echo
echo "--- VRAM / 时间 ---"
rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -2
date -Is
'''
rc, out, err = _sshutil.run_remote(script, timeout=200, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
