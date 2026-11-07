#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_find_repo.py -- 找 phoenixclyde 下的 strata 项目。"""
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
print("token identity:", me.get("login"), "|", st)

st, repos = get("https://api.github.com/users/phoenixclyde/repos?per_page=100&sort=updated")
print("phoenixclyde repos:", st, len(repos) if isinstance(repos, list) else repos.get("message"))
if isinstance(repos, list):
    for r in repos:
        name = r["name"]
        mark = "  <<< strata" if "strata" in name.lower() else ""
        print("  %-40s %-8s %s%s" % (name, r.get("default_branch"), r.get("size"), mark))
