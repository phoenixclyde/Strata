import json,re,urllib.request
TOK=open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r: return json.load(r)
rel=[r for r in get("https://api.github.com/repos/Niko1221/Strata/releases?per_page=5") if r["tag_name"]=="v0.2.9"][0]
print("### v0.2.9", rel["published_at"])
b=re.sub(r"\r","",rel["body"] or "")
print(b[:2200])
print("\n### compare v0.2.8...v0.2.9")
c=get("https://api.github.com/repos/Niko1221/Strata/compare/v0.2.8...v0.2.9")
print("commits=%d files=%d" % (c.get("total_commits",-1), len(c.get("files",[]))))
for f in c.get("files",[])[:25]:
    print("  %-52s +%s -%s" % (f["filename"][:52], f["additions"], f["deletions"]))
