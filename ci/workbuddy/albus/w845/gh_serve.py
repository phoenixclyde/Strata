import json, urllib.request
TOK=open("deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r:
        return json.loads(r.read().decode("utf-8","replace"))
c=get("https://api.github.com/repos/Niko1221/Strata/compare/v0.2.8...v0.2.9")
print("compare v0.2.8...v0.2.9  commits=%d  files=%d  ahead_by=%s" % (c.get("total_commits",-1), len(c.get("files",[])), c.get("ahead_by")))
files=c.get("files",[])
print("\n== 全部改动文件（按目录分组）==")
import collections
g=collections.Counter()
for f in files:
    fn=f["filename"]; top="/".join(fn.split("/")[:2]) if "/" in fn else fn
    g[top]+=1
for k,v in sorted(g.items(), key=lambda x:-x[1]):
    print("  %-40s %d" % (k,v))
print("\n== serve/ 目录明细 ==")
for f in files:
    if f["filename"].startswith("serve/"):
        print("  %-46s +%s -%s  %s" % (f["filename"], f["additions"], f["deletions"], f["status"]))
print("\n== 其他可疑目录（src/program, src/core, CMakeLists, scripts, docker） ==")
for f in files:
    fn=f["filename"]
    if fn.startswith(("src/program/","src/core/","scripts/","docker/","Dockerfile")) or fn in ("CMakeLists.txt",):
        print("  %-52s +%s -%s" % (fn[:52], f["additions"], f["deletions"]))
print("\n== 非 serve 的 .py（tools 等） ==")
for f in files:
    if f["filename"].endswith(".py") and not f["filename"].startswith("serve/"):
        print("  %-52s +%s -%s" % (f["filename"][:52], f["additions"], f["deletions"]))
