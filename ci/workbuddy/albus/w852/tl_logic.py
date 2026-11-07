import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def ls(p):
    u = "https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/tensilelite/%s?ref=develop" % p
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
for p in ("Logic", "Logic/asm_full", "Logic/gfx906", "Logic/vega20"):
    try:
        d = ls(p)
        names = [x["name"] for x in d][:12]
        print("%-20s -> %d 项: %s" % (p, len(d), " ".join(names)))
    except Exception as e:
        print("%-20s -> ERR %s" % (p, str(e)[:50]))
