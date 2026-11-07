#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_check_upstream.py -- 确认没碰到任何"上游"仓库。

查：
 1. phoenixclyde/Strata 的 parent（fork 自哪里）
 2. 该 parent 的最近提交（有没有我的）
 3. token 能访问的全部仓库清单（划清边界）
 4. 记忆里提到的 Niko1221/Strata 最近提交
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


st, js = get("https://api.github.com/repos/phoenixclyde/Strata")
print("=== phoenixclyde/Strata ===")
print("   HTTP", st)
if st == 200:
    par = js.get("parent")
    src = js.get("source")
    print("   fork:", js.get("fork"))
    print("   parent :", par["full_name"] if par else None)
    print("   source :", src["full_name"] if src else None)

    if par:
        pn = par["full_name"]
        st2, c = get("https://api.github.com/repos/%s/commits?per_page=3" % pn)
        print("   --- parent 最近 3 条 (%s, HTTP %s) ---" % (pn, st2))
        if st2 == 200:
            for x in c:
                a = x["commit"]["author"]
                print("      %s  %-14s %s  %s" % (x["sha"][:10], a["name"], a["date"],
                                                  x["commit"]["message"].splitlines()[0][:45]))

print("\n=== token 能访问的仓库（全部）===")
st, repos = get("https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member")
if st == 200:
    for r in repos:
        print("   %-45s %s" % (r["full_name"], "fork" if r["fork"] else ""))
else:
    print("   HTTP", st, repos.get("message"))

print("\n=== Niko1221/Strata（记忆里的上游）===")
st, c = get("https://api.github.com/repos/Niko1221/Strata/commits?per_page=3")
print("   HTTP", st)
if st == 200:
    for x in c:
        a = x["commit"]["author"]
        print("   %s  %-14s %s  %s" % (x["sha"][:10], a["name"], a["date"],
                                      x["commit"]["message"].splitlines()[0][:45]))
else:
    print("   ", c.get("message"))
