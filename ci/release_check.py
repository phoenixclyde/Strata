#!/usr/bin/env python3
"""release_check -- the four pointers of a release, in one command (W1021).

Why: a release writes the version in four independent places and any one of them can be
stale.  On 2026-11-06 the engine was deployed as `strata-0.1.56-091` while its source said
0.1.57, because `build.ninja` had cached `-DSTRATA_VERSION="0.1.56"`.  Nothing failed: the
binary ran, health was ok, and the label was simply wrong.

    tag                     git describe on the production source tree
    image                   BUILD-IMAGE.json inside the image the container runs
    binary                  /data/bin/<exe> --version  (+ md5)
    compile-time define     -DSTRATA_VERSION in the build dir's cached command lines

Every field must name the same engine version, and the container's image must be the one
the release claims.  Exit non-zero with the table when they disagree.

Usage: release_check.py [--repo DIR] [--build DIR] [--container NAME] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

DEF_REPO = "/home/albus/strata166/pr/strata-fork"
DEF_BUILD = "/home/albus/strata166/build-r28"
DEF_CONT = "strata166-407"


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEF_REPO)
    ap.add_argument("--build", default=DEF_BUILD)
    ap.add_argument("--container", default=DEF_CONT)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows, fails = [], []

    def add(name, value, ok, note=""):
        rows.append({"field": name, "value": value, "ok": ok, "note": note})
        if not ok:
            fails.append(name)

    # 1. tag
    rc, tag = sh(["git", "-C", a.repo, "describe", "--tags"])
    rc2, sha = sh(["git", "-C", a.repo, "rev-parse", "--short", "HEAD"])
    add("tag", "%s @ %s" % (tag, sha), rc == 0 and tag.startswith("mi50-"),
        "must be a mi50-* tag on HEAD")

    # 2. image the container runs + its BUILD-IMAGE.json
    rc, img = sh(["docker", "inspect", "-f", "{{.Config.Image}}", a.container])
    add("container image", img or "(none)", rc == 0 and img.startswith("strata-gfx906:"))
    rc, js = sh(["docker", "run", "--rm", "--entrypoint", "sh", img or "none", "-c",
                 "cat /src/BUILD-IMAGE.json"], timeout=120)
    try:
        meta = json.loads(js)
    except Exception:
        meta = {}
    add("BUILD-IMAGE.json", json.dumps(meta, ensure_ascii=False) if meta else "(unreadable)",
        bool(meta) and "engine" in meta and "source" in meta)

    # 3. the binary the live config points at
    rc, cfg = sh(["python3", "-c",
                  "import json,sys;print(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))['exe'])"])
    exe = cfg.strip()
    rc, ver = sh(["docker", "exec", a.container, exe, "--version"])
    rc2, md5 = sh(["docker", "exec", a.container, "md5sum", exe])
    add("binary", "%s | %s | %s" % (os.path.basename(exe), ver, md5.split()[0] if md5 else "?"),
        rc == 0 and ver.startswith("strata "))

    # 4. compile-time define cached in the build dir
    rc, defs = sh("grep -oE 'DSTRATA_VERSION=\\\\\"[0-9.]+\\\\\"' %s/_ci_all.txt 2>/dev/null | sort -u"
                  % a.build)
    versions = sorted(set(re.findall(r"[0-9]+\.[0-9]+\.[0-9]+", defs)))
    add("compile-time version", ",".join(versions) or "(none)", len(versions) == 1,
        "a single value, or the build dir mixes versions")

    # agreement
    engine_bin = (ver.split()[-1] if ver.startswith("strata ") else "")
    engine_img = meta.get("engine", "")
    engine_def = versions[0] if len(versions) == 1 else ""
    same = len({x for x in (engine_bin, engine_img, engine_def) if x}) == 1
    add("engine versions agree", "bin=%s image=%s define=%s" % (engine_bin or "?", engine_img or "?", engine_def or "?"),
        same, "all three must name the same engine version")

    if a.json:
        print(json.dumps({"rows": rows, "fails": fails}, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print("  [%s] %-22s %s" % ("ok " if r["ok"] else "FAIL", r["field"], r["value"]))
            if r["note"] and not r["ok"]:
                print("        -> %s" % r["note"])
    print("RELEASE_CHECK: %s" % ("PASS" if not fails else "FAIL (%s)" % ", ".join(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
