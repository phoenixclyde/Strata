import urllib.request, json
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-plan"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

# 1) v0.2.5 release 正文
try:
    rel = api("/repos/Niko1221/Strata/releases/tags/v0.2.5")
    print("=== RELEASE v0.2.5 ===")
    print((rel.get("body") or "")[:3000])
except Exception as e:
    print("release FAIL", e)

# 2) issue 4081 的评论
d = api("/repos/Niko1221/Strata/issues/4081/comments")
print("\n=== issue #4081 comments (%d) ===" % len(d))
for c in d:
    print("[%s] %s" % (c["user"]["login"], (c.get("body") or "")[:1200]))
