#!/usr/bin/env python3
# W1048 retro Tier B round 3: pa7's patch requires pa6's F16D lines (the W1039
# work tree was cumulative).  Replay pa6 -> pa7 on 62d10e25, then compare the
# result with the committed 91a7c5a4 ("pa6 + pa7").  Identical means the build
# tree's content is already versioned and CI-covered at 91a7c5a4; any drift is
# committed as ci/retro/pa7-recon so nothing is lost either way.
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


def main():
    base = "62d10e25cfb094ce4c2092aaae4d5f01cc6168b4"
    wt = TMP / "wt-pa7-recon"
    if wt.exists():
        shutil.rmtree(wt)
    git("worktree", "remove", "--force", str(wt))
    git("worktree", "prune")
    c = git("worktree", "add", "-f", "--detach", str(wt), base)
    if c.returncode != 0:
        raise SystemExit("worktree add failed")

    for patch in ("pa6_patch.py", "wire_f16d.py", "pa7_patch.py"):
        txt = (PUSH / patch).read_text(encoding="utf-8", errors="replace")
        txt = txt.replace("/home/albus/strata166/pr/port-all", str(wt))
        adj = TMP / ("adj2_" + patch)
        adj.write_text(txt, encoding="utf-8", newline="\n")
        r = subprocess.run([sys.executable, str(adj)], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print("patch", patch, "->", r.returncode)
        print(r.stdout[-500:])
        if r.returncode != 0:
            raise SystemExit("patch failed " + patch)

    # compare replayed tree against the committed pa6+pa7 landing commit
    d = git("diff", "--stat", "91a7c5a4e284f71b44316927131248362802d0ef", cwd=str(wt))
    print("=== diff vs 91a7c5a4 ===")
    print(d.stdout[-1500:] or "(empty)")
    st = git("status", "--porcelain", cwd=str(wt))
    if not st.stdout.strip():
        print("REPLAY EMPTY? unexpected")
        raise SystemExit(1)

    if d.stdout.strip() == "":
        print("VERDICT: pa6+pa7 replay is byte-identical to 91a7c5a4; content landing == 91a7c5a4")
        git("worktree", "remove", "--force", str(wt))
        return

    git("add", "-A", cwd=str(wt))
    msg = ("[retro W1048] reconstruct pa7 build tree (pa6->pa7 cumulative on 62d10e25)\n\n"
           "Replays pa6_patch.py then pa7_patch.py -- the W1039 work tree was cumulative --\n"
           "on the recorded base of the strata-0.1.57-pa7 binary.  Diff against the committed\n"
           "91a7c5a4 landing is printed above; whatever drift exists is preserved here.\n")
    git("-c", "user.name=albus", "-c", "user.email=albus@localhost",
        "commit", "-m", msg, cwd=str(wt))
    sha = git("rev-parse", "HEAD", cwd=str(wt)).stdout.strip()
    p = git("push", "origin", "HEAD:refs/heads/ci/retro/pa7-recon", cwd=str(wt))
    if p.returncode != 0:
        raise SystemExit("push failed")
    print("=== PA7 RECON ===", sha)
    git("worktree", "remove", "--force", str(wt))


if __name__ == "__main__":
    main()
