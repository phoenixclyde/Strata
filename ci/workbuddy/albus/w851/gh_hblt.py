import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
def raw(path, ref="develop"):
    d = get("https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/%s?ref=%s" % (path, ref))
    return base64.b64decode(d["content"]).decode("utf-8", "replace")

print("=== hipblaslt/CMakeLists.txt 里的 GPU_TARGETS 默认 ===")
try:
    t = raw("CMakeLists.txt")
    for i, ln in enumerate(t.splitlines(), 1):
        if "GPU_TARGETS" in ln or "gfx" in ln.lower():
            print("  %4d %s" % (i, ln[:130]))
except Exception as e:
    print("  ERR", e)

print("\n=== Tensilelite 支持的架构表（Tensile/Common.py 里的 gfx 列表） ===")
for p in ["tensilelite/Tensile/Common.py", "tensilelite/Tensile/AsmCaps.py"]:
    try:
        t = raw(p)
        import re
        archs = sorted(set(re.findall(r"gfx[0-9]{3,4}", t)))
        print("  %-34s -> %s" % (p, " ".join(archs)))
    except Exception as e:
        print("  %-34s ERR %s" % (p, str(e)[:60]))
