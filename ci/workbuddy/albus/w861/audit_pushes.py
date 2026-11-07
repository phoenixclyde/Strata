#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_audit_pushes.py -- 核对本次会话到底推到了哪些仓库。"""
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


st, me = get("https://api.github.com/user")
print("token ->", me.get("login"), "(%s)" % st)

for repo in ("phoenixclyde/Strata", "KIntegrated/vllm-gfx906-mobydick", "phoenixclyde/vllm-gfx906-mobydick"):
    st, js = get("https://api.github.com/repos/%s/commits?per_page=3" % repo)
    print("\n=== %s  (%s)" % (repo, st))
    if st != 200:
        print("   ", js.get("message"))
        continue
    for c in js:
        msg = c["commit"]["message"].splitlines()[0][:60]
        who = c["commit"]["author"]["name"]
        when = c["commit"]["author"]["date"]
        print("   %s  %-14s %s  %s" % (c["sha"][:10], who, when, msg))
