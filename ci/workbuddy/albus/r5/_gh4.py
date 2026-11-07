import json, urllib.request
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-tune"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

for n in (3821, 4002):
    d = api("/repos/Niko1221/Strata/pulls/%d" % n)
    print("=" * 20, "PR #%d" % n, d["title"])
    print("state=%s merged=%s base=%s" % (d["state"], d.get("merged"), d["base"]["ref"]) if "base" in d else d["state"])
    print((d.get("body") or "")[:2600])
