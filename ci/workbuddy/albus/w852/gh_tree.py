import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
# 列出 mixa3607/ML-gfx906 全部文件路径（git trees, recursive）
t = get("https://api.github.com/repos/mixa3607/ML-gfx906/git/trees/HEAD?recursive=1")
paths = [x["path"] for x in t.get("tree", []) if x["type"] == "blob"]
print("文件总数:", len(paths))
hits = [p for p in paths if any(k in p.lower() for k in ("hipblaslt", "blas", "gemm", "rocm"))]
for p in hits[:25]:
    print("  ", p)
