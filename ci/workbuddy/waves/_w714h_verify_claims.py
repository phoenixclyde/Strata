# B) 我们的 mmproj sha256 vs huihui 仓三个 mmproj 的 lfs oid 对撞
# C) 我们的 MTP 出处（mtp_fetch 的 URL/仓）+ /data/mtp 现状
import base64, hashlib, io, json, os, re, subprocess, urllib.request

WS = r"D:/workbuddy_space/strata_ws"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "Mozilla/5.0"), ("Accept", "application/json")]

print("=== B1) huihui 仓三个 mmproj 的完整 sha256（hf-mirror）===")
try:
    items = json.loads(op.open("https://hf-mirror.com/api/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/tree/main?recursive=true", timeout=40).read().decode())
    hui = {}
    for it in items:
        if it.get("type") == "file" and "mmproj" in it["path"].lower():
            oid = ((it.get("lfs") or {}).get("oid") or "")
            hui[it["path"]] = (it.get("size"), oid)
            print("   %-46s %12s  %s" % (it["path"], it.get("size"), oid))
except Exception as e:
    print("   失败:", repr(e))
    hui = {}

print("=== B2) 我们手上那个 mmproj 的 sha256 ===")
cands = [os.path.join(r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS", "mmproj-Qwen3.8-Flash-Next-BF16.gguf"),
         os.path.join(r"D:/IDM", "mmproj-Ornith-1.5-35B-A3B-f16.gguf")]
for p in cands:
    if os.path.exists(p):
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        sz = os.path.getsize(p)
        hit = [k for k, (s, o) in hui.items() if o == h]
        print("   %-52s %12d  sha256=%s  %s" % (os.path.basename(p), sz, h, ("<= 等于 huihui 的 " + hit[0]) if hit else "(与 huihui 三个 mmproj 都不同)"))
    else:
        print("   (缺)", p)

print()
print("=== C) 我们的 MTP 出处（搜 mtp_fetch / MTP 下载记录）===")
hits = []
for root, dirs, files in os.walk(WS):
    if any(x in root for x in ["transfer", "tmp", "upstream", "snapshots_premigrate", "logs"]):
        continue
    for f in files:
        if not f.endswith((".py", ".txt", ".sh", ".md", ".json")):
            continue
        fp = os.path.join(root, f)
        try:
            t = io.open(fp, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if re.search(r"mtp_fetch|mtp-manifest|MTP_REVISION|/mtp/", t):
            for ln in t.splitlines():
                if re.search(r"mtp_fetch|mtp-manifest|MTP_REVISION|HF_ENDPOINT|repo|resolve", ln, re.I):
                    hits.append((os.path.relpath(fp, WS), ln.strip()[:160]))
for h, l in hits[:30]:
    print("   %-46s %s" % (h, l))
print("   (命中 %d 行)" % len(hits))

print()
print("=== C2) 166 上 /data/mtp 现状与 rt 里的清单 ===")
sc = """set -u
ls -l /home/albus/strata166/data/mtp/ | head -12
echo '--- rt 目录 ---'; ls -l /home/albus/strata166/data/mtp/rt | head -8
echo '--- manifest 头部（能看出源）---'
head -c 400 /home/albus/strata166/data/mtp/mtp-manifest.json 2>/dev/null; echo
head -c 300 /home/albus/strata166/data/mtp/mtp-inventory.json 2>/dev/null; echo
"""
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(sc.encode()) + b"\n", capture_output=True, timeout=120)
print(p.stdout.decode("utf-8", "replace"))
