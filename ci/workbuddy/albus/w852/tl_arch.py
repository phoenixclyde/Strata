import json, urllib.request, base64, re
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def raw(p):
    u = "https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/tensilelite/tensilelite/" + p + "?ref=develop"
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return base64.b64decode(d["content"]).decode("utf-8", "replace")
t = raw("Common/Architectures.py")
print("len =", len(t))
archs = sorted(set(re.findall(r"gfx[0-9]{3,4}", t)))
print("文件里出现的 gfx:", " ".join(archs))
# 打印 arch 表定义附近
i = t.find("gfx")
print("\n--- 前 1800 字符 ---")
print(t[:1800])
