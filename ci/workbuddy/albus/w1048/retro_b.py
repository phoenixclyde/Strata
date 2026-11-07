#!/usr/bin/env python3
# W1048 retro Tier B (round 2): reconstruct pa4 and pa7 candidate trees from the
# exact patch scripts that built them.  pa2 is NOT reconstructed here: its patch
# anchors match no committed state, so it is registered as an exemption whose
# content landing commit is 3b935ddf (see CI_RUNS.tsv).
import pathlib
import shutil
import subprocess
import sys

R = "/home/albus/strata166/pr/k10"
TMP = pathlib.Path("/home/albus/strata166/tmp/w1048")
PUSH = TMP / "push"


def git(*a, cwd=R):
    r = subprocess.run(["git", "-C", cwd] + list(a), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print("git", " ".join(a)[:80], "->", r.returncode)
    if r.returncode != 0:
        print(r.stdout[-1000:])
    return r


TIER_B = [
    ("pa4-recon", "8b5e547fa64fad8a67861731e6aa33f0bff5055d", "pa4_patch.py"),
    ("pa7-recon", "62d10e25cfb094ce4c2092aaae4d5f01cc6168b4", "pa7_patch.py"),
]


def main():
    # drop the aborted pa2 worktree if present
    git("worktree", "prune")
    wt0 = TMP / "wt-pa2-recon"
    if wt0.exists():
        shutil.rmtree(wt0)
        git("worktree", "prune")

    results = []
    for name, base, patch in TIER_B:
        wt = TMP / ("wt-" + name)
        if wt.exists():
            shutil.rmtree(wt)
        c = git("worktree", "add", "--detach", str(wt), base)
        if c.returncode != 0:
            raise SystemExit("worktree add failed " + name)
        txt = (PUSH / patch).read_text(encoding="utf-8", errors="replace")
        txt = txt.replace("/home/albus/strata166/pr/port-all", str(wt))
        adj = TMP / ("adj_" + patch)
        adj.write_text(txt, encoding="utf-8", newline="\n")
        r = subprocess.run([sys.executable, str(adj)], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print("patch", name, "->", r.returncode)
        print(r.stdout[-600:])
        if r.returncode != 0:
            raise SystemExit("patch failed " + name)
        st = git("status", "--porcelain", cwd=str(wt))
        if not st.stdout.strip():
            raise SystemExit("patch changed nothing " + name)
        git("add", "-A", cwd=str(wt))
        msg = ("[retro W1048] reconstruct %s on %s from %s\n\n"
               "The historical candidate binary was built from this exact patch script on\n"
               "this exact base, but the work tree was never committed.  This commit replays\n"
               "the script so the change is versioned and CI-able.  Evidence grade B+: patch\n"
               "and base are recorded build inputs; only unrelated worktree drift is unknown.\n" % (name, base[:8], patch))
        c = git("-c", "user.name=albus", "-c", "user.email=albus@localhost",
                "commit", "-m", msg, cwd=str(wt))
        if c.returncode != 0:
            raise SystemExit("commit failed " + name)
        sha = git("rev-parse", "HEAD", cwd=str(wt)).stdout.strip()
        branch = "ci/retro/" + name
        p = git("push", "origin", "HEAD:refs/heads/" + branch, cwd=str(wt))
        if p.returncode != 0:
            raise SystemExit("push failed " + name)
        results.append((branch, sha))
        git("worktree", "remove", "--force", str(wt))

    print("=== TIER B REFS ===")
    for b, s in results:
        print(b, s)
    print("=== ALL RETRO BRANCHES ON ORIGIN ===")
    ls = git("ls-remote", "--heads", "origin", "ci/retro")
    print(ls.stdout)


if __name__ == "__main__":
    main()
