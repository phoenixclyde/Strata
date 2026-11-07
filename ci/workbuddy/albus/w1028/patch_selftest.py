import io
p = "/home/albus/strata166/pr/strata-fork/ci/selftest_pin.py"
s = io.open(p, encoding="utf-8").read()

old = '''def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)
'''
new = '''# Git exports GIT_DIR (plus the quarantine variables) to hooks, and `git -C <dir>` does NOT
# override them.  Run from a hook, this fixture's `git init` therefore re-initialised *that*
# repository instead of the temp dir -- it set core.bare = true on the real worktree (W1028,
# found after the first gate push) and every later `git -C $tmp describe --tags` answered
# "No names found", which read as "the pin check is broken".  Strip the environment.
GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
           "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_QUARANTINE_PATH", "GIT_COMMON_DIR")


def sh(*a, **kw):
    kw.setdefault("env", {k: v for k, v in os.environ.items() if k not in GIT_ENV})
    return subprocess.run(a, capture_output=True, text=True, **kw)
'''
assert old in s, "sh anchor"
s = s.replace(old, new, 1)

old2 = '''    sh("git", "-C", tmp, "tag", "mi50-selftest")
'''
new2 = '''    sh("git", "-C", tmp, "tag", "mi50-selftest")
    # Loud check: if the fixture ever writes into some other repository again, fail here instead
    # of reporting a pin failure for a reason that has nothing to do with the pin.
    probe = sh("git", "-C", tmp, "rev-parse", "--is-inside-work-tree")
    if probe.stdout.strip() != "true":
        raise SystemExit("fixture: %s is not a work tree (%s)"
                         % (tmp, (probe.stdout + probe.stderr).strip()))
'''
assert old2 in s, "tag anchor"
s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("selftest_pin patched")
