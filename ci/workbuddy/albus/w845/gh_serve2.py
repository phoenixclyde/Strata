import json, urllib.request
TOK=open("deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r:
        return json.loads(r.read().decode("utf-8","replace"))
c=get("https://api.github.com/repos/Niko1221/Strata/compare/v0.2.8...v0.2.9")
files=c.get("files",[])
print("== serve/ 与 packaging/、"+"apps/host 明细 ==")
for f in files:
    fn=f["filename"]
    if fn.startswith(("serve/","packaging/")) or fn in ("setup.py","CMakeLists.txt"):
        print("  %-44s +%-5s -%-5s %s" % (fn, f["additions"], f["deletions"], f["status"]))
print("\n== src/core + src/kernels + src/prefill（引擎面）==")
for f in files:
    fn=f["filename"]
    if fn.startswith(("src/core/","src/kernels/","src/prefill/","src/program","include/strata")):
        print("  %-44s +%-5s -%-5s %s" % (fn, f["additions"], f["deletions"], f["status"]))
print("\n== serve/server.py 的补丁片段（前 3000 字符）==")
for f in files:
    if f["filename"]=="serve/server.py":
        print(f.get("patch","(no patch field)")[:3000])
