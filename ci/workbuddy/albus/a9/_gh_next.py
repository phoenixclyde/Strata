import urllib.request, json, re
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

d = api("/repos/Niko1221/Strata/compare/v0.2.5...main")
print("commits=%d files=%d (v0.2.5 -> main)" % (d.get("total_commits", 0), len(d.get("files") or [])))
pat = re.compile(r"prefill|chunk|expert|copy|stream|cache|serve|hip|amd", re.I)
n = 0
for c in d.get("commits", []):
    m = c["commit"]["message"].split("\n")[0]
    if pat.search(m):
        print(" ", m[:120]); n += 1
print("matched", n)
print("--- 关键文件 ---")
for f in d.get("files") or []:
    if f["filename"].startswith(("src/prefill/", "src/core/conversation", "src/program/generate")):
        print("  %+5d %s" % (f.get("changes"), f["filename"]))
