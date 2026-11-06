#!/usr/bin/env python3
"""Negative tests for the fifth pointer, without touching the live repo or image.

Each case builds a throwaway "repo" whose only relevant content is .github/workflows,
third_party/ggml/VERSION.txt, a build dir with _ci_all.txt, and a mi50-* tag -- so the
other pointers stay green and a red result can only come from the pin.
"""
import io, os, shutil, subprocess, sys, tempfile

# Relative to THIS file, never the work repo: the absolute path made every CI run fail with
# rc=2 "cannot open file" (runs #42-#44, 9-11 s each), which the test then reported as
# "[BAD] baseline ... rc=2" -- a path bug wearing a pin bug clothes.
RC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "release_check.py")
SHA = "3cf03257f219afbe7334045ff7c6a06ac68c627d"
VER = "0.1.57"


# Git exports GIT_DIR (plus the quarantine variables) to hooks, and `git -C <dir>` does NOT
# override them.  Run from a hook, this fixture's `git init` therefore re-initialised *that*
# repository instead of the temp dir -- it set core.bare = true on the real worktree (W1028,
# found after the first gate push) and every later `git -C $tmp describe --tags` answered
# "No names found", which read as "the pin check is broken".  Strip the environment.
GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
           "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_QUARANTINE_PATH", "GIT_COMMON_DIR")


def sh(*a, **kw):
    kw.setdefault("env", {k: v for k, v in os.environ.items() if k not in GIT_ENV})
    return subprocess.run(a, capture_output=True, text=True, **kw)


def fixture(tmp, pin, refs, ver=SHA):
    os.makedirs(os.path.join(tmp, ".github", "workflows"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "third_party", "ggml"), exist_ok=True)
    io.open(os.path.join(tmp, ".github", "workflows", "metal-build.yml"), "w",
            encoding="utf-8").write("env:\n  LLAMA_CPP_COMMIT: %s\n" % pin if pin else "env: {}\n")
    # The release pin row reads the recipe when there is no image (--offline), so a complete
    # fixture needs one: without it every case reported "llama.cpp pin (release) (absent)" and
    # the baseline could not pass -- the same "fixture is not the real thing" shape again.
    os.makedirs(os.path.join(tmp, "ci", "docker"), exist_ok=True)
    io.open(os.path.join(tmp, "ci", "docker", "Dockerfile-selftest"), "w",
            encoding="utf-8").write("ENV LLAMA_CPP_SHA=%s\n" % SHA)
    if ver:
        # CMakeLists.txt:2078 obeys this file, so it is the first declaration
        io.open(os.path.join(tmp, "third_party", "ggml", "VERSION.txt"), "w",
                encoding="utf-8").write("%s Sun Sep 20 16:08:11 2026 +0800\n" % ver)
    # the version define must be present regardless of refs, otherwise the "no llama.cpp" case
    # would fail for the wrong reason (missing define) instead of the one it tests
    lines = ['-DSTRATA_VERSION=\\"%s\\" /opt/rocm/llvm/bin/clang++ -c x.cu' % VER]
    lines += ['/llama.cpp/ggml/src/f%d.cu' % i for i in range(refs)]
    io.open(os.path.join(tmp, "_ci_all.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    sh("git", "-C", tmp, "init", "-q")
    sh("git", "-C", tmp, "add", "-A")
    sh("git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
    sh("git", "-C", tmp, "tag", "mi50-selftest")
    # Loud check: if the fixture ever writes into some other repository again, fail here instead
    # of reporting a pin failure for a reason that has nothing to do with the pin.
    probe = sh("git", "-C", tmp, "rev-parse", "--is-inside-work-tree")
    if probe.stdout.strip() != "true":
        raise SystemExit("fixture: %s is not a work tree (%s)"
                         % (tmp, (probe.stdout + probe.stderr).strip()))


def run(tmp):
    if not os.path.isfile(RC):
        raise SystemExit("selftest_pin: release_check.py not found next to this file (%s)" % RC)
    # --offline: the fixture has no container, and a host fact is not a pin fact.
    r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp, "--offline")
    return r.returncode, r.stdout + r.stderr


def case(name, pin, refs, want_fail, ver=SHA):
    tmp = tempfile.mkdtemp()
    try:
        fixture(tmp, pin, refs, ver)
        rc, out = run(tmp)
        bad = [l.strip() for l in out.splitlines() if "FAIL" in l]
        ok = (rc != 0) == want_fail
        print("  [%s] %-46s rc=%d %s" % ("ok " if ok else "BAD", name, rc,
                                         ("| " + bad[0][:66]) if bad else ""))
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# release_check reads the live container; on a runner without a docker daemon every case
# would fail and the gate would be red for the wrong reason.  Skip loudly, not silently.
if sh("docker", "info").returncode != 0:
    print("  SKIP: no docker daemon here (the pin tests need the live image)")
    print("SELFTEST: SKIP(no docker)")
    sys.exit(0)

n = 0
n += case("baseline: both declarations agree", SHA, 93, False)
n += case("workflow pin disagrees with VERSION.txt", "f" * 40, 93, True)
n += case("no pin declared anywhere", "", 93, True, ver="")
n += case("engine built from no llama.cpp", SHA, 0, True)
print("SELFTEST: %d/4" % n)
sys.exit(0 if n == 4 else 1)
