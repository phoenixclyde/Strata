import json,re,urllib.request
TOK=open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus"}
def get(u):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r:
                return json.loads(r.read().decode("utf-8","replace"))
        except Exception as e:
            err=e
    raise err
rel=get("https://api.github.com/repos/Niko1221/Strata/releases/tags/v0.2.9")
print("### v0.2.9", rel["published_at"])
print(re.sub(r"\r","",rel["body"] or "")[:1800])
print("\n### commits v0.2.8..v0.2.9 (first 30)")
cs=get("https://api.github.com/repos/Niko1221/Strata/commits?sha=v0.2.9&per_page=40")
print("count=%d" % len(cs))
for c in cs[:30]:
    msg=c["commit"]["message"].splitlines()[0][:88]
    print("  %s %s" % (c["sha"][:8], msg))
