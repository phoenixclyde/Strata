import urllib.request, json
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

d = api("/repos/Niko1221/Strata/issues/3321")
print("### #3321", d["title"], "|", d["state"], "| comments", d["comments"])
print((d.get("body") or "")[:2500])
cs = api("/repos/Niko1221/Strata/issues/3321/comments")
for c in cs[-3:]:
    print("\n--%s--" % c["user"]["login"])
    print((c.get("body") or "")[:1500])
