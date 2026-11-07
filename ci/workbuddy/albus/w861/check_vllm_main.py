#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_check_vllm_main.py -- 查 vLLM 官方主仓库有没有被我碰过。

口径：
 1. 仓库 pushed_at（GitHub 自己维护，改不了）
 2. 最近 10 条提交的作者/时间
 3. 按 author=phoenixclyde 直接搜该仓库，看有没有我名下的提交
"""
import json
import os
import urllib.parse
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


REPO = "vllm-project/vllm"
st, js = get("https://api.github.com/repos/%s" % REPO)
print("=== %s ===" % REPO)
if st == 200:
    print("   pushed_at:", js.get("pushed_at"))
    print("   default_branch:", js.get("default_branch"))
    perms = js.get("permissions") or {}
    print("   permissions:", perms)
else:
    print("   HTTP", st, js.get("message"))

print("\n--- 最近 6 条提交 ---")
st, cs = get("https://api.github.com/repos/%s/commits?per_page=6" % REPO)
if st == 200:
    for c in cs:
        a = c["commit"]["author"]
        print("   %s  %-20s %s  %s" % (c["sha"][:10], a["name"][:20], a["date"],
                                       c["commit"]["message"].splitlines()[0][:42]))
else:
    print("   HTTP", st, cs.get("message"))

print("\n--- 按 author=phoenixclyde 搜该仓库 ---")
q = urllib.parse.quote("repo:%s author:phoenixclyde" % REPO)
st, js = get("https://api.github.com/search/commits?q=%s&per_page=5" % q)
print("   HTTP", st, "total_count:", js.get("total_count"), js.get("message", ""))
if isinstance(js.get("items"), list):
    for it in js["items"][:5]:
        print("   ", it["sha"][:10], it["commit"]["author"]["date"],
              it["commit"]["message"].splitlines()[0][:50])
