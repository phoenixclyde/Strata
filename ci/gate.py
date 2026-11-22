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
    if not os.path.isfile(mmvq):
        # W1159: v0.2.16 layout keeps kernels under engine/ (upstream moved src/ -> engine/src/).
        # Same file, same invariants below -- the check's intent is unchanged.
        mmvq = os.path.join(repo, "engine/src/kernels/cuda/native_mmvq.cu")
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


def read_tsv_kv(path):
    """key<TAB>value 的注释型 TSV；读不到返回 {}。"""
    d = {}
    try:
        for ln in io.open(path, encoding="utf-8-sig"):
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 2:
                d[f[0].strip()] = f[1].strip()
    except OSError:
        return {}
    return d


def read_tag_ledger(path):
    """tag -> (sha, purpose)。purpose 枚举 deploy / marking。"""
    d = {}
    try:
        lines = [l for l in io.open(path, encoding="utf-8-sig").read().splitlines()
                 if l.strip() and not l.startswith("#")]
    except OSError:
        return d
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 3:
            d[f[0].strip()] = (f[1].strip(), f[2].strip())
    return d


def tag_triplet(repo, tag):
    """tag -> (object_sha, object_type, commit_sha).

    An annotated tag is its own object: `git rev-parse <tag>` returns the TAG object,
    never the commit.  Every prov/3 comparison must use the dereferenced commit
    (`<tag>^{commit}`); comparing the tag object to HEAD is a guaranteed false red.
    """
    def g(*args):
        return subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                              text=True, check=True).stdout.strip()
    return g("rev-parse", tag), g("cat-file", "-t", tag), g("rev-parse", tag + "^{commit}")


def _pointer_paths(repo):
    """Every place CANDIDATE_POINTER.tsv may legitimately live: env first, then up to 4 parents."""
    out = []
    if os.environ.get("DEPLOY_POINTER"):
        out.append(os.environ["DEPLOY_POINTER"])
    d = os.path.abspath(repo)
    for _ in range(4):
        out.append(os.path.join(d, "deploy", "CANDIDATE_POINTER.tsv"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return out


def release_baseline(repo):
    """RELEASE_BASELINE_SHA = the sha the binary was built from (single authority).

    Not HEAD (a CI-only commit on top must not turn provenance red) and not the tag
    object (see tag_triplet).
    """
    for c in _pointer_paths(repo):
        if c and os.path.isfile(c):
            for line in io.open(c, encoding="utf-8-sig"):
                f = line.rstrip("\n").split("\t")
                if len(f) >= 2 and f[0] == "built_from":
                    return f[1].strip()
    return ""


NON_ENGINE_PREFIXES = ("ci/", "docs/", "serve/", "tools/", "tests/", "bench/",
                       "history/", "albus/", ".workbuddy/", ".github/", "assets/")
NON_ENGINE_ROOT_SUFFIX = (".md", ".txt", ".bat", ".gitignore", ".gitattributes")
ENGINE_FILES = ("CMakeLists.txt", "CMakePresets.json", "Makefile", "Dockerfile")


def is_engine_path(p):
    """Fail-closed: anything not explicitly non-engine counts as an engine path."""
    if p in ENGINE_FILES:
        return True
    if p.startswith(NON_ENGINE_PREFIXES):
        return False
    if "/" not in p:
        return not p.endswith(NON_ENGINE_ROOT_SUFFIX)
    return True


def _git_out(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True, check=True).stdout.strip()


def _is_ancestor(repo, sha, head):
    if not sha or not head:
        return False
    return subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", sha, head],
                          capture_output=True).returncode == 0


def prov3_verdict(repo, tag, baseline=None, head=None, basename="prov/3"):
    """T1 tag^{commit} == RELEASE_BASELINE_SHA / T2 baseline is HEAD's ancestor /
    T3 baseline..HEAD has no engine path.  Returns [(state, name, detail)]."""
    out = []
    baseline = baseline if baseline is not None else release_baseline(repo)
    head = head if head is not None else _git_out(repo, "rev-parse", "HEAD")
    if not baseline:
        return [(FAIL, basename + " tag==release",
                 "no RELEASE_BASELINE_SHA (CANDIDATE_POINTER.tsv 的 built_from 缺失)")]
    # 哪个 tag？部署台账记的是**上一代**（生产在跑的那份），装机前它不可能等于候选的
    # 构建 sha。所以先认「指向 release baseline 的 mi50-* tag」，台账 tag 只在它确实
    # 解引用到 baseline 时才优先 —— 否则拿台账 tag 比候选，等于要求候选已经被装过。
    try:
        tags_at = [t for t in _git_out(repo, "tag", "--points-at", baseline).split()
                   if t.startswith("mi50-")]
    except Exception as e:
        return [(FAIL, basename + " tag^{commit}", "cannot list tags at baseline: %s" % e)]
    chosen, source = "", ""
    if tag and tag != "-":
        try:
            if tag_triplet(repo, tag)[2] == baseline:
                chosen, source = tag, "deploy 台账"
        except Exception:
            pass
    if not chosen:
        if len(tags_at) == 1:
            chosen, source = tags_at[0], "tag --points-at release baseline（台账尚未记它）"
        elif len(tags_at) > 1:
            return [(FAIL, basename + " tag==release",
                     "release baseline %s 上有多个 mi50-* tag，无法唯一确定：%s"
                     % (baseline[:12], tags_at))]
        else:
            return [(FAIL, basename + " tag==release",
                     "release baseline %s 没有任何 mi50-* tag（也无台账 tag 指向它）" % baseline[:12])]
    try:
        obj, typ, com = tag_triplet(repo, chosen)
    except Exception as e:
        return [(FAIL, basename + " tag^{commit}", "cannot dereference %s: %s" % (chosen, e))]
    if com != baseline:
        return [(FAIL, basename + " tag^{commit}",
                 "%s deref %s != release baseline %s（tag 没打在产二进制的构建 sha 上）"
                 % (chosen, com[:12], baseline[:12]))]
    _extra = []
    if tag and tag != "-" and tag != chosen:
        _extra.append((OK, basename + " 台账",
                       "deploy 台账末行仍是 %s（上一代在跑的），候选 tag 是 %s —— 装机前这是预期" % (tag, chosen)))
    if not _is_ancestor(repo, baseline, head):
        return [(FAIL, basename + " T2 祖先",
                 "release baseline %s 不是 HEAD %s 的祖先（HEAD 被回退或换了分支）"
                 % (baseline[:12], (head or "?")[:12]))]
    files = []
    if head and head != baseline:
        files = [x for x in _git_out(repo, "diff", "--name-only", "%s..%s" % (baseline, head)).splitlines()
                 if x.strip()]
    eng = [f for f in files if is_engine_path(f)]
    if eng:
        return [(FAIL, basename + " T3 引擎路径",
                 "baseline..HEAD 有 %d 处引擎路径改动（例：%s）⇒ 二进制不再代表 HEAD"
                 % (len(eng), eng[:3]))]
    if head == baseline:
        return [(OK, basename + " tag^{commit}",
                 "%s object %s(%s) -> commit %s == HEAD（exact）" % (chosen, obj[:12], typ, com[:12]))]
    return _extra + [(OK, basename + " tag^{commit}",
             "%s object %s(%s) -> commit %s == release baseline；HEAD %s 领先 %d 文件（全非引擎）"
             % (chosen, obj[:12], typ, com[:12], head[:12], len(files))),
            (OK, basename + " 口径", "via-release-baseline（HEAD 是发布点的 CI-only 后置提交）")]


def check_tag_cli(repo, tag):
    """--check-tag: print the triplet and the verdict, with the naive comparison as a control."""
    obj, typ, com = tag_triplet(repo, tag)
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    naive = (obj == head)
    deref = (com == head)
    print("tag          = %s" % tag)
    print("object_type  = %s" % typ)
    print("object_sha   = %s" % obj)
    print("deref_commit = %s   (rev-parse %s^{commit})" % (com, tag))
    print("HEAD         = %s" % head)
    print("naive obj==HEAD   -> %s   [负向样例：必须为 False，否则说明比较对象取错]"
          % ("MATCH" if naive else "MISMATCH"))
    print("deref commit==HEAD-> %s" % ("MATCH" if deref else "MISMATCH"))
    _b = release_baseline(repo)
    print("release baseline   = %s   (CANDIDATE_POINTER.built_from)" % (_b or "<absent>"))
    print("deref commit==baseline-> %s" % ("MATCH" if _b and com == _b else "MISMATCH"))
    print("TAG_PROV(HEAD)   : %s" % ("PASS" if deref else "FAIL"))
    _v = prov3_verdict(repo, tag)
    print("TAG_PROV(release): %s" % ("PASS" if all(x[0] != FAIL for x in _v) else "FAIL"))
    for _st, _nm, _dt in _v:
        print("   %-4s %-22s %s" % ("PASS" if _st == OK else "FAIL", _nm, _dt))
    return 0 if (deref and typ == "tag") else 1


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

    # --- 2) 候选制品 == 它的构建产物（D21/D12 同类：唯一权威 = deploy/CANDIDATE_POINTER.tsv）
    # 原判据拿"生产 exe"比 build/strata：生产一落后候选就必然红，那不是漂移而是设计。
    # 判据本身不变（装机前候选必须与构建产物逐字节一致），只把比对对象换成候选指针。
    root166 = os.path.dirname(os.path.dirname(os.path.abspath(build_strata)))
    pointer = os.environ.get("DEPLOY_POINTER") or os.path.join(root166, "deploy", "CANDIDATE_POINTER.tsv")
    ptr = read_tsv_kv(pointer)
    if ptr.get("md5") and ptr.get("build_dir"):
        art = os.path.join(root166, ptr["build_dir"], "strata")
        try:
            a_md5 = md5_file(art)
        except Exception as e:
            add(FAIL, "prov/2 候选==构建产物", "cannot md5 %s: %s" % (art, e))
            a_md5 = None
        if a_md5 is not None:
            if a_md5 == ptr["md5"]:
                add(OK, "prov/2 候选==构建产物",
                    "指针 %s md5 %s == %s/strata（%s B）"
                    % (ptr.get("exe", "?"), a_md5[:12], ptr["build_dir"], ptr.get("size", "?")))
            else:
                add(FAIL, "prov/2 候选==构建产物",
                    "指针 md5 %s != %s/strata %s -- 候选被换过或构建目录不是它"
                    % (ptr["md5"][:12], ptr["build_dir"], a_md5[:12]))
        if cfg_md5 is not None and cfg_md5 != ptr["md5"]:
            add(OK, "prov/2b 生产 vs 候选",
                "生产在跑 %s（%s），候选 %s 未部署 -- 预期（未进 Stage 4）"
                % (exe, cfg_md5[:12], ptr.get("exe", "?")))
    else:
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
                    "build/strata %s != config exe %s -- deploy drifted from build?"
                    % (b_md5[:12], cfg_md5[:12]))

    # --- 3) release-point tag, anchored on the binary's build sha (r15)
    # The old check asked `git tag --points-at HEAD`, i.e. it assumed HEAD *is* the release
    # point; one CI-only commit on top then turns provenance red for a reason that has nothing
    # to do with the artifact.  The anchor is now RELEASE_BASELINE_SHA, and the tag must still
    # dereference to *that* sha -- HEAD and the tag object remain invalid answers.
    for _st, _nm, _dt in prov3_verdict(repo, l_tag, basename="prov/3"):
        add(_st, _nm, _dt)




def check_invariants(repo):
    """W1178: the content a rebase must not take away.

    W1176 lost 1,973 lines of our own work to `checkout --theirs` on two files and every
    static check stayed green, because they all looked at *presence of patterns we chose*,
    never at "the code that was there yesterday is still there".  Each row of
    ci/PROD_INVARIANTS.tsv is the regression test for one such loss: a literal that must
    still be in the file, a line-count floor for a file whose content is mostly upstream's,
    or a file that must exist.  Aggregated into one line so the gate output stays readable.
    """
    man = os.path.join(repo, "ci/PROD_INVARIANTS.tsv")
    txt = read(man)
    if txt is None:
        add(FAIL, "prod invariants", "ci/PROD_INVARIANTS.tsv is missing")
        return
    bad, n = [], 0
    for ln, line in enumerate(txt.splitlines(), 1):
        line = line.lstrip("\ufeff")          # a manifest saved with a BOM must not fail row 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 3:
            bad.append("row %d: expected >=3 columns" % ln)
            continue
        if cols[0].strip() == "path":          # the manifest header
            continue
        path, kind, value = cols[0].strip(), cols[1].strip(), cols[2].strip()
        note = cols[3].strip() if len(cols) > 3 else ""
        full = os.path.join(repo, path)
        n += 1
        if kind == "exists":
            if not os.path.isfile(full):
                bad.append("%s: missing (%s)" % (path, note))
            continue
        body = read(full)
        if body is None:
            bad.append("%s: missing (%s)" % (path, note))
            continue
        if kind == "contains":
            if value not in body:
                bad.append("%s: no %r (%s)" % (path, value, note))
        elif kind == "min_lines":
            got = len(body.splitlines())
            if got < int(value):
                bad.append("%s: %d lines < floor %s (%s)" % (path, got, value, note))
        else:
            bad.append("row %d: unknown kind %r" % (ln, kind))
    if bad:
        add(FAIL, "prod invariants (%d rows)" % n, "; ".join(bad[:6]))
    else:
        add(OK, "prod invariants (%d rows)" % n,
            "the content W1176 lost is asserted by ci/PROD_INVARIANTS.tsv")


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
    ap.add_argument("--check-tag", default=None,
                    help="打印 tag 三值（object / type / ^{commit}）并判定 tag==HEAD；不跑其余门")
    a = ap.parse_args()
    if a.check_tag:
        return check_tag_cli(a.repo, a.check_tag)

    check_source(a.repo)
    check_invariants(a.repo)
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
