import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
B = "https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/"
def ls(p=""):
    with urllib.request.urlopen(urllib.request.Request(B + p + "?ref=develop", headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
def raw(p):
    with urllib.request.urlopen(urllib.request.Request(B + p + "?ref=develop", headers=H), timeout=40) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return base64.b64decode(d["content"]).decode("utf-8", "replace")

print("=== tensilelite/ 顶层 ===")
for it in ls(""):
    print("  %-3s %s" % (it["type"][:3], it["name"]))
print("\n=== Tensile/ 顶层 ===")
try:
    for it in ls("Tensile/"):
        print("  %-3s %s" % (it["type"][:3], it["name"]))
except Exception as e:
    print("  ERR", e)
print("\n=== Common.py 的 SupportedISA ===")
try:
    t = raw("Tensile/Common.py")
    i = t.find("SupportedISA")
    print(t[i:i+700] if i >= 0 else "  (未找到)")
except Exception as e:
    print("  ERR", e)
