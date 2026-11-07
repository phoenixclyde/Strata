#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_check_vllm.py -- 确认两个 vLLM 仓库有没有被我碰过。

判定口径：列出最近 10 条提交，看有没有 author.date > 2026-10-30 且作者不是原有维护者的。
"""
import json
import os
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
tok = open(os.path.join(HERE, "..", "..", "deploy", "tmp", "_tok.txt"), encoding="utf-8").read().strip()


def get(url):
    r = urllib.request.Request(url)
    r.add_header("Authorization", "Bearer " + tok)
    r.add_header("User-Agent", "w861")
    r.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


for repo in ("phoenixclyde/vllm-gfx906-mobydick", "phoenixclyde/vllm-gfx906-routeb"):
    print("=== %s ===" % repo)
    st, js = get("https://api.github.com/repos/%s" % repo)
    if st == 200:
        print("   pushed_at:", js.get("pushed_at"), "| default:", js.get("default_branch"))

    st, js = get("https://api.github.com/repos/%s/commits?per_page=10" % repo)
    if st != 200:
        print("   commits HTTP", st, js.get("message"))
        continue
    latest = None
    mine = 0
    for c in js:
        a = c["commit"]["author"]
        d = a["date"]
        latest = latest or d
        flag = ""
        if d > "2026-10-30":
            flag = "  <<< 10-30 之后"
            if "w861" in c["commit"]["message"].lower() or "hipblaslt" in c["commit"]["message"].lower():
                mine += 1
        print("   %s  %-14s %s  %s%s" % (c["sha"][:10], a["name"], d,
                                         c["commit"]["message"].splitlines()[0][:42], flag))
    print("   >>> 最新提交时间: %s | 我推的: %d" % (latest, mine))
    print()
