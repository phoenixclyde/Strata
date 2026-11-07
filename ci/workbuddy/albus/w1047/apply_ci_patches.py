"""Apply W1047 CI/coverage patches to the remote source tree and commit."""
import io
import pathlib
import shutil
import subprocess
import tarfile

R = pathlib.Path("/home/albus/strata166/pr/k10")
TAR = pathlib.Path("/home/albus/strata166/tmp/w1047/workbuddy_ci_bundle.tar.gz")
BR = "ci/w1047-coverage"
BASE = "origin/ci/w1046-hooks"


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(R)] + list(args), check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()


if git("status", "--porcelain"):
    raise SystemExit("source tree dirty; refusing")
git("fetch", "origin", "--prune")
git("checkout", "-B", BR, BASE)
if TAR.is_file():
    with tarfile.open(TAR, "r:gz") as tar:
        tar.extractall(R)
    print("bundle extracted")
else:
    print("WARNING: no bundle tar; patches only")

# WorkBuddy self-test runner must sit at the bundle root.
src = R / "ci/workbuddy/albus/w1047/workbuddy_selftest.py"
syn = R / "ci/workbuddy/albus/w1047/workbuddy_syntax.py"
if src.is_file():
    shutil.copy2(src, R / "ci/workbuddy/workbuddy_selftest.py")
if syn.is_file():
    shutil.copy2(syn, R / "ci/workbuddy/workbuddy_syntax.py")

# 1) round_gate --status must resolve hooks through git, not .git/hooks.
p = R / "ci/round_gate.py"
s = p.read_text(encoding="utf-8")
old = '''    for hook_name in ("pre-commit", "pre-push"):
        hook = ROOT / ".git" / "hooks" / hook_name
        if not hook.is_file():'''
new = '''    hooks_resolved = run(["git", "rev-parse", "--git-path", "hooks"], cwd=ROOT)
    hook_dir = pathlib.Path(hooks_resolved.stdout.strip() or ".git/hooks")
    if not hook_dir.is_absolute():
        hook_dir = ROOT / hook_dir
    for hook_name in ("pre-commit", "pre-push"):
        hook = hook_dir / hook_name
        if not hook.is_file():'''
if old not in s:
    raise SystemExit("round_gate hook anchor not found")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8", newline="\n")

# 2) Workflow: all branches, local-workbuddy paths, syntax + self-tests.
p = R / ".github/workflows/downstream-gate.yml"
s = p.read_text(encoding="utf-8")
s = s.replace("    branches: [main, gfx906/mi50, 'ci/**']", "    branches: ['**']", 1)
s = s.replace("    branches: [main]\n    paths:\n      - 'src/**'",
              "    branches: [main, 'gfx906/**', 'ci/**']\n    paths:\n      - 'src/**'", 1)
old_paths = """      - 'src/**'
      - 'include/**'
      - 'CMakeLists.txt'
      - 'ci/**'
      - '.github/workflows/downstream-gate.yml'"""
new_paths = """      - 'src/**'
      - 'include/**'
      - 'CMakeLists.txt'
      - 'ci/**'
      - 'tools/**'
      - 'deploy/params/**'
      - 'albus/**'
      - 'waves/**'
      - '.github/workflows/downstream-gate.yml'"""
if old_paths not in s:
    raise SystemExit("workflow paths anchor not found")
s = s.replace(old_paths, new_paths, 1)
old_run = '''          for f in ci/*.sh ci/strata-ci ci/repack_ab/*.sh; do bash -n "$f" && echo "ok   $f"; done
          python3 -m py_compile ci/*.py ci/repack_ab/*.py && echo "ok   ci/*.py + ci/repack_ab/*.py"'''
new_run = '''          for f in ci/*.sh ci/strata-ci ci/repack_ab/*.sh; do bash -n "$f" && echo "ok   $f"; done
          python3 -m py_compile ci/*.py ci/repack_ab/*.py && echo "ok   ci/*.py + ci/repack_ab/*.py"
          python3 ci/workbuddy_syntax.py
          python3 ci/workbuddy_selftest.py'''
if old_run not in s:
    raise SystemExit("workflow syntax anchor not found")
s = s.replace(old_run, new_run, 1)
p.write_text(s, encoding="utf-8", newline="\n")

# 3) README: state the corrected topology and provenance bridge.
p = R / "ci/README.md"
s = p.read_text(encoding="utf-8")
s = s.rstrip("\n") + """

## W1047 (2026-11-07): full coverage and retrospective provenance

Corrections to earlier rounds are recorded in `ci/provenance/HISTORY_CORRECTIONS.md`.
The active WorkBuddy script/patch surface is no longer local-only: it is mirrored
under `ci/workbuddy/**`, syntax-checked and self-tested by this workflow. Every
auditable workspace file also has a SHA-256 row in
`ci/provenance/workspace_manifest.tsv`; historical source snapshots are not
copied wholesale into the engine repository, but they cannot disappear silently.

The workflow is still static-only. It now covers **all push branches** and the
local gate/tool paths, but it does not compile ROCm or run GPU benchmarks.
"""
p.write_text(s, encoding="utf-8", newline="\n")

# 4) Syntax/self-tests before commit.
r = subprocess.run([ "python3", str(R / "ci/workbuddy_syntax.py")], text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(r.stdout[-4000:])
if r.returncode != 0:
    raise SystemExit("workbuddy syntax failed")
r = subprocess.run(["python3", str(R / "ci/workbuddy_selftest.py")], text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(r.stdout[-5000:])
if r.returncode != 0:
    raise SystemExit("workbuddy self-tests failed")
r = subprocess.run(["python3", str(R / "ci/round_gate.py"), "--ci"], text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(r.stdout[-5000:])
if r.returncode != 0:
    raise SystemExit("round gate failed")

git("add", "-A")
git("commit", "-m", "ci(W1047): full local-tool coverage, worktree-safe hooks, provenance manifest")
print("branch", BR, "commit", git("rev-parse", "--short", "HEAD"))
print(git("show", "--stat", "--oneline", "HEAD"))
