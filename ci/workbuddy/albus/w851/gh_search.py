import json, urllib.request, urllib.parse, time
TOK = open("deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus"}
def q(query, per=8):
    u = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query) + "&per_page=%d&sort=updated" % per
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"error": str(e)}
for query in [
    'gfx906 hipblaslt repo:ROCm/rocm-libraries',
    'gfx906 hipblaslt repo:ROCm/hipBLASLt',
    'MI50 hipblaslt in:title,body',
    'gfx906 "not supported" rocm in:title',
]:
    d = q(query)
    print("\n### " + query)
    if "error" in d:
        print("  ERR", d["error"]); continue
    print("  total=%s" % d.get("total_count"))
    for it in d.get("items", [])[:6]:
        print("  #%-6s %-58s %s" % (it["number"], it["title"][:58], it["state"]))
