import json, urllib.request, sys
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-tune"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

prs = api("/repos/Niko1221/Strata/pulls?state=all&per_page=30&sort=created&direction=desc")
for pr in prs if isinstance(prs, list) else []:
    print("PR #%s [%s] %s" % (pr["number"], pr["state"], pr["title"][:110]))
print("---issues---")
iss = api("/repos/Niko1221/Strata/issues?state=all&per_page=25&sort=created&direction=desc")
for it in iss if isinstance(iss, list) else []:
    if "pull_request" in it:
        continue
    print("#%s [%s] %s" % (it["number"], it["state"], it["title"][:110]))
