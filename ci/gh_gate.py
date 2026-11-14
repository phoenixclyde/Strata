#!/usr/bin/env python3
"""A deploy needs a green GitHub Actions run for the commit being deployed.

**THE SINGLE AUTHORITATIVE CRITERION (D21, 2026-11-14)**

    A commit that produces an engine binary must carry a completed, successful
    `downstream-gate.yml` run for ITS OWN sha.  A commit that produces no binary
    (a dependency bump, a report, a docs change) must not be blocked by this
    step; it is covered by the nearest ancestor that DOES carry a green run,
    provided nothing between that ancestor and HEAD touches the engine sources.

Why: the two gates used to disagree.  `deploy_gate.py` D7 only asks for a
coverage row for a binary-producing sha, so `5579addaa` (PR#2, one line of
`requirements-nvfp4-local.txt`) passed D7 while `deploy.sh` step 0 refused it
outright -- the pipeline could never reach the install step for a tree whose
engine bytes are identical to a sha that *was* covered.  The fix is not an
exemption flag and not a paths-whitelist edit: it is a second, narrower leg
with its own evidence, printed on every use.

Exit codes
  0  a completed run for this sha concluded `success`, **or** the sha is a
     non-engine descendant of such a sha (the chain is printed)
  6  no run for this sha and no acceptable ancestor chain yet (use --wait)
  7  the latest run for this sha did not succeed (URL printed)
  8  cannot talk to the API (no token / auth / network)

Usage
  gh_gate.py [--sha SHA] [--wait SEC] [--repo OWNER/NAME] [--workflow FILE]
             [--no-ancestor-chain] [--quiet] [--self-test]

The ancestor leg can be turned off with --no-ancestor-chain; with it off this
script is exactly the old "this sha must have a green run" gate.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
API = "https://api.github.com"
DEF_REPO = "phoenixclyde/Strata"
DEF_WORKFLOW = "downstream-gate.yml"

# What an engine binary is built from.  A change under any of these makes the
# ancestor's run stop standing in for HEAD's.  Deliberately conservative: a
# false "engine changed" costs one CI run, a false "engine unchanged" ships an
# unverified binary.
ENGINE_PATHS = ("src/", "include/", "cmake/", "third_party/", "metal/", "sycl/")
ENGINE_FILES = ("CMakeLists.txt", "CMakePresets.json", "setup.py", "Dockerfile")


def head_sha(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def head_branch(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root)] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def engine_paths_changed(paths):
    """The engine-affecting subset of a diff.  Pure function: this is what the
    self-test exercises, so the rule can be checked without a network or a repo."""
    hits = []
    for p in paths:
        if not p:
            continue
        q = p.replace("\\", "/").strip()
        if q in ENGINE_FILES or any(q.startswith(pref) for pref in ENGINE_PATHS):
            hits.append(q)
    return hits


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


def api(path, tok, tries=3):
    """Read one API resource. Retries a truncated/slow body: the branch-runs list is
    big enough that a short read shows up as IncompleteRead, and a deploy gate must
    not turn a flaky socket into a REFUSE."""
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "Accept-Encoding": "identity",       # a 600 KB gzip body is what truncated before
        "User-Agent": "strata-gh-gate"})
    last = None
    for i in range(max(1, tries)):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return 200, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return e.code, e.read()[:300].decode("utf-8", "replace")
        except Exception as e:                      # IncompleteRead, timeout, reset
            last = e
            if i + 1 < tries:
                time.sleep(1.5 * (i + 1))
    return -1, "transport error after %d tries: %r" % (tries, last)


def runs_for(repo, workflow, sha, tok):
    st, body = api("/repos/%s/actions/workflows/%s/runs?head_sha=%s&per_page=10" % (repo, workflow, sha), tok)
    if st != 200 or not isinstance(body, dict):
        return st, None
    return st, body.get("workflow_runs", [])


def runs_for_branch(repo, workflow, branch, tok, per_page=15):
    st, body = api("/repos/%s/actions/workflows/%s/runs?branch=%s&per_page=%d"
                   % (repo, workflow, urllib.parse.quote(branch, safe=""), per_page), tok)
    if st != 200 or not isinstance(body, dict):
        return st, None
    return st, body.get("workflow_runs", [])


def ancestor_chain(repo, workflow, sha, tok, branch, root):
    """The second leg: (green_sha, run, changed_paths) or (None, reason)."""
    if not branch or branch == "HEAD":
        return None, "detached HEAD: no branch to look up an ancestor run on"
    st, runs = runs_for_branch(repo, workflow, branch, tok)
    if st == -1:
        # 传输层（截断/超时/重置）不是「没有 run」。把它折叠成 FAIL 会让部署门把网络抖动
        # 说成代码问题（第 5 种观测层缺陷，2026-11-14 实测：613 KB 响应在 166 上稳定 IncompleteRead）。
        return None, "UNCONFIRMED: transport error listing runs for %s (%s)" % (branch, runs)
    if st != 200 or runs is None:
        return None, "cannot list runs for branch %s (HTTP %s)" % (branch, st)
    for r in runs:
        if r.get("status") != "completed" or r.get("conclusion") != "success":
            continue
        g = r.get("head_sha") or ""
        if not g or g == sha:
            continue
        rc, _ = git(root, "merge-base", "--is-ancestor", g, sha)
        if rc != 0:
            continue
        rc2, out = git(root, "diff", "--name-only", "%s..%s" % (g, sha))
        if rc2 != 0:
            return None, "cannot diff %s..%s" % (g[:12], sha[:12])
        return (g, r, [x for x in out.splitlines() if x.strip()]), None
    return None, "no successful run on %s is an ancestor of %s" % (branch, sha[:12])


def self_test():
    """Negative tests first: a rule that cannot fail is not a rule."""
    cases = [
        ("PR#2 的一条依赖清单", ["requirements-nvfp4-local.txt"], []),
        ("docs only", ["docs/DETAILS.md", "README.md"], []),
        ("ci 脚本", ["ci/gh_gate.py"], []),
        ("引擎源", ["src/program/generate.cpp"], ["src/program/generate.cpp"]),
        ("头文件", ["include/strata/core/mtp.hpp"], ["include/strata/core/mtp.hpp"]),
        ("CMake", ["CMakeLists.txt"], ["CMakeLists.txt"]),
        ("vendored ggml", ["third_party/strata-ggml/ggml/src/ggml-cuda/mmq.cu"],
         ["third_party/strata-ggml/ggml/src/ggml-cuda/mmq.cu"]),
        ("混合（必须判引擎变）", ["requirements.txt", "src/kernels/cuda/mmq.cu"], ["src/kernels/cuda/mmq.cu"]),
        ("反斜杠路径", ["src\\program\\generate.cpp"], ["src/program/generate.cpp"]),
        ("空", [], []),
    ]
    bad = 0
    for name, paths, want in cases:
        got = engine_paths_changed(paths)
        ok = got == want
        bad += 0 if ok else 1
        print("  %-24s %-4s got=%s" % (name, "PASS" if ok else "FAIL", got))
    print("GH_GATE_SELF_TEST: %d/%d" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None, help="commit to check (default: repo HEAD)")
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--workflow", default=DEF_WORKFLOW)
    ap.add_argument("--wait", type=int, default=0, help="poll for up to N seconds when the run is missing or running")
    ap.add_argument("--no-ancestor-chain", action="store_true",
                    help="turn off the non-engine-descendant leg (old behaviour: this sha must have a run)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

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
                if not a.no_ancestor_chain:
                    got, why = ancestor_chain(a.repo, a.workflow, sha, tok, head_branch(ROOT), ROOT)
                    if got is not None:
                        green, run, changed = got
                        hits = engine_paths_changed(changed)
                        if not hits:
                            print("GH_GATE: PASS %s via-binary-ancestor %s run #%s %s"
                                  % (sha[:12], green[:12], run.get("run_number"), run.get("html_url")))
                            print("  no run for %s itself; %d non-engine path(s) changed since %s: %s"
                                  % (sha[:12], len(changed), green[:12],
                                     ", ".join(changed[:8]) + (" …" if len(changed) > 8 else "")))
                            return 0
                        print("GH_GATE: FAIL %s has no run and %d engine path(s) changed since the green "
                              "%s -- this commit needs its own run:" % (sha[:12], len(hits), green[:12]))
                        for h in hits[:12]:
                            print("    " + h)
                        return 6
                    if "UNCONFIRMED" in why:
                        print("GH_GATE: UNCONFIRMED %s -- %s" % (sha[:12], why))
                        print("  transport error is not a verdict: retry, or re-run with --wait. "
                              "No PASS and no FAIL is claimed for this sha.")
                        return 9
                    print("GH_GATE: FAIL no `%s` run exists for %s in %s." % (a.workflow, sha[:12], a.repo))
                    print("  ancestor leg: " + why)
                else:
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
