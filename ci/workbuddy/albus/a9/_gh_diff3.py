import urllib.request, json
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

d = api("/repos/Niko1221/Strata/compare/v0.2.4.2...v0.2.5")
for f in d["files"]:
    if f["filename"] == "src/program/generate.cpp":
        print(f.get("patch", "(no patch)")[:6000])
