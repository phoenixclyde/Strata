# -*- coding: utf-8 -*-
"""W803: 读上游 CPU share 的四条正文（质量口径 + 校准旋钮）"""
import json, sys, urllib.request

TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
REPO = "Niko1221/Strata"
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "w803-audit"}


def get(url):
    r = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read())


def body(n, cut=4200):
    try:
        it = get("https://api.github.com/repos/%s/issues/%d" % (REPO, n))
    except Exception as e:
        print("#%d ERROR %s" % (n, e)); return
    print("=" * 100)
    print("#%d [%s] %s  (%s)" % (n, it["state"], it["title"], it["created_at"][:10]))
    print(it.get("body") or "(no body)")
    try:
        cs = get("https://api.github.com/repos/%s/issues/%d/comments?per_page=30" % (REPO, n))
        for c in cs:
            print("-" * 60)
            print("@%s %s:" % (c["user"]["login"], c["created_at"][:10]))
            print((c.get("body") or "")[:cut])
    except Exception as e:
        print("comments ERROR", e)


for n in sys.argv[1:]:
    body(int(n))
