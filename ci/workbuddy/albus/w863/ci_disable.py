# -*- coding: utf-8 -*-
"""[W863] Disable the workflows that have nothing to do with a downstream fork.

Repository-setting layer, not a code change:
  * nothing enters git -> zero rebase conflict with upstream
  * `enable` puts any of them back in one call
Reason per workflow is in deploy/CI_CD_BLUEPRINT.md §2.

Kept active: Minimal serving runtime, Portable monitor client.
"""
import json
import sys
import urllib.request

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"
KEEP = {"Minimal serving runtime", "Portable monitor client"}
DRY = "--apply" not in sys.argv


def api(path, method="GET"):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        headers={"Authorization": "token " + TOK,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "albus-w863"})
    with urllib.request.urlopen(req, timeout=45) as r:
        body = r.read()
    return json.loads(body) if body.strip() else {}


wfs = api("/repos/%s/actions/workflows" % REPO)["workflows"]
print("%-34s %-10s %s" % ("name", "state", "id"))
for w in wfs:
    mark = "KEEP" if w["name"] in KEEP else ("disable" if not DRY else "would disable")
    print("%-34s %-10s %-12s %s" % (w["name"][:34], w["state"], w["id"], mark))

if DRY:
    print("\n(dry run -- pass --apply to change)")
    raise SystemExit(0)

print()
for w in wfs:
    if w["name"] in KEEP:
        continue
    if w["state"] == "disabled_manually":
        print("already disabled: %s" % w["name"])
        continue
    api("/repos/%s/actions/workflows/%s/disable" % (REPO, w["id"]), method="PUT")
    print("disabled: %s" % w["name"])

print("\n--- after ---")
for w in api("/repos/%s/actions/workflows" % REPO)["workflows"]:
    print("%-34s %s" % (w["name"][:34], w["state"]))
