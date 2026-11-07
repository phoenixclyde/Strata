# -*- coding: utf-8 -*-
"""Why does 'Minimal serving runtime' fail on our branches?

Authoritative source: the GitHub API (run -> jobs -> steps, plus the raw job log).
Prints only names/conclusions/lines -- never the token.
"""
import io
import json
import sys
import urllib.request
import zipfile

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"


def api(path, raw=False):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "token " + TOK,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "albus-w863"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if raw else json.loads(data)


run_id = sys.argv[1] if len(sys.argv) > 1 else "41286635139"

run = api("/repos/%s/actions/runs/%s" % (REPO, run_id))
print("RUN %s" % run_id)
print("  workflow   : %s (%s)" % (run["name"], run["path"]))
print("  event      : %s   branch/tag: %s" % (run["event"], run.get("head_branch")))
print("  head_sha   : %s" % run["head_sha"][:10])
print("  conclusion : %s   attempt %s" % (run["conclusion"], run["run_attempt"]))
print("  created    : %s   -> updated %s" % (run["created_at"], run["updated_at"]))

jobs = api("/repos/%s/actions/runs/%s/jobs?per_page=20" % (REPO, run_id))["jobs"]
for j in jobs:
    print("\nJOB %s  [%s]  %s -> %s" % (j["name"], j["id"], j["started_at"], j["completed_at"]))
    print("  runner: %s  conclusion: %s" % (j.get("runner_name"), j["conclusion"]))
    for s in j["steps"]:
        print("   %2d %-52s %s" % (s["number"], s["name"][:52], s["conclusion"]))
    # annotations attached to the job's check run
    try:
        ann = api("/repos/%s/check-runs/%s/annotations" % (REPO, j["id"]))
        for a in ann:
            print("  ANNOTATION [%s] %s:%s  %s" % (a.get("annotation_level"), a.get("path"),
                                                   a.get("start_line"), a.get("message", "")[:300]))
    except Exception as e:
        print("  annotations: n/a (%s)" % e)

    if j["conclusion"] not in ("success", "skipped", None):
        print("  --- job log tail (last 120 lines) ---")
        try:
            blob = api("/repos/%s/actions/jobs/%s/logs" % (REPO, j["id"]), raw=True)
            if blob[:2] == b"PK":
                zf = zipfile.ZipFile(io.BytesIO(blob))
                txt = "\n".join(zf.read(n).decode("utf-8", "replace") for n in zf.namelist())
            else:
                txt = blob.decode("utf-8", "replace")
            lines = [l for l in txt.splitlines() if l.strip()]
            for l in lines[-120:]:
                print("   | " + l[:240])
        except Exception as e:
            print("   log unavailable: %s" % e)
