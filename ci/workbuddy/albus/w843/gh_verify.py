import json, re, urllib.request
TOK=open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H={"Authorization":"Bearer "+TOK,"Accept":"application/vnd.github+json","User-Agent":"albus-audit"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r: return json.load(r)
for n in (3987,):
    d=get("https://api.github.com/repos/Niko1221/Strata/issues/%d"%n)
    b=re.sub(r"\r","",d["body"] or "")
    print("### #%d %s"%(n,d["title"]))
    print(b[:2600])
    print("\n--- files changed ---")
    try:
        fs=get("https://api.github.com/repos/Niko1221/Strata/pulls/%d/files"%n)
        for f in fs[:8]: print("  %s  +%s -%s"%(f["filename"],f["additions"],f["deletions"]))
    except Exception as e: print("  ERR",e)
