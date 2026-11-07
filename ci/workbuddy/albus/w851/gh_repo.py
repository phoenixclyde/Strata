import json, urllib.request
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def get(u, raw=False):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        b = r.read().decode("utf-8", "replace")
        return b if raw else json.loads(b)
d = get("https://api.github.com/search/repositories?q=gfx906+rocm&sort=stars&per_page=8")
print("=== repos: gfx906 rocm ===")
for it in d.get("items", [])[:8]:
    print("  %-40s stars=%-4s %s" % (it["full_name"], it["stargazers_count"], (it["description"] or "")[:60]))
print("\n=== README of top repo ===")
try:
    top = d["items"][0]["full_name"]
    r = get("https://api.github.com/repos/%s/readme" % top)
    import base64
    txt = base64.b64decode(r["content"]).decode("utf-8", "replace")
    print("repo:", top, " len:", len(txt))
    for line in txt.splitlines()[:60]:
        if line.strip():
            print("  ", line[:140])
except Exception as e:
    print("  ERR", e)
