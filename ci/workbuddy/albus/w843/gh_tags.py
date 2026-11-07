import json,urllib.request
TOK=open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r: return json.load(r)
print("=== 最新 tags ===")
for t in get("https://api.github.com/repos/Niko1221/Strata/tags?per_page=5"):
    print(" ", t["name"], t["commit"]["sha"][:8])
print("=== releases ===")
for r in get("https://api.github.com/repos/Niko1221/Strata/releases?per_page=3"):
    print(" ", r["tag_name"], r["published_at"], r["name"][:50])
print("=== main head ===")
print(" ", get("https://api.github.com/repos/Niko1221/Strata/branches/main")["commit"]["sha"][:8])
