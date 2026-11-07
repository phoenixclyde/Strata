import json, urllib.request, base64
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
d = get("https://api.github.com/search/repositories?q=gfx906+in:name,description&sort=stars&per_page=15")
print("=== gfx906 repos ===")
for it in d.get("items", [])[:15]:
    print("  %-46s ★%-4s %s" % (it["full_name"], it["stargazers_count"], (it["description"] or "")[:56]))
# 找 mixa3607 的仓库
print("\n=== mixa3607 的仓库 ===")
try:
    u = get("https://api.github.com/users/mixa3607/repos?per_page=20&sort=updated")
    for it in u[:12]:
        print("  %-46s ★%-4s" % (it["full_name"], it["stargazers_count"]))
except Exception as e:
    print("  ERR", e)
