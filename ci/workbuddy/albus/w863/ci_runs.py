# -*- coding: utf-8 -*-
"""Is the CI red ours, or upstream's?  List workflow runs for both repos/branches."""
import json
import urllib.request

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()


def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "token " + TOK,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-w863"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


for repo in ("phoenixclyde/Strata", "Niko1221/Strata"):
    print("=" * 78)
    print(repo)
    try:
        runs = api("/repos/%s/actions/runs?per_page=30" % repo)["workflow_runs"]
    except Exception as e:
        print("  n/a:", e)
        continue
    for r in runs:
        print("  %-28s %-22s %-9s %-9s %s  %s" % (
            r["name"][:28], (r.get("head_branch") or "")[:22], r["event"],
            r["conclusion"], r["created_at"][:16], r["head_sha"][:8]))
