#!/usr/bin/env python3
"""release_check -- the five pointers of a release, in one command (W1021, W1022).

Why: a release writes the version in four independent places and any one of them can be
stale.  On 2026-11-06 the engine was deployed as `strata-0.1.56-091` while its source said
0.1.57, because `build.ninja` had cached `-DSTRATA_VERSION="0.1.56"`.  Nothing failed: the
binary ran, health was ok, and the label was simply wrong.

    tag                     git describe on the production source tree
    image                   BUILD-IMAGE.json inside the image the container runs
    binary                  /data/bin/<exe> --version  (+ md5)
    compile-time define     -DSTRATA_VERSION in the build dir's cached command lines
    llama.cpp pin           upstream LLAMA_CPP_COMMIT == image's llama_cpp (40 hex) == the
                            tree actually present in the image (a tree hash, not a label)

Every field must name the same engine version, and the container's image must be the one
the release claims.  The llama.cpp pin is checked by *content*: a 7-char prefix proves
nothing, and an image can swap the vendored tree without changing any version string.  Exit non-zero with the table when they disagree.

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
    ap.add_argument("--offline", action="store_true",
                    help="skip the rows that need the live box (container, image, binary); "
                         "the tag / pin / build rows are still judged")
    a = ap.parse_args()

    rows, fails = [], []

    # Rows that can only be judged where the engine actually runs.  On a GitHub runner there is
    # no container and no /data/bin, and the run used to die on `docker inspect` with
    # "no such object: strata166-407" -- a host fact scored as a release failure.  --offline turns
    # those into SKIP, which is what a static run can honestly say about them.
    OFFLINE_ROWS = {"container image", "BUILD-IMAGE.json", "binary", "engine versions agree",
                    "llama.cpp tree (image)"}

    def add(name, value, ok, note=""):
        if a.offline and name in OFFLINE_ROWS:
            rows.append({"field": name, "value": "SKIP (needs the live box)",
                         "ok": True, "note": "not checkable on a runner"})
            return
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

    # 5. llama.cpp pin -- the dependency that decides quantisation and kernel behaviour
    # two declarations: third_party/ggml/VERSION.txt is what CMakeLists.txt:2078 obeys, the
    # workflow is a second copy.  They must agree; a disagreement is the failure, not a tie to break.
    rc, ver_txt = sh("head -1 %s/third_party/ggml/VERSION.txt 2>/dev/null" % a.repo)
    mv = re.search(r"\b[0-9a-f]{40}\b", ver_txt or "")
    pin_ver = mv.group(0) if mv else ""
    rc, wf = sh("grep -hoE 'LLAMA_CPP_COMMIT: *[0-9a-f]{40}' %s/.github/workflows/*.yml 2>/dev/null | head -1" % a.repo)
    mw = re.search(r"[0-9a-f]{40}", wf or "")
    pin_wf = mw.group(0) if mw else ""
    pin_up = pin_ver or pin_wf
    add("llama.cpp pin (upstream)", pin_ver or pin_wf or "(not declared)",
        bool(pin_up) and (not (pin_ver and pin_wf) or pin_ver == pin_wf),
        "VERSION.txt (CMakeLists.txt:2078) and the workflow pin must both exist and agree")

    pin_img = (meta.get("llama_cpp") or "").strip()
    full = bool(re.fullmatch(r"[0-9a-f]{40}", pin_img))
    add("llama.cpp pin (release)", pin_img or "(absent)",
        full and (not pin_up or pin_img == pin_up),
        "BUILD-IMAGE.json must carry the FULL 40-hex sha; a 7-char prefix cannot be verified")

    # a tree hash, because the vendored tree can be replaced without any string changing
    rc, th = sh(["docker", "exec", a.container, "sh", "-c",
                 "cd /src/third_party/llama.cpp && find . -type f -print0 | LC_ALL=C sort -z "
                 "| xargs -0 md5sum 2>/dev/null | md5sum | cut -d' ' -f1"], timeout=300)
    th_img = (meta.get("llama_cpp_tree") or "").strip()
    add("llama.cpp tree (image)", "%s claimed=%s" % (th.strip()[:12] or "?", th_img[:12] or "(absent)"),
        rc == 0 and bool(th_img) and th.strip() == th_img,
        "hash of the tree in the image must equal the one recorded at build time")

    # and the engine must have been compiled from that tree, not from a stale copy
    rc, n = sh("grep -c '/llama.cpp/' %s/_ci_all.txt 2>/dev/null" % a.build)
    n = int(re.sub(r"\D", "", n or "0") or 0)
    add("llama.cpp in engine build", "%d references to /llama.cpp/" % n, n > 0,
        "STRATA_GGML_DIR must point at the vendored tree; 0 means the engine used something else")

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
