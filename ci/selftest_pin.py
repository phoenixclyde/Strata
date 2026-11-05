#!/usr/bin/env python3
"""Negative tests for the fifth pointer, without touching the live repo or image.

Each case builds a throwaway "repo" whose only relevant content is .github/workflows,
a build dir with _ci_all.txt, and a mi50-* tag (so the *other* four pointers stay green
and a red result can only come from the pin check).
"""
import io, os, shutil, subprocess, sys, tempfile

RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"
SHA = "3cf03257f219afbe7334045ff7c6a06ac68c627d"
VER = '0.1.57'


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def fixture(tmp, pin, refs):
    os.makedirs(os.path.join(tmp, ".github", "workflows"), exist_ok=True)
    io.open(os.path.join(tmp, ".github", "workflows", "metal-build.yml"), "w",
            encoding="utf-8").write("env:\n  LLAMA_CPP_COMMIT: %s\n" % pin if pin else "env: {}\n")
    # the version define must be present regardless of refs, otherwise case 4 fails for the
    # wrong reason (missing define) instead of the one it is testing (no llama.cpp at all)
    lines = ['-DSTRATA_VERSION=\\"%s\\" /opt/rocm/llvm/bin/clang++ -c x.cu' % VER]
    lines += ['/llama.cpp/ggml/src/f%d.cu' % i for i in range(refs)]
    io.open(os.path.join(tmp, "_ci_all.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    sh("git", "-C", tmp, "init", "-q")
    sh("git", "-C", tmp, "add", "-A")
    sh("git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
    sh("git", "-C", tmp, "tag", "mi50-selftest")


def run(tmp):
    r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp)
    return r.returncode, r.stdout + r.stderr


def case(name, pin, refs, want_fail):
    tmp = tempfile.mkdtemp()
    try:
        fixture(tmp, pin, refs)
        rc, out = run(tmp)
        bad = [l.strip() for l in out.splitlines() if "FAIL" in l]
        ok = (rc != 0) == want_fail
        print("  [%s] %-44s rc=%d %s" % ("ok " if ok else "BAD", name, rc,
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
n += case("baseline: correct pin, 93 refs", SHA, 93, False)
n += case("wrong upstream pin (all f)", "f" * 40, 93, True)
n += case("no upstream pin at all", "", 93, True)
n += case("engine built from no llama.cpp", SHA, 0, True)
print("SELFTEST: %d/4" % n)
sys.exit(0 if n == 4 else 1)
