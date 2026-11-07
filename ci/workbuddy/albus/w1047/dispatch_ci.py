"""Dispatch Downstream gate for every production/candidate branch and wait."""
import io
import json
import time
import urllib.error
import urllib.request

TOKEN = io.open("deploy/tmp/_tok.txt").read().strip()
REPO = "phoenixclyde/Strata"
WF = "downstream-gate.yml"
REFS = [
    "gfx906/lcpp-k10",
    "gfx906/attn-opt",
    "gfx906/dot48",
    "gfx906/hc-dp4a",
    "ci/w1046-gates",
    "ci/w1046-hooks",
    "ci/w1047-coverage",
]


def api(url, data=None, method=None):
    headers = {"Authorization": "Bearer " + TOKEN,
               "Accept": "application/vnd.github+json",
               "User-Agent": "albus"}
    if data is not None:
        raw = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    else:
        raw = None
    req = urllib.request.Request(url, data=raw, headers=headers, method=method or ("POST" if raw else "GET"))
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def dispatch(ref):
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WF}/dispatches"
    try:
        st, _ = api(url, {"ref": ref})
        print("dispatch", ref, st)
        return st in (200, 204)
    except urllib.error.HTTPError as e:
        print("dispatch", ref, "HTTP", e.code, e.read()[:300])
        return False


def runs():
    st, raw = api(f"https://api.github.com/repos/{REPO}/actions/runs?per_page=100")
    return json.loads(raw).get("workflow_runs", [])


def sha_for_ref(ref):
    st, raw = api(f"https://api.github.com/repos/{REPO}/commits/{ref}")
    return json.loads(raw)["sha"]


def main():
    want = {}
    for ref in REFS:
        sha = sha_for_ref(ref)
        want[sha] = ref
        dispatch(ref)
        time.sleep(1)
    deadline = time.time() + 900
    pending = dict(want)
    while pending and time.time() < deadline:
        for r in runs():
            sha = r.get("head_sha")
            if sha in pending and r.get("name") == "Downstream gate":
                if r.get("status") == "completed":
                    print("completed", pending[sha], sha[:8], r.get("conclusion"), r.get("html_url"))
                    if r.get("conclusion") == "success":
                        pending.pop(sha)
                    else:
                        raise SystemExit(f"CI failed for {pending[sha]}")
        if pending:
            print("pending", [(ref, sha[:8]) for sha, ref in pending.items()])
            time.sleep(20)
    if pending:
        raise SystemExit("timeout waiting for CI: " + ",".join(pending.values()))
    print("DISPATCH_CI: PASS", len(want), "refs")


if __name__ == "__main__":
    main()
