#!/usr/bin/env python3
# W1048: retro-CI coverage. Tier A pushes one branch per uncovered historical sha;
# Tier B reconstructs the three uncommitted candidate trees from their patch scripts
# and commits them, so every change that produced an artifact is CI-able.
# Touches only refs/heads/ci/retro/* and throwaway worktrees; never the checkout.
import pathlib
import shutil
import subprocess
import sys

R = "/home/albus/strata166/pr/k10"
TMP = pathlib.Path("/home/albus/strata166/tmp/w1048")
TMP.mkdir(parents=True, exist_ok=True)
LOCAL = pathlib.Path("/home/albus/strata166/tmp/w1048/push")  # scripts arrive here


def git(*a, cwd=R):
    r = subprocess.run(["git", "-C", cwd] + list(a), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print("git", " ".join(a)[:90], "->", r.returncode)
    if r.returncode != 0:
        print(r.stdout[-1200:])
    return r


# ---- Tier A: per-sha retro branches -------------------------------------
TIER_A = [
    ("fa8e6761842179d56085b06db4b31776aa0e354b", "ci/retro/fa8e6761-k10-pin"),
    ("79516b21ca5d747045e6c5dc00e0a1bd6c9c0a29", "ci/retro/79516b21-pa0"),
    ("8b44f3d1097b74c731b733dd60c0a15aeb15e494", "ci/retro/8b44f3d1-pa1"),
    ("806a4b2f6", "ci/retro/806a4b2f-tqfix"),
    ("3b935ddfc", "ci/retro/3b935ddf-pa2land"),
    ("8b5e547fa64fad8a67861731e6aa33f0bff5055d", "ci/retro/8b5e547f-pa3"),
    ("62d10e25cfb094ce4c2092aaae4d5f01cc6168b4", "ci/retro/62d10e25-pa5"),
    ("91a7c5a4e284f71b44316927131248362802d0ef", "ci/retro/91a7c5a4-pa6pa7"),
    ("064aa6c04", "ci/retro/064aa6c0-hc-first"),
]

# ---- Tier B: reconstructed uncommitted trees ---------------------------
# (name, base sha, patch script on 166, patched file)
TIER_B = [
    ("pa2-recon", "8b44f3d1097b74c731b733dd60c0a15aeb15e494",
     "wire_opt_prefill.py", "src/kernels/cuda/qsa_decode_attn.cu"),
    ("pa4-recon", "8b5e547fa64fad8a67861731e6aa33f0bff5055d",
     "pa4_patch.py", "src/kernels/cuda/qsa_decode_attn.cu"),
    ("pa7-recon", "62d10e25cfb094ce4c2092aaae4d5f01cc6168b4",
     "pa7_patch.py", "src/kernels/cuda/qsa_decode_attn.cu"),
]


def main():
    # sanity: all Tier A shas exist and carry the workflow file
    for sha, ref in TIER_A:
        c = git("cat-file", "-e", sha + "^{commit}")
        if c.returncode != 0:
            raise SystemExit("missing sha " + sha)
        t = git("ls-tree", "-r", "--name-only", sha)
        if "workflows/downstream-gate.yml" not in t.stdout:
            raise SystemExit("no workflow at " + sha)

    # one push, many refspecs -> a single pre-push gate run
    refspecs = ["%s:refs/heads/%s" % (sha, ref) for sha, ref in TIER_A]
    p = git("push", "origin", *refspecs)
    if p.returncode != 0:
        raise SystemExit("tier A push failed")

    results = [(ref.split("/")[-1], git("rev-parse", sha).stdout.strip()) for sha, ref in TIER_A]

    for name, base, patch, target in TIER_B:
        wt = TMP / ("wt-" + name)
        if wt.exists():
            shutil.rmtree(wt)
        c = git("worktree", "add", "--detach", str(wt), base)
        if c.returncode != 0:
            raise SystemExit("worktree add failed " + name)
        # rewrite the patch script's hardcoded tree path to this worktree
        src = LOCAL / patch
        txt = src.read_text(encoding="utf-8", errors="replace")
        txt = txt.replace("/home/albus/strata166/pr/port-all", str(wt))
        adj = TMP / ("adj_" + patch)
        adj.write_text(txt, encoding="utf-8", newline="\n")
        r = subprocess.run([sys.executable, str(adj)], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print("patch", name, "->", r.returncode)
        print(r.stdout[-800:])
        if r.returncode != 0:
            raise SystemExit("patch failed " + name)
        st = git("status", "--porcelain", cwd=str(wt))
        if not st.stdout.strip():
            raise SystemExit("patch changed nothing " + name)
        git("add", "-A", cwd=str(wt))
        msg = ("[retro W1048] reconstruct %s on %s from %s\n\n"
               "Historical candidate binary was built from an UNCOMMITTED work tree.\n"
               "This commit replays the exact patch script (%s) on the recorded base so\n"
               "the change is versioned and CI-able.  Evidence grade B: tree may differ\n"
               "from the build tree in unrelated worktree drift; the patch itself is exact.\n"
               % (name, base[:8], patch, patch))
        c = git("-c", "user.name=albus", "-c", "user.email=albus@localhost",
                "commit", "-m", msg, cwd=str(wt))
        if c.returncode != 0:
            raise SystemExit("commit failed " + name)
        sha = git("rev-parse", "HEAD", cwd=str(wt)).stdout.strip()
        branch = "ci/retro/" + name
        p = git("push", "origin", "HEAD:refs/heads/" + branch, cwd=str(wt))
        if p.returncode != 0:
            raise SystemExit("push failed " + name)
        results.append((branch.split("/")[-1], sha))
        git("worktree", "remove", "--force", str(wt))

    print("=== RETRO REFS ===")
    for name, sha in results:
        print(name, sha)


if __name__ == "__main__":
    main()
