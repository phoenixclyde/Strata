import json, urllib.request, urllib.parse
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-tune"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

for q in ['repo:Niko1221/Strata "PREFILL_STREAM_MIN"',
          'repo:Niko1221/Strata "small chunk" prefill',
          'repo:Niko1221/Strata "short prompt" prefill tokens',
          'repo:Niko1221/Strata "wait copy"']:
    d = api("/search/issues?q=" + urllib.parse.quote(q) + "&per_page=10&sort=updated")
    print("### " + q + "  total=%s" % d.get("total_count"))
    for it in d.get("items", []):
        print("   #%s [%s] %s" % (it["number"], it["state"], it["title"][:100]))
