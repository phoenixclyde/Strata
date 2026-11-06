#!/usr/bin/env python3
"""A deploy needs a green GitHub Actions run for the exact commit being deployed.

Why this is the gate and not the local script: the change lands on GitHub, so the gate has to
run on GitHub -- on a clean runner, with nothing from this working copy.  The local
`ci/round_gate.py` stays as a pre-push convenience; it is no longer evidence.

State of the world this was written in (W1029): `downstream-gate` is `active`, and
`GET /repos/.../actions/permissions` says `enabled: true`, yet every `workflow_dispatch` returns
**422 "Actions has been disabled for this repository"** and pushes produce no runs.  That is a
repository-level switch the REST API cannot flip.  This script therefore refuses to deploy and
names the two facts to check, instead of pretending the gate ran.

Exit codes
  0  a completed run for this sha concluded `success`
  6  no run for this sha yet, or the run is still in progress (use --wait to poll)
  7  the latest run for this sha did not succeed (URL printed)
  8  cannot talk to the API (no token / auth / network)

Usage
  gh_gate.py [--sha SHA] [--wait SEC] [--repo OWNER/NAME] [--workflow FILE] [--quiet]
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
API = "https://api.github.com"
DEF_REPO = "phoenixclyde/Strata"
DEF_WORKFLOW = "downstream-gate.yml"


def head_sha(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def token():
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "STRATA_GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name].strip()
    for p in (ROOT / "deploy" / "tmp" / "_tok.txt", pathlib.Path.home() / ".config" / "strata" / "gh_token"):
        if p.is_file():
            line = p.read_text(encoding="utf-8").strip().splitlines()
            if line and line[0].strip():
                return line[0].strip()
    return ""


def api(path, tok):
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "strata-gh-gate"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "replace")


def runs_for(repo, workflow, sha, tok):
    st, body = api("/repos/%s/actions/workflows/%s/runs?head_sha=%s&per_page=10" % (repo, workflow, sha), tok)
    if st != 200 or not isinstance(body, dict):
        return st, None
    return st, body.get("workflow_runs", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None, help="commit to check (default: repo HEAD)")
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--workflow", default=DEF_WORKFLOW)
    ap.add_argument("--wait", type=int, default=0, help="poll for up to N seconds when the run is missing or running")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    sha = a.sha or head_sha(ROOT)
    if not sha:
        print("GH_GATE: FAIL (no sha, not a git tree?)")
        return 8
    tok = token()
    if not tok:
        print("GH_GATE: FAIL no token (set GITHUB_TOKEN or deploy/tmp/_tok.txt)")
        return 8

    deadline = time.time() + max(0, a.wait)
    while True:
        st, runs = runs_for(a.repo, a.workflow, sha, tok)
        if st != 200:
            print("GH_GATE: FAIL API %s for %s (%s)" % (st, a.repo, str(runs)[:160]))
            return 8
        if runs:
            latest = runs[0]
            if latest.get("status") == "completed":
                concl = latest.get("conclusion")
                if concl == "success":
                    if not a.quiet:
                        print("GH_GATE: PASS %s run #%s %s" % (sha[:12], latest.get("run_number"),
                                                               latest.get("html_url")))
                    return 0
                print("GH_GATE: FAIL run #%s concluded %s -- %s" % (latest.get("run_number"), concl,
                                                                    latest.get("html_url")))
                return 7
            if time.time() >= deadline:
                print("GH_GATE: PENDING run #%s is %s (%s); re-run with --wait" %
                      (latest.get("run_number"), latest.get("status"), latest.get("html_url")))
                return 6
        else:
            if time.time() >= deadline:
                print("GH_GATE: FAIL no `%s` run exists for %s in %s." % (a.workflow, sha[:12], a.repo))
                print("  GitHub runs on the pushed commit; check, in this order:")
                print("   1. is the sha actually on origin?   git ls-remote origin gfx906/mi50")
                print("   2. does a run appear?               GET /repos/%s/actions/runs?per_page=1" % a.repo)
                print("   3. can a dispatch start one?        422 'Actions has been disabled for this")
                print("      repository' while /actions/permissions says enabled:true means the repo")
                print("      switch is off -- only the web UI can turn it back on (Settings -> Actions")
                print("      -> General, or the banner on the Actions tab).")
                return 6
        time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
