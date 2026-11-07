import json, urllib.request
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
b = get("https://api.github.com/repos/Niko1221/Strata/branches/main")
print("upstream main =", b["commit"]["sha"][:10], "|", b["commit"]["commit"]["message"].splitlines()[0][:70])
print("commit date   =", b["commit"]["commit"]["committer"]["date"])
t = get("https://api.github.com/repos/Niko1221/Strata/tags?per_page=4")
for x in t:
    print("tag", x["name"], x["commit"]["sha"][:10])
# 本地看到的
print("\n本地 upstream/main = c62d5e3a (v0.2.9)")
print("是否已前进 =", b["commit"]["sha"][:10] != "c62d5e3a15")
