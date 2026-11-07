import json, urllib.request, base64, re
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
def ls(path):
    return get("https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/%s?ref=develop" % path)
def raw(path):
    d = get("https://api.github.com/repos/ROCm/rocm-libraries/contents/projects/hipblaslt/%s?ref=develop" % path)
    return base64.b64decode(d["content"]).decode("utf-8", "replace")

# 找定义 tensilelite_get_base_architectures 的 cmake 文件
for p in ["tensilelite/Tensile/cmake", "tensilelite/cmake", "cmake"]:
    try:
        items = ls(p)
        for it in items:
            if it["name"].endswith(".cmake"):
                print("  file:", p + "/" + it["name"])
    except Exception as e:
        print("  ls %-28s ERR %s" % (p, str(e)[:50]))

print("\n=== 搜 get_base_architectures 定义 ===")
for p in ["tensilelite/Tensile/cmake/TensileConfig.cmake", "tensilelite/cmake/TensileConfig.cmake"]:
    try:
        t = raw(p)
        i = t.find("function(tensilelite_get_base_architectures")
        if i < 0: i = t.find("get_base_architectures")
        if i >= 0:
            print("  in", p)
            print(t[i:i+900])
            break
    except Exception as e:
        print("  %-50s ERR" % p)
