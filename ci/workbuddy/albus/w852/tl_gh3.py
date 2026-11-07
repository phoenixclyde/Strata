import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60) as r:
        return r.read().decode("utf-8", "replace")
def ls(p):
    return json.loads(get("https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/tensilelite/%s?ref=develop" % p))
def raw(p):
    d = json.loads(get("https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/tensilelite/%s?ref=develop" % p))
    return base64.b64decode(d["content"]).decode("utf-8", "replace")

print("=== Common/ 目录 ===")
for it in ls("Common"):
    print("  ", it["name"])
print("\n=== Components/ 里与 MFMA 相关的文件 ===")
cs = [it["name"] for it in ls("Components") if it["name"].endswith(".py")]
mf = [n for n in cs if "mfma" in n.lower() or "MFMA" in n]
print("  Components 文件数:", len(cs))
print("  名字含 MFMA 的:", mf)
print("\n=== Hardware.py 里的 arch/ISA 判定 ===")
t = raw("Hardware.py")
import re
for kw in ("SupportedISA", "gfx906", "isMfma", "Mfma", "vega"):
    idx = [m.start() for m in re.finditer(kw, t)]
    print("  %-14s 命中 %d" % (kw, len(idx)))
    for i in idx[:2]:
        print("     ...", t[max(0,i-70):i+90].replace("\n", " "))
