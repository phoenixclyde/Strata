import json, urllib.request, urllib.parse
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def q(query, per=10):
    u = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query) + "&per_page=%d&sort=updated" % per
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"error": str(e)}
for query in [
    'repo:ROCm/hipBLASLt gfx906',
    'repo:ROCm/rocm-libraries hipblaslt gfx906',
    '"gfx906" hipblaslt in:title,body',
    'TensileLite gfx906',
    'MI50 hipblaslt tensilite in:title,body',
]:
    d = q(query)
    print("\n### " + query)
    if "error" in d:
        print("  ERR", d["error"]); continue
    print("  total=%s" % d.get("total_count"))
    for it in d.get("items", [])[:8]:
        repo = it["repository_url"].split("/repos/")[-1]
        print("  %-28s #%-6s %-52s %s" % (repo, it["number"], it["title"][:52], it["state"]))
