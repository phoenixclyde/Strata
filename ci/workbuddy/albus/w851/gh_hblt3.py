import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def raw(path, repo="ROCm/rocm-libraries", base="projects/hipblaslt/"):
    d = get("https://api.github.com/repos/%s/contents/%s%s?ref=develop" % (repo, base, path))
    return base64.b64decode(d["content"]).decode("utf-8", "replace")
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

t = raw("cmake/tensilelite_supported_architectures.cmake")
print("=== cmake/tensilelite_supported_architectures.cmake ===")
print(t[:2600])
