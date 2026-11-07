import urllib.request, os, sys

FILES = [
    ("DEAD-ENDS.md", 8000),
    ("lds-layout.md", 4000),
    ("dequant-instructions.md", 4000),
    ("latency-hiding.md", 5000),
]
BASE = "https://raw.githubusercontent.com/KIntegrated/vllm-gfx906-mobydick/gfx906/main/docs/gfx906/"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_rk"
os.makedirs(OUT, exist_ok=True)
for name, lim in FILES:
    try:
        d = urllib.request.urlopen(BASE + name, timeout=90).read().decode("utf-8", "replace")
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(d)
        print("=" * 72)
        print("## " + name, len(d), "bytes")
        print(d[:lim])
    except Exception as e:
        print("## " + name, "ERR", e)
