# -*- coding: utf-8 -*-
"""[W863] Fire the upstream watcher once by hand and report what it did.

workflow_dispatch needs the file to exist on the default branch -- that is why a copy of
upstream-watch.yml lives on `main`.  Dispatch ref stays `main`; the job itself checks out
gfx906/mi50 (declared in the yml).
"""
import json
import time
import urllib.request

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        "https://api.github.com" + path, data=data, method=method,
        headers={"Authorization": "token " + TOK,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "albus-w863",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    return json.loads(raw) if raw.strip() else {}


wfs = {w["name"]: w for w in api("/repos/%s/actions/workflows" % REPO)["workflows"]}
w = wfs.get("Upstream watch")
if not w:
    raise SystemExit("Upstream watch is not registered -- is the file on the default branch?")

print("workflow: %s id=%s state=%s path=%s" % (w["name"], w["id"], w["state"], w["path"]))
print("dispatching on ref=main ...")
api("/repos/%s/actions/workflows/%s/dispatches" % (REPO, w["id"]), "POST", {"ref": "main"})
print("dispatched\n")

for _ in range(20):
    time.sleep(6)
    runs = api("/repos/%s/actions/workflows/%s/runs?per_page=1" % (REPO, w["id"]))["workflow_runs"]
    if not runs:
        print("no run yet"); continue
    r = runs[0]
    print("run %s  status=%s  conclusion=%s  event=%s  branch=%s"
          % (r["id"], r["status"], r["conclusion"], r["event"], r.get("head_branch")))
    if r["conclusion"] or r["status"] == "completed":
        break

if runs:
    jid = api("/repos/%s/actions/runs/%s/jobs" % (REPO, runs[0]["id"]))["jobs"]
    for j in jid:
        print("\njob %s: %s" % (j["name"], j["conclusion"]))
        for s in j["steps"]:
            print("  %2d %-42s %s" % (s["number"], s["name"][:42], s["conclusion"]))

issues = api("/repos/%s/issues?labels=upstream-watch&state=all&per_page=10" % REPO)
print("\nupstream-watch issues: %d" % len(issues))
for i in issues:
    print("  #%s [%s] %s" % (i["number"], i["state"], i["title"]))
