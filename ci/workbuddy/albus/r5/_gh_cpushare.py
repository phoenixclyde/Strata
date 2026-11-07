# -*- coding: utf-8 -*-
"""W803: 上游关于 CPU prefill share 的质量/正确性口径（不猜，读正文）"""
import json, os, sys, urllib.parse, urllib.request

TOK = open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
REPO = "Niko1221/Strata"
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "w803-audit"}


def get(url):
    r = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read())


def search(q, kind="issues"):
    u = "https://api.github.com/search/%s?q=%s&per_page=30" % (kind, urllib.parse.quote(q))
    try:
        return get(u)
    except Exception as e:
        return {"error": str(e)}


for q in ['repo:%s "cpu share"' % REPO,
          'repo:%s "PREFILL_CPU_SHARE"' % REPO,
          'repo:%s "CPU prefill"' % REPO,
          'repo:%s cpu_share' % REPO]:
    j = search(q)
    print("=" * 100)
    print("Q:", q, "total", j.get("total_count"), j.get("error") or "")
    for it in (j.get("items") or [])[:8]:
        print("  #%s [%s] %s" % (it["number"], it["state"], it["title"][:110]))
        if it.get("pull_request"):
            print("       PR merged_at=%s" % (it["pull_request"].get("merged_at")))
        else:
            print("       comments=%s created=%s" % (it.get("comments"), it["created_at"][:10]))
