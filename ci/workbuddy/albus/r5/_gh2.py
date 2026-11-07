import json, urllib.request, sys
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-tune"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

for n in (4005, 4006):
    d = api("/repos/Niko1221/Strata/pulls/%d" % n)
    print("=" * 20, "PR #%d" % n, d["title"])
    print("state=%s merged=%s base=%s" % (d["state"], d.get("merged"), d["base"]["ref"]))
    print((d.get("body") or "")[:3000])
    print()
for n in (4081,):
    d = api("/repos/Niko1221/Strata/issues/%d" % n)
    print("=" * 20, "ISSUE #%d" % n, d["title"])
    print("state=%s comments=%s" % (d["state"], d["comments"]))
    print((d.get("body") or "")[:3000])
