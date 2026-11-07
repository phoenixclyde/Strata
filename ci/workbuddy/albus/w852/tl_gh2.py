import json, urllib.request
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
base = "https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/"
print("=== tensilelite/tensilelite/ ===")
d = json.loads(get(base + "tensilelite/?ref=develop"))
for it in d[:24]:
    print("  %-3s %s" % (it["type"][:3], it["name"]))
print("\n=== 直接取 Common.py 的 SupportedISA ===")
for p in ("tensilelite/Common.py", "tensilelite/Tensile/Common.py", "Common.py"):
    try:
        t = get("https://raw.githubusercontent.com/ROCm/rocm-libraries/develop/projects/hipblaslt/tensilelite/" + p)
        if "SupportedISA" in t:
            i = t.find("SupportedISA")
            print("  found in", p)
            print(t[i:i+600])
            break
    except Exception as e:
        print("  %-28s ERR %s" % (p, str(e)[:40]))
