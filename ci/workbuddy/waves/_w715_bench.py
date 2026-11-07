# W715 实测：等 HTTP 就绪 -> 造测试图 -> 冒烟 -> 长生成(MTP) -> 图片请求(vision) -> 重复段(suffix draft) -> 日志汇总
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

PY = r'''
import json, os, sys, time, urllib.request

BASE = "http://127.0.0.1:8090"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
IMG = "/data/_w715_test.png"

print("=== -1) 等 HTTP 就绪（最多 10 分钟）===")
ready = False
for i in range(120):
    try:
        with urllib.request.urlopen(BASE + "/v1/models", timeout=10) as r:
            r.read()
        ready = True
        print("  就绪 (%.0fs)" % (i * 5))
        break
    except Exception:
        time.sleep(5)
if not ready:
    print("  HTTP 未就绪，放弃")
    sys.exit(1)


def post(path, obj, timeout=900):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), time.time() - t0


def chat(msgs, max_tokens=64):
    o = {"model": MODEL, "messages": msgs, "max_tokens": max_tokens, "temperature": 0}
    body, dt = post("/v1/chat/completions", o)
    try:
        d = json.loads(body)
        m = d["choices"][0]["message"]
        txt = m.get("content")
        if not txt:
            txt = m.get("reasoning_content") or ("[键=%s] " % list(m.keys())) + json.dumps(m, ensure_ascii=False)[:400]
        return txt, dt, d.get("usage", {})
    except Exception as e:
        return "PARSE_FAIL %r %s" % (e, body[:200]), dt, {}


print()
print("=== 0) 造测试图 ===")
try:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (448, 448), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((40, 40, 408, 408), outline=(0, 0, 0), width=5)
    d.ellipse((120, 120, 328, 328), fill=(220, 30, 30))
    d.rectangle((60, 300, 200, 380), fill=(30, 60, 220))
    im.save(IMG)
    print("  已写", IMG, os.path.getsize(IMG), "B")
except Exception as e:
    print("  造图失败:", repr(e))

print()
print("=== 1) 冒烟（64 tok）===")
txt, dt, u = chat([{"role": "user", "content": "用一句话说明什么是 MoE（专家混合）。"}], 64)
print("  %.1fs  usage=%s" % (dt, u))
print("  答:", txt.strip()[:220])

print()
print("=== 2) 长生成（512 tok，触发 MTP）===")
txt, dt, u = chat([{"role": "user", "content": "请用中文写一篇约 400 字的短文，介绍 GPU 显存带宽对推理速度的影响。"}], 512)
print("  %.1fs  usage=%s" % (dt, u))
print("  答:", txt.strip()[:160].replace("\n", " "))

print()
print("=== 3) 图片请求（触发 vision）===")
if os.path.exists(IMG):
    msg = [{"role": "user", "content": [
        {"type": "text", "text": "这张图里有什么形状和颜色？请简要描述。"},
        {"type": "image_url", "image_url": {"url": IMG}}]}]
    txt, dt, u = chat(msg, 128)
    print("  %.1fs  usage=%s" % (dt, u))
    print("  答:", txt.strip()[:260].replace("\n", " "))

print()
print("=== 4) 重复段 prompt（触发 suffix draft / n-gram lookup）===")
para = ("The quick brown fox jumps over the lazy dog. " * 12).strip()
txt, dt, u = chat([{"role": "user", "content": para + "\n\n请原样重复上面这段英文。"}], 128)
print("  %.1fs  usage=%s" % (dt, u))
print("  答:", txt.strip()[:160].replace("\n", " "))

print()
print("=== 5) /v1/models ===")
try:
    with urllib.request.urlopen(BASE + "/v1/models", timeout=60) as r:
        print(" ", r.read().decode()[:280])
except Exception as e:
    print("  失败:", repr(e))
'''

SC = r'''set -u
C=strata166-407
docker exec -i $C sh -c 'cat > /tmp/_w715_bench.py' <<'__PY__'
@PY@
__PY__
docker exec $C python3 /tmp/_w715_bench.py 2>&1 | tail -70
echo
echo "===== 6) 日志汇总 ====="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "--- drafts accepted / suffix drafts ---"
grep -E 'drafts accepted|suffix drafts' "$L" | tail -12
echo "--- prompt / 吞吐 / 命中 ---"
grep -E 'strata serve: prompt|decode expert cache hit rate' "$L" | tail -10
'''.replace("@PY@", PY)

p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=1800)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_bench.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
