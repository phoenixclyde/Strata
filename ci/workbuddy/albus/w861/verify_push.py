#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_verify_push.py -- 严格确认：有没有推到 KIntegrated（错的那个）。

三件事：
 1. KIntegrated/vllm-gfx906-mobydick 的 docs/hipblaslt_gfx906_investigation.md 是否存在
 2. 该仓库最近 5 条提交里有没有 2026-10-31 之后、作者不是 Kevin Read 的
 3. phoenixclyde/Strata 里我们推的那个文件确认存在
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


print("=== 1) KIntegrated 里有没有这个文件 ===")
p = ("https://api.github.com/repos/KIntegrated/vllm-gfx906-mobydick/contents/"
     "docs/hipblaslt_gfx906_investigation.md")
st, js = get(p)
print("   HTTP", st, "->", js.get("message") if st != 200 else "EXISTS(不该存在)")

print("\n=== 2) KIntegrated 最近 5 条提交 ===")
st, js = get("https://api.github.com/repos/KIntegrated/vllm-gfx906-mobydick/commits?per_page=5")
if st == 200:
    for c in js:
        a = c["commit"]["author"]
        print("   %s  %-14s %s  %s" % (c["sha"][:10], a["name"], a["date"],
                                      c["commit"]["message"].splitlines()[0][:50]))
else:
    print("   HTTP", st, js.get("message"))

print("\n=== 3) phoenixclyde/Strata 里我们的文件 ===")
st, js = get("https://api.github.com/repos/phoenixclyde/Strata/contents/docs/hipblaslt_gfx906_investigation.md")
print("   HTTP", st, "size=", js.get("size"), "sha=", str(js.get("sha"))[:12])
