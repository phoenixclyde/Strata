#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测 fork 的 GitHub Actions 到底能不能跑（不看记录，直接打 API）。

只读 + 一次 dispatch 尝试（dispatche 是唯一能证明"能不能触发"的办法）。
"""
import io
import json
import urllib.error
import urllib.request

TOK = io.open("deploy/tmp/_tok.txt", encoding="utf-8").read().strip()
REPO = "phoenixclyde/Strata"
BASE = "https://api.github.com/repos/" + REPO


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + TOK,
                                          "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28",
                                          "User-Agent": "strata-w1035"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, repr(e)


st, body = call("GET", "")
print("GET repo                         ->", st)
if st == 200:
    d = json.loads(body)
    print("   full_name=%s  default_branch=%s  archived=%s  disabled=%s"
          % (d.get("full_name"), d.get("default_branch"), d.get("archived"), d.get("disabled")))

st, body = call("GET", "/actions/workflows")
print("GET actions/workflows            ->", st)
if st == 200:
    for w in json.loads(body).get("workflows", []):
        print("   %-28s state=%-10s path=%s" % (w.get("name"), w.get("state"), w.get("path")))
elif st == 403 or st == 404:
    print("   " + body[:300])

st, body = call("GET", "/actions/runs?per_page=5")
print("GET actions/runs?per_page=5      ->", st)
if st == 200:
    runs = json.loads(body).get("total_count", 0)
    print("   total_count=%s" % runs)
    for r in json.loads(body).get("workflow_runs", [])[:5]:
        print("   #%s %-26s %-9s %s" % (r.get("run_number"), r.get("name")[:26],
                                        r.get("conclusion"), r.get("created_at")))
elif st != 200:
    print("   " + body[:300])

st, body = call("POST", "/actions/workflows/downstream-gate.yml/dispatches",
                {"ref": "gfx906/mi50"})
print("POST dispatch downstream-gate    ->", st)
print("   " + body.replace("\n", " ")[:260])
