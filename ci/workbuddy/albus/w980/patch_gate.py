#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch ci/gate.py: add config-schema checks to check_prod."""
import io, os, sys, re

p = "/home/albus/strata166/pr/strata-fork/ci/gate.py"
src = io.open(p, encoding="utf-8").read()

FUNC = '''
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
            if tok in INTS and not re.fullmatch(r"\\d+", str(val)):
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


'''

CALL = '''    add(OK, "production config parses")

    check_config_schema(cfg)
'''

if "check_config_schema" in src:
    print("already patched")
    sys.exit(0)

anchor = "# --------------------------------------------------------------------------- prod\ndef check_prod("
if anchor not in src:
    print("ANCHOR NOT FOUND")
    sys.exit(2)

src = src.replace(anchor, FUNC + "# --------------------------------------------------------------------------- prod\ndef check_prod(", 1)

anchor2 = '''    add(OK, "production config parses")\n'''
if anchor2 not in src:
    print("ANCHOR2 NOT FOUND")
    sys.exit(2)
src = src.replace(anchor2, CALL, 1)

# cfg_path_global: keep the path reachable from the schema check without touching signatures
src = src.replace('def check_prod(cfg_path, container, health_url):\n',
                  'def check_prod(cfg_path, container, health_url):\n    cfg_path_global[0] = cfg_path\n', 1)
if "cfg_path_global" not in src.split("def check_prod")[0]:
    src = src.replace("OK, FAIL, SKIP = \"PASS\", \"FAIL\", \"SKIP\"",
                      "OK, FAIL, SKIP = \"PASS\", \"FAIL\", \"SKIP\"\ncfg_path_global = [\"\"]", 1)

io.open(p, "w", encoding="utf-8").write(src)
print("patched", p)
