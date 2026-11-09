#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""strata-ci gate -- the checks a commit must pass before it may be built or deployed.

Two classes of check, because they run in two places:

  source   runs anywhere (a GitHub runner, the 166 host).  These catch the "config face"
           mistakes we have actually made: a rollback switch that exists only in a
           comment, a table entry that can never be hit, a fallback that is not 1.
  build /  need the build tree or the production config; on a runner they report SKIP
  prod     instead of failing.

Exit 0 = deployable, 1 = stop.  Nothing here writes anything.

Usage:
  gate.py [--repo DIR] [--build DIR] [--config FILE] [--source-only] [--quiet]
"""
import argparse
import io
import hashlib
import json
import os
import re
import subprocess
import sys

OK, FAIL, SKIP = "PASS", "FAIL", "SKIP"
cfg_path_global = [""]
rows = []


def add(level, name, detail=""):
    rows.append((level, name, detail))


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


# --------------------------------------------------------------------------- source
def check_source(repo):
    mmvq = os.path.join(repo, "src/kernels/cuda/native_mmvq.cu")
    src = read(mmvq)
    if src is None:
        add(FAIL, "native_mmvq.cu present", mmvq)
        return
    add(OK, "native_mmvq.cu present")

    # 1. the table function must exist at all
    m = re.search(r"wave_rows_for\s*\(([^)]*)\)\s*\{", src)
    if not m:
        add(FAIL, "wave_rows_for() exists", "not found -- the R table is gone")
        return
    add(OK, "wave_rows_for() exists")

    # isolate the function body by brace matching
    start = m.end() - 1
    depth, i = 0, start
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[start:i + 1]

    # 2. the runtime switch must be a real getenv, not a comment
    #    (this exact bug shipped once: the name appeared only in a comment)
    has_getenv = bool(re.search(r'getenv\s*\(\s*"STRATA_MMVQ_WAVE_ROWS"', src))
    mentions = "STRATA_MMVQ_WAVE_ROWS" in src
    if has_getenv:
        add(OK, "STRATA_MMVQ_WAVE_ROWS has a real getenv()")
    elif mentions:
        add(FAIL, "STRATA_MMVQ_WAVE_ROWS has a real getenv()",
            "the name appears but no getenv() reads it -- the rollback switch is fake")
    else:
        add(FAIL, "STRATA_MMVQ_WAVE_ROWS has a real getenv()",
            "not mentioned at all -- there is no runtime rollback path")

    # 3. R must come from the table, never from a hardcoded literal in the function
    #    (a literal 2/4 here would silently apply to every shape).
    allowed = set(int(x) for x in os.environ.get("ALLOWED_WAVE_ROWS", "1 2 4").split())
    hard = set(int(v) for v in re.findall(r"return\s+(\d+)\s*;", body)) - {1}
    if hard:
        add(FAIL, "wave_rows_for has no hardcoded R>1", "found return %s" % sorted(hard))
    else:
        add(OK, "wave_rows_for has no hardcoded R>1")

    # 4. the table itself: every cell must be 0 (=R1) or an allowed row count,
    #    and ncols=1 must be 0 everywhere (measured: no gain there, and R=4 lost 10%).
    mtab = re.search(r"kWaveRows\[\]\s*=\s*\{(.*?)\n\};", src, re.S)
    if not mtab:
        add(FAIL, "kWaveRows[] table found", "the measured table is missing")
    else:
        entries = re.findall(r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*\{([^}]*)\}\s*\}", mtab.group(1))
        if not entries:
            add(FAIL, "kWaveRows[] entries parse", "found the array but no {n_in, n_out, {..}} rows")
        else:
            bad_cell, ncols1 = [], []
            for n_in, n_out, cells in entries:
                vals = [int(x) for x in re.findall(r"-?\d+", cells)]
                if len(vals) != 8:
                    bad_cell.append("%s->%s has %d columns" % (n_in, n_out, len(vals)))
                    continue
                bad_cell += ["%s->%s r[%d]=%d" % (n_in, n_out, i, v)
                             for i, v in enumerate(vals) if v != 0 and v not in allowed]
                ncols1.append(vals[0])
            shapes = sorted({(int(a), int(b)) for a, b, _ in entries})
            if bad_cell:
                add(FAIL, "table cells are 0 or in %s" % sorted(allowed), "; ".join(bad_cell[:4]))
            else:
                add(OK, "table cells are 0 or in %s" % sorted(allowed),
                    "%d shapes x 8 columns" % len(entries))
            if any(ncols1):
                add(FAIL, "ncols=1 stays at R=1", "found %s" % [v for v in ncols1 if v])
            else:
                add(OK, "ncols=1 stays at R=1")
            add(OK, "table covers measured shapes", ", ".join("%d->%d" % s for s in shapes[:9]))

    # 5. fail-safe: an unmatched shape must fall back to 1 row (the old behaviour).
    #    Comments are stripped first -- the real code carries a trailing comment there.
    stripped = re.sub(r"//[^\n]*", "", body)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
    if re.search(r"return\s+1\s*;\s*\}\s*$", stripped.rstrip()):
        add(OK, "unmatched shapes fall back to 1 row")
    else:
        add(FAIL, "unmatched shapes fall back to 1 row",
            "no trailing `return 1;` -- an unmeasured shape would pick an unmeasured kernel")

    # 6. the include that costs 45% if it is the wrong one
    bad_inc = re.findall(r'#include\s*[<"]((?!include/strata)[^">]*platform/hip_compat)', src)
    if bad_inc:
        add(FAIL, "hip_compat include path in source",
            "found %s -- the measured one is include/strata/platform/hip_compat" % bad_inc[0])
    else:
        add(OK, "hip_compat include path in source")

    # 6. no backup files inside the tracked tree
    junk = []
    for root, dirs, files in os.walk(os.path.join(repo, "src")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        junk += [os.path.relpath(os.path.join(root, f), repo)
                 for f in files if f.endswith((".bak", ".orig", ".rej"))]
    if junk:
        add(FAIL, "no backup files under src/", ", ".join(junk[:4]))
    else:
        add(OK, "no backup files under src/")

    # 7. the ledger that makes a rebase safe
    nz = read(os.path.join(repo, "docs/DOWNSTREAM.md"))
    if nz is None:
        add(FAIL, "docs/DOWNSTREAM.md present", "the patch ledger is missing")
    elif "v0.2.9" not in nz and "based on" not in nz.lower():
        add(FAIL, "docs/DOWNSTREAM.md anchors the upstream version",
            "no upstream version line -- a rebase would have nothing to check against")
    else:
        add(OK, "docs/DOWNSTREAM.md present and anchored")


# --------------------------------------------------------------------------- build
def check_build(build_dir):
    nb = os.path.join(build_dir, "build.ninja")
    txt = read(nb)
    if txt is None:
        add(SKIP, "build.ninja checks", "no build tree at %s" % build_dir)
        return

    # the single most expensive flag to lose: 47% slower without it
    if "-DNDEBUG" in txt:
        add(OK, "compile flags carry -DNDEBUG")
    else:
        add(FAIL, "compile flags carry -DNDEBUG", "missing -DNDEBUG costs ~47% (measured)")

    incs = re.findall(r"-I\s*(\S*hip_compat\S*)", txt)
    good = [i for i in incs if "include/strata/platform/hip_compat" in i]
    if good:
        add(OK, "hip_compat include path", good[0])
    elif incs:
        add(FAIL, "hip_compat include path",
            "found %s -- the measured one is include/strata/platform/hip_compat (-45%% else)"
            % incs[0])
    else:
        add(SKIP, "hip_compat include path", "no -I...hip_compat line found")

    bin_path = os.path.join(build_dir, "strata")
    if os.path.exists(bin_path):
        add(OK, "engine binary built", "%d bytes" % os.path.getsize(bin_path))
    else:
        add(FAIL, "engine binary built", bin_path + " missing")



# --------------------------------------------------------------------------- config schema
# The checks below exist because a hand-edited config took production down: `env` was
# rewritten as a list (json.dump of a list of keys) and the server died with
#   AttributeError: 'list' object has no attribute 'items'
# before it could bind.  Nothing in the old gate looked at the shape of the file.

VALUE_FLAGS = {
    "--pack", "--native", "--expert-profile", "--expert-cache", "--pcie-frac", "--spec",
    "--spec-min-p", "--mtp", "--mtp-window", "--max-context", "--kv", "--prefill",
    "--prompt-cache-every", "--expert-profile-save", "--conversation-cache-mib",
    "--vram-reserve-mib", "--ple-io", "--kv-resident", "--pool-workers", "--pool-tasks",
    "--host-core", "--resident-budget-gib", "--ram-keep-gib", "--adapt-swaps",
    "--peer-slots", "--peer-reserve-mib", "--peer-prefill-rows",
}
BOOL_FLAGS = {
    "--vision", "--mmap-experts", "--resident-cpu-experts", "--resident-experts",
    "--resident-pin", "--kv-grow", "--no-hit-poke", "--stream-token", "--expert-cache-per-layer",
    "--prefill-head-alias", "--prompt-cache-tail", "--prompt-cache-spread", "--remote-expert-opt",
}
ENUMS = {
    "--ple-io": {"direct", "mmap", "ram"},
    "--expert-cache": None,        # int or "auto"
    "--kv": None,                  # free-form today (fp16/int8/q4_0/k8v4/...)
}
INTS = {"--spec", "--max-context", "--prompt-cache-every", "--conversation-cache-mib",
        "--vram-reserve-mib", "--mtp-window", "--pool-workers", "--pool-tasks",
        "--kv-resident", "--adapt-swaps", "--peer-slots", "--peer-reserve-mib"}


def check_config_schema(cfg):
    env = cfg.get("env")
    if env is None:
        add(OK, "config env absent (no overrides)")
    elif isinstance(env, dict):
        bad = [k for k, v in env.items() if not isinstance(k, str) or not isinstance(v, (str, int, float))]
        if bad:
            add(FAIL, "config env is a dict of scalars", "bad entries: %r" % bad[:3])
        else:
            add(OK, "config env is a dict", "%d keys" % len(env))
    else:
        add(FAIL, "config env is a dict",
            "got %s -- the server calls cfg['env'].items() and dies before binding" % type(env).__name__)

    a = cfg.get("args")
    if not isinstance(a, list):
        add(FAIL, "config args is a list", "got %s" % type(a).__name__)
        return
    add(OK, "config args is a list", "%d entries" % len(a))

    unknown, problems, seen, i = [], [], set(), 0
    while i < len(a):
        tok = a[i]
        if not isinstance(tok, str) or not tok.startswith("--"):
            problems.append("args[%d]=%r is not a flag" % (i, tok))
            i += 1
            continue
        if tok in seen:
            problems.append("duplicate flag %s" % tok)
        seen.add(tok)
        if tok in BOOL_FLAGS:
            i += 1
            continue
        if tok in VALUE_FLAGS:
            if i + 1 >= len(a) or (isinstance(a[i + 1], str) and a[i + 1].startswith("--")):
                problems.append("%s has no value" % tok)
                i += 1
                continue
            val = a[i + 1]
            if tok in ENUMS and ENUMS[tok] and str(val) not in ENUMS[tok]:
                problems.append("%s=%r not in %s" % (tok, val, sorted(ENUMS[tok])))
            if tok in INTS and not re.fullmatch(r"\d+", str(val)):
                problems.append("%s=%r is not an integer" % (tok, val))
            i += 2
            continue
        unknown.append(tok)
        i += 1

    if problems:
        add(FAIL, "config args are well formed", "; ".join(problems[:4]))
    else:
        add(OK, "config args are well formed", "%d flags" % len(seen))
    if unknown:
        add(FAIL, "config args are known flags", "unknown: %s (add to gate.py if intentional)" % ", ".join(unknown[:4]))
    else:
        add(OK, "config args are known flags")

    bak = sorted(f for f in os.listdir(os.path.dirname(os.path.abspath(cfg_path_global[0])))
                 if f.startswith(os.path.basename(cfg_path_global[0]) + ".bak")) if cfg_path_global[0] else []
    if bak:
        add(OK, "config has a rollback copy", bak[-1])
    else:
        add(SKIP, "config has a rollback copy", "no .bak_* next to the config")


# --------------------------------------------------------------------------- prod
def check_prod(cfg_path, container, health_url):
    cfg_path_global[0] = cfg_path
    d = read(cfg_path)
    if d is None:
        add(SKIP, "production config", "no config at %s" % cfg_path)
        return
    try:
        cfg = json.loads(d)
    except json.JSONDecodeError as e:
        add(FAIL, "production config parses", str(e))
        return
    add(OK, "production config parses")

    check_config_schema(cfg)

    exe = cfg.get("exe", "")
    # the container's /data is the host's <data dir of this config>
    real = exe.replace("/data/", os.path.dirname(os.path.abspath(cfg_path)) + "/", 1)
    if os.path.exists(real):
        add(OK, "config exe points at an existing binary", exe)
    else:
        add(FAIL, "config exe points at an existing binary", "%s -> %s missing" % (exe, real))

    env = cfg.get("env")
    env = env if isinstance(env, dict) else {}
    v = env.get("STRATA_MMVQ_WAVE_ROWS")
    if v is None:
        add(OK, "wave-rows env unset (= table in use)")
    elif str(v).strip() in ("0", "1"):
        add(OK, "wave-rows env is a rollback value", str(v))
    else:
        add(FAIL, "wave-rows env is a rollback value", "got %r, expected 0/1/unset" % v)

    try:
        out = subprocess.run(["curl", "-s", "--max-time", "6", health_url],
                             capture_output=True, text=True, timeout=12).stdout
        if '"status": "ok"' in out and '"loaded": true' in out:
            add(OK, "production /health ok and loaded")
        elif out.strip():
            add(FAIL, "production /health ok and loaded", out[:120])
        else:
            add(SKIP, "production /health ok and loaded", "no answer")
    except Exception as e:                                    # noqa: BLE001
        add(SKIP, "production /health ok and loaded", str(e))


# --------------------------------------------------------------------------- main

def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_provenance(cfg_path, build_strata, ledger, repo):
    """[R80/W1060] 3 provenance checks (fail-closed):
    1) config exe md5 == ledger-last exe_md5
    2) that md5 == build/strata md5
    3) ledger-last tag != "-" and equals the repo HEAD tag"""
    # --- ledger last row
    try:
        lines = [l for l in io.open(ledger, encoding="utf-8").read().splitlines()
                 if l.strip() and not l.startswith("#")]
    except Exception as e:
        add(FAIL, "prov/ledger", "cannot read %s: %s" % (ledger, e))
        return
    hdr = lines[0].split("\t")
    try:
        i_exe, i_md5, i_tag = hdr.index("exe"), hdr.index("exe_md5"), hdr.index("tag")
    except ValueError as e:
        add(FAIL, "prov/ledger-cols", "missing column: %s" % e)
        return
    last = lines[-1].split("\t")
    l_exe, l_md5, l_tag = last[i_exe], last[i_md5], last[i_tag]

    # --- 1) config exe md5 == ledger exe_md5
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8-sig"))
        exe = cfg.get("exe") or cfg.get("engine")
        host_bin = os.environ.get("STRATA_DATA_BIN") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(repo))), "data", "bin")
        exe_host = exe.replace("/data/bin/", host_bin.rstrip("/") + "/") if exe else ""
        cfg_md5 = md5_file(exe_host)
    except Exception as e:
        add(FAIL, "prov/1 config-exe==ledger", "cannot md5 config exe: %s" % e)
        cfg_md5 = None
    if cfg_md5 is not None:
        if cfg_md5 == l_md5:
            add(OK, "prov/1 config-exe==ledger", "exe=%s md5=%s == ledger-last %s" % (exe, cfg_md5[:12], l_exe))
        else:
            add(FAIL, "prov/1 config-exe==ledger",
                "config exe md5 %s != ledger-last %s (%s) -- deploy not logged?" % (cfg_md5[:12], l_md5[:12], l_exe))

    # --- 2) that md5 == build/strata md5
    try:
        b_md5 = md5_file(build_strata)
    except Exception as e:
        add(FAIL, "prov/2 exe==build/strata", "cannot md5 %s: %s" % (build_strata, e))
        b_md5 = None
    if b_md5 is not None and cfg_md5 is not None:
        if b_md5 == cfg_md5:
            add(OK, "prov/2 exe==build/strata", "build md5 %s == config exe md5" % b_md5[:12])
        else:
            add(FAIL, "prov/2 exe==build/strata",
                "build/strata %s != config exe %s -- deploy drifted from build?" % (b_md5[:12], cfg_md5[:12]))

    # --- 3) ledger tag != "-" and equals HEAD tag
    try:
        out = subprocess.run(["git", "-C", repo, "tag", "--points-at", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.split()
        head_tags = [t for t in out if t.startswith("mi50-")]
    except Exception as e:
        add(FAIL, "prov/3 tag==HEAD", "cannot read HEAD tags: %s" % e)
        head_tags = []
    if l_tag == "-" or not l_tag:
        add(FAIL, "prov/3 tag==HEAD", "ledger-last tag is %r (unlogged deploy?)" % l_tag)
    elif not head_tags:
        add(FAIL, "prov/3 tag==HEAD", "HEAD has no mi50-* tag but ledger says %s" % l_tag)
    elif l_tag in head_tags:
        add(OK, "prov/3 tag==HEAD", "ledger tag %s == HEAD tag(s) %s" % (l_tag, head_tags))
    else:
        add(FAIL, "prov/3 tag==HEAD", "ledger tag %s not in HEAD tags %s" % (l_tag, head_tags))


def main():
    ap = argparse.ArgumentParser()
    _self = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _root166 = os.path.dirname(os.path.dirname(_self))
    ap.add_argument("--repo", default=os.environ.get("REPO", _self))
    ap.add_argument("--build", default=os.environ.get("BUILD",
                                                      os.path.join(_root166, "gfx029-build")))
    ap.add_argument("--config", default=os.environ.get("CFG", ""))
    ap.add_argument("--health", default=os.environ.get("HEALTH", "http://127.0.0.1:8090/health"))
    ap.add_argument("--source-only", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    check_source(a.repo)
    if a.source_only:
        add(OK, "prov/deploy-time-only",
            "R80 provenance runs only with --config (deploy.sh step 1); --source-only sees no production files")
    if not a.source_only:
        check_build(a.build)
        if a.config:
            check_prod(a.config, None, a.health)
            check_provenance(a.config, os.path.join(a.build, "strata"),
                             os.environ.get("DEPLOY_LEDGER",
                                            os.environ.get("DEPLOY_LEDGER",
                                                           os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                                                        "ci", "state", "prod_history.tsv"))),
                             a.repo)

    fails = [r for r in rows if r[0] == FAIL]
    if not a.quiet:
        for lvl, name, detail in rows:
            print("%-4s %-52s %s" % (lvl, name, detail))
        print()
    print("gate: %d checks, %d failed, %d skipped"
          % (len(rows), len(fails), sum(1 for r in rows if r[0] == SKIP)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
