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
files = d.get("files") or []
print("files=%d" % len(files))
for pref in ("src/prefill/", "src/core/", "src/kernels/", "src/program/"):
    hit = [f for f in files if f["filename"].startswith(pref)]
    print("%-14s %d 个文件" % (pref, len(hit)))
    for f in hit:
        print("   %+5d %s" % (f.get("changes"), f["filename"]))
