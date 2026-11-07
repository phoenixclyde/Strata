#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""strata-ci publish -- write what happened on 166 back onto the commit in GitHub.

Why: the GPU work cannot run on a GitHub runner, so L2-L4 live on the 166 host.  The
result was that GitHub saw nothing: commit 17929597 had `combined status: pending, 0
statuses` even though that exact tree was built, benched and (earlier) deployed here.

The documented pattern for exactly this case is the Commit Statuses API: the external
system runs the job and posts a status back, so GitHub holds the state and the link while
the compute and the data stay inside.  Two rules from the docs that this follows:
  * post against the commit SHA, never the branch name (a branch moves; the SHA does not);
  * give it a context, so several checks can coexist (`strata/166`).
Checks API would give step-level detail, but it needs a GitHub App; statuses are enough
for "built / benched / deployed, with numbers".

Run from the workstation (it holds the token); it reads 166 over ssh.
Usage: publish.py [--sha SHA] [--state success|pending|failure|error] [--desc TEXT] [--dry-run]
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"
RS = r"D:\workbuddy_space\strata_ws\albus\rs.py"
CTX = "strata/166"


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


def on_166(cmd, timeout=120):
    p = subprocess.run([sys.executable, RS, "-c", cmd], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default="")
    ap.add_argument("--state", default="success")
    ap.add_argument("--desc", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    sha = a.sha or on_166("git -C /home/albus/strata166/pr/strata-fork rev-parse HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise SystemExit("could not resolve a commit sha (got %r)" % sha)

    # what is actually running, straight from the host
    snap = on_166(
        "python3 - <<'PY'\n"
        "import json,glob,os,subprocess\n"
        "cfg=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))\n"
        "runs=sorted(glob.glob('/home/albus/strata166/ci/state/runs/*.json'))\n"
        "b=json.load(open(runs[-1])) if runs else {}\n"
        "h=subprocess.run(['curl','-s','--max-time','5','http://127.0.0.1:8090/health'],capture_output=True,text=True).stdout\n"
        "v=subprocess.run(['rocm-smi','--showmeminfo','vram'],capture_output=True,text=True).stdout\n"
        "used=[l for l in v.splitlines() if 'Used' in l]\n"
        "print(json.dumps({'exe':cfg.get('exe'),'env':len(cfg.get('env') or {}),'ok':'\"status\": \"ok\"' in h,\n"
        "  'loaded':'\"loaded\": true' in h,'vram_used':used[0].split(':')[-1].strip() if used else None,\n"
        "  'bench_run':os.path.basename(runs[-1]) if runs else None,\n"
        "  'tok_s':(b.get('metrics') or {}).get('tok_s',{}).get('median'),\n"
        "  'bench_cv':(b.get('metrics') or {}).get('tok_s',{}).get('cv_pct'),\n"
        "  'bench_tag':b.get('git_tag'),\n"
        "  'head_tag':subprocess.run(['git','-C','/home/albus/strata166/pr/strata-fork','describe',\n"
        "     '--exact-match','--tags','HEAD'],capture_output=True,text=True).stdout.strip() or None}))\n"
        "PY")

    try:
        s = json.loads(snap)
    except json.JSONDecodeError:
        raise SystemExit("could not read the host snapshot:\n" + snap[:400])

    desc = a.desc or ("%s · %s tok/s (CV %.2f%%) · VRAM %.1f GB · env %d · health %s"
                      % ((s["exe"] or "?").split("/")[-1],
                         s["tok_s"] if s["tok_s"] is not None else "?",
                         s["bench_cv"] or 0,
                         int(s["vram_used"]) / 1e9 if s["vram_used"] else 0,
                         s["env"], "ok" if s["ok"] and s["loaded"] else "NOT OK")
                      + (" · " + s["head_tag"] if s.get("head_tag") else " · UNTAGGED"))
    desc = desc[:140]

    print("sha    : %s" % sha)
    print("state  : %s" % a.state)
    print("context: %s" % CTX)
    print("desc   : %s" % desc)
    print("source : exe=%s  bench=%s  bench_tag=%s  head_tag=%s"
          % (s["exe"], s["bench_run"], s["bench_tag"], s.get("head_tag")))
    if a.dry_run:
        print("\n[dry-run] nothing posted")
        return 0

    api("/repos/%s/statuses/%s" % (REPO, sha), "POST",
        {"state": a.state, "context": CTX, "description": desc})
    st = api("/repos/%s/commits/%s/status" % (REPO, sha))
    print("\nposted. combined status now: %s" % st["state"])
    for x in st["statuses"]:
        if x["context"] == CTX:
            print("  %s -> %s | %s" % (x["context"], x["state"], x["description"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
