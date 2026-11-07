#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check whether the push actually triggered the Downstream gate workflow.

Token is read from deploy/tmp/_tok.txt and NEVER printed. If GitHub is not
reachable from this host, the script says so instead of guessing.
"""
import io
import json
import pathlib
import urllib.request

ROOT = pathlib.Path("D:/workbuddy_space/strata_ws")
tok = (ROOT / "deploy" / "tmp" / "_tok.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
base = "https://api.github.com/repos/phoenixclyde/Strata"
urls = [
    base + "/actions/workflows/downstream-gate.yml/runs?branch=gfx906/mi50&per_page=3",
    base + "/commits/gfx906/mi50",
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers={
            "Authorization": "Bearer " + tok,
            "Accept": "application/vnd.github+json",
            "User-Agent": "strata-round-gate",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        if "workflow_runs" in d:
            print("workflow_runs total =", d.get("total_count"))
            for run in d["workflow_runs"][:3]:
                print("  %s | %s | %s | sha=%s | created=%s" % (
                    run["run_number"], run["status"], run.get("conclusion"),
                    run["head_sha"][:8], run["created_at"]))
        elif "sha" in d:
            print("remote HEAD =", d["sha"][:12])
    except Exception as e:
        print("QUERY_FAILED", u.split("/")[-1][:40], type(e).__name__, str(e)[:90])
