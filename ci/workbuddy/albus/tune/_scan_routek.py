import json, urllib.request, urllib.parse, sys, time

TOK = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
BASE = "KIntegrated/vllm-gfx906-mobydick"


def gh(u, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.Request(u, headers={"Authorization": "token " + TOK, "User-Agent": "albus"})
            return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())
        except Exception as e:
            if i == tries - 1:
                return {"_err": repr(e)}
            time.sleep(2)


FEAT = ["c5", "moe-opt", "int8-packed", "e2-packed", "nh2-int8-gemv", "qsa-fn",
        "fa-integration", "fa-cover-1", "wht1-qsa-topk", "wht1-graph-capture", "dflash2", "triton-1"]

for f in FEAT:
    st = gh("https://api.github.com/repos/%s/branches/gfx906%%2F%s" % (BASE, f))
    if "_err" in st:
        print("%-20s branch lookup ERR %s" % (f, st["_err"])); continue
    sha = st["commit"]["sha"]
    cd = st["commit"]["commit"]["author"]["date"]
    msg = st["commit"]["commit"]["message"].split("\n")[0][:90]
    cmp = gh("https://api.github.com/repos/%s/compare/gfx906/main...%s" % (BASE, sha))
    if "_err" in cmp:
        print("%-20s %s %s | compare ERR %s" % (f, sha[:8], cd[:16], cmp["_err"])); continue
    files = cmp.get("files") or []
    tot = cmp.get("total_commits")
    add = sum(x.get("additions", 0) for x in files)
    dele = sum(x.get("deletions", 0) for x in files)
    print("%-20s %s %s | commits=%s files=%s +%d/-%d" % (f, sha[:8], cd[:16], tot, len(files), add, dele))
    print("    head: " + msg)
    # 只看 kernel 相关文件
    kf = [x for x in files if any(k in x["filename"] for k in
          ("cuda", "rocm", "hip", "triton", ".cu", ".cuh", "quant", "moe", "qsa", "attention"))]
    for x in kf[:8]:
        print("      %-72s +%s/-%s" % (x["filename"], x.get("additions"), x.get("deletions")))
    if len(kf) > 8:
        print("      ... +%d more kernel files" % (len(kf) - 8))
