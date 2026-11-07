#!/usr/bin/env python3
# W1048: dispatch Downstream gate on every retro ref and bind runs to history.
import io
import json
import time
import urllib.error
import urllib.request

TOKEN = io.open("deploy/tmp/_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"
WF = "downstream-gate.yml"
REFS = [
    "ci/retro/fa8e6761-k10-pin",
    "ci/retro/79516b21-pa0",
    "ci/retro/8b44f3d1-pa1",
    "ci/retro/806a4b2f-tqfix",
    "ci/retro/3b935ddf-pa2land",
    "ci/retro/8b5e547f-pa3",
    "ci/retro/62d10e25-pa5",
    "ci/retro/91a7c5a4-pa6pa7",
    "ci/retro/064aa6c0-hc-first",
    "ci/retro/pa4-recon",
    "gfx906/port-all",          # branch tip too: every pushed change visible
]


def api(url, data=None, method=None):
    headers = {"Authorization": "Bearer " + TOKEN,
               "Accept": "application/vnd.github+json",
               "User-Agent": "albus"}
    raw = None
    if data is not None:
        raw = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=raw, headers=headers,
                                 method=method or ("POST" if raw else "GET"))
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def sha_for_ref(ref):
    st, raw = api("https://api.github.com/repos/%s/commits/%s" % (REPO, ref))
    return json.loads(raw)["sha"]


def dispatch(ref):
    url = "https://api.github.com/repos/%s/actions/workflows/%s/dispatches" % (REPO, WF)
    try:
        st, _ = api(url, {"ref": ref})
        print("dispatch", ref, st)
        return st in (200, 204)
    except urllib.error.HTTPError as e:
        print("dispatch", ref, "HTTP", e.code, e.read()[:200])
        return False


def main():
    want = {}
    for ref in REFS:
        sha = sha_for_ref(ref)
        want[sha] = ref
        dispatch(ref)
        time.sleep(1)
    print("=== WANTED ===")
    for sha, ref in want.items():
        print(ref, sha)
    deadline = time.time() + 1200
    pending = dict(want)
    done = {}
    while pending and time.time() < deadline:
        st, raw = api("https://api.github.com/repos/%s/actions/runs?per_page=60" % REPO)
        for r in json.loads(raw).get("workflow_runs", []):
            sha = r.get("head_sha")
            if sha in pending and r.get("name") == "Downstream gate":
                if r.get("status") == "completed":
                    print("completed", pending[sha], sha[:8], r.get("conclusion"), r.get("id"))
                    if r.get("conclusion") == "success":
                        done[sha] = (pending[sha], r.get("id"), r.get("html_url"))
                        del pending[sha]
        if pending:
            time.sleep(20)
    print("=== DONE %d / %d ===" % (len(done), len(want)))
    for sha, (ref, rid, url) in done.items():
        print("RUN\t%s\t%s\t%s\t%s" % (ref, sha, rid, url))
    if pending:
        print("=== PENDING ===")
        for sha, ref in pending.items():
            print("PENDING\t%s\t%s" % (ref, sha))
    io.open("albus/w1048/retro_runs.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps({sha: {"ref": v[0], "run_id": v[1], "url": v[2]} for sha, v in done.items()},
                   indent=2))


if __name__ == "__main__":
    main()
