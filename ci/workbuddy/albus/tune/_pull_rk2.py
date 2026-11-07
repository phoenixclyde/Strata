import urllib.request, os, time, base64, subprocess

FILES = ["DEAD-ENDS.md", "dequant-instructions.md", "latency-hiding.md",
         "DEVLOG-moe-opt.md", "DEVLOG-qwen38.md", "moe-decode-roadmap.md"]
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_rk"
os.makedirs(OUT, exist_ok=True)
PATHS = [
    "https://raw.githubusercontent.com/KIntegrated/vllm-gfx906-mobydick/gfx906/main/docs/gfx906/%s",
    "https://gh-proxy.com/https://raw.githubusercontent.com/KIntegrated/vllm-gfx906-mobydick/gfx906/main/docs/gfx906/%s",
    "https://ghfast.top/https://raw.githubusercontent.com/KIntegrated/vllm-gfx906-mobydick/gfx906/main/docs/gfx906/%s",
]
HOST = "albus@192.168.50.166"


def fetch_via_166(name):
    """166 的线路有时比本机稳：直接 curl 回 base64。"""
    for tpl in PATHS:
        url = tpl % name
        s = "curl -sL --max-time 60 '%s' | base64 -w0" % url
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                           input=base64.b64encode(s.encode()).decode("ascii").encode("ascii"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        try:
            raw = base64.b64decode(b"".join(p.stdout.split()))
            if len(raw) > 500:
                return raw.decode("utf-8", "replace")
        except Exception:
            pass
    return None


for name in FILES:
    txt = None
    for i in range(2):
        try:
            txt = urllib.request.urlopen(PATHS[0] % name, timeout=40).read().decode("utf-8", "replace")
            if len(txt) > 500:
                break
            txt = None
        except Exception:
            txt = None
        time.sleep(1)
    if not txt:
        txt = fetch_via_166(name)
    if txt:
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(txt)
        print("OK   %-28s %6d bytes" % (name, len(txt)))
    else:
        print("FAIL %s" % name)
