import urllib.request, json, urllib.parse
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

for q in ['repo:Niko1221/Strata "agent turn"',
          'repo:Niko1221/Strata TTFT cached conversation',
          'repo:Niko1221/Strata "conversation cache" restore',
          'repo:Niko1221/Strata gfx906 prompt slow']:
    d = api("/search/issues?q=" + urllib.parse.quote(q) + "&per_page=8&sort=updated")
    print("### %s  total=%s" % (q, d.get("total_count")))
    for it in d.get("items", []):
        print("   #%s [%s] %s" % (it["number"], it["state"], it["title"][:105]))
