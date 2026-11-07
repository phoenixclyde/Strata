import urllib.request, json, re
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

d = api("/repos/Niko1221/Strata/compare/v0.2.4.2...v0.2.5")
print("commits=%d files=%d" % (d.get("total_commits", 0), len(d.get("files") or [])))
pat = re.compile(r"prefill|chunk|expert|cache|serve|hip|amd|gfx9|prompt", re.I)
for c in d.get("commits", []):
    m = c["commit"]["message"].split("\n")[0]
    if pat.search(m):
        print(" ", m[:130])
print("--- 主要改动文件（前 25，按改动量）---")
fs = sorted(d.get("files") or [], key=lambda f: -(f.get("changes") or 0))[:25]
for f in fs:
    print("  %+5d %s" % (f.get("changes"), f["filename"]))
