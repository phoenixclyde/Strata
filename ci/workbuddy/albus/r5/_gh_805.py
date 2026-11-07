# -*- coding: utf-8 -*-
"""W805：上游对 gfx906 / MI50 的专家 GEMM 与 prefill 有没有新东西（逐个读标题，不猜）"""
import json, urllib.parse, urllib.request

TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
REPO = "Niko1221/Strata"
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "w805"}


def search(q):
    u = "https://api.github.com/search/issues?q=%s&per_page=20&sort=updated" % urllib.parse.quote(q)
    r = urllib.request.Request(u, headers=H)
    try:
        with urllib.request.urlopen(r, timeout=60) as f:
            return json.loads(f.read())
    except Exception as e:
        return {"error": str(e)}


QS = ['repo:%s gfx906' % REPO,
      'repo:%s MI50' % REPO,
      'repo:%s "prompt" "dp4a"' % REPO,
      'repo:%s "gemm gate" OR "gate/up"' % REPO,
      'repo:%s prefill dequant' % REPO]
seen = set()
for q in QS:
    j = search(q)
    print("=" * 96)
    print("Q:", q, "total", j.get("total_count"), j.get("error") or "")
    for it in (j.get("items") or [])[:10]:
        n = it["number"]
        if n in seen:
            continue
        seen.add(n)
        kind = "PR " if it.get("pull_request") else "iss"
        print("  #%-5d %s %-6s %-8s %s" % (n, kind, it["state"], it["updated_at"][:10], it["title"][:95]))
