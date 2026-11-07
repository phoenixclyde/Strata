import json, urllib.request, time

TOK = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
BASE = "KIntegrated/vllm-gfx906-mobydick"
MAIN = "284ce5ff6a"   # gfx906/main

SHAS = {
    "c5": "a0a941719d", "dflash2": "0b2a1e9da9", "e2-packed": "8150b72018",
    "fa-cover-1": "71fe8c3934", "fa-integration": "f4b77c371a", "int8-packed": "20f356dbc3",
    "moe-opt": "1691d1dd29", "nh2-int8-gemv": "2ce603dcd7", "qsa-fn": "113ca61c62",
    "triton-1": "84040ec8", "wht1-graph-capture": "d1a647a7", "wht1-qsa-topk": "bf7c498e",
}


def gh(u, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.Request(u, headers={"Authorization": "token " + TOK, "User-Agent": "albus"})
            return json.loads(urllib.request.urlopen(r, timeout=90).read().decode())
        except Exception as e:
            if i == tries - 1:
                return {"_err": repr(e)}
            time.sleep(2)


for f, sha in SHAS.items():
    c = gh("https://api.github.com/repos/%s/commits/%s" % (BASE, sha))
    date = c["commit"]["author"]["date"][:16] if "_err" not in c else "?"
    msg = c["commit"]["message"].split("\n")[0][:100] if "_err" not in c else c["_err"]
    cmp = gh("https://api.github.com/repos/%s/compare/%s...%s" % (BASE, MAIN, sha))
    if "_err" in cmp:
        print("%-20s %s | compare ERR %s" % (f, date, cmp["_err"]))
        continue
    files = cmp.get("files") or []
    add = sum(x.get("additions", 0) for x in files)
    dele = sum(x.get("deletions", 0) for x in files)
    print("== %-20s %s  commits=%s files=%s +%d/-%d" % (f, date, cmp.get("total_commits"), len(files), add, dele))
    print("   " + msg)
    kf = [x for x in files if any(k in x["filename"] for k in
          ("cuda", "rocm", "hip", "triton", ".cu", ".cuh", "quant", "moe", "qsa", "attention", "kernel"))]
    for x in kf[:6]:
        print("     %-74s +%s/-%s" % (x["filename"], x.get("additions"), x.get("deletions")))
    if len(kf) > 6:
        print("     ... +%d more" % (len(kf) - 6))
