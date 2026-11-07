import json, urllib.request
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-tune"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

cs = api("/repos/Niko1221/Strata/commits?path=src/prefill/prefill.cpp&per_page=25")
for c in cs:
    msg = c["commit"]["message"].split("\n")[0]
    print("%s %s" % (c["commit"]["author"]["date"][:16], msg[:110]))
print("--- tags ---")
tags = api("/repos/Niko1221/Strata/tags?per_page=8")
for t in tags:
    print(t["name"], t["commit"]["sha"][:8])
