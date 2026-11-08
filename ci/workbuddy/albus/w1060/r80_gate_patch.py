#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1060/R80: add the three provenance checks to ci/gate.py (both identical copies).
#   1) config exe md5 == last deploy-ledger exe_md5
#   2) that md5 == build/strata md5
#   3) last ledger tag != "-" and equals the repo HEAD's tag
# Fail-closed: any mismatch or missing input is FAIL. Append-only edit to gate.py.
import hashlib
import io
import re
import shutil

PATHS = [
    "/home/albus/strata166/pr/strata-fork/ci/gate.py",
    "/home/albus/strata166/pr/k10/ci/gate.py",
]

FN = '''

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
    hdr = lines[0].split("\\t")
    try:
        i_exe, i_md5, i_tag = hdr.index("exe"), hdr.index("exe_md5"), hdr.index("tag")
    except ValueError as e:
        add(FAIL, "prov/ledger-cols", "missing column: %s" % e)
        return
    last = lines[-1].split("\\t")
    l_exe, l_md5, l_tag = last[i_exe], last[i_md5], last[i_tag]

    # --- 1) config exe md5 == ledger exe_md5
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8-sig"))
        exe = cfg.get("exe") or cfg.get("engine")
        exe_host = exe.replace("/data/bin/", "/home/albus/strata166/data/bin/") if exe else ""
        cfg_md5 = md5_file(exe_host)
    except Exception as e:
        add(FAIL, "prov/1 config-exe==ledger", "cannot md5 config exe: %s" % e)
        cfg_md5 = None
    if cfg_md5 is not None:
        if cfg_md5 == l_md5:
            add(PASS, "prov/1 config-exe==ledger", "exe=%s md5=%s == ledger-last %s" % (exe, cfg_md5[:12], l_exe))
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
            add(PASS, "prov/2 exe==build/strata", "build md5 %s == config exe md5" % b_md5[:12])
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
        add(PASS, "prov/3 tag==HEAD", "ledger tag %s == HEAD tag(s) %s" % (l_tag, head_tags))
    else:
        add(FAIL, "prov/3 tag==HEAD", "ledger tag %s not in HEAD tags %s" % (l_tag, head_tags))

'''

CALL = '''    check_source(a.repo)
    if not a.source_only:
        check_build(a.build)
        if a.config:
            check_prod(a.config, None, a.health)
            check_provenance(a.config, os.path.join(a.build, "strata"),
                             os.environ.get("DEPLOY_LEDGER",
                                            "/home/albus/strata166/ci/state/prod_history.tsv"),
                             a.repo)
'''
OLD_CALL = '''    check_source(a.repo)
    if not a.source_only:
        check_build(a.build)
        if a.config:
            check_prod(a.config, None, a.health)
'''

for P in PATHS:
    s = io.open(P, encoding="utf-8").read()
    assert "check_provenance" not in s, P
    assert s.count(OLD_CALL) == 1, (P, s.count(OLD_CALL))
    s = s.replace(OLD_CALL, CALL, 1)
    # imports
    if "import hashlib" not in s:
        s = s.replace("import argparse", "import argparse\nimport hashlib", 1)
    if "import json" not in s:
        s = s.replace("import argparse", "import argparse\nimport json", 1)
    if "import subprocess" not in s:
        s = s.replace("import argparse", "import argparse\nimport subprocess", 1)
    # insert the function before def main
    s = s.replace("\ndef main():", FN + "\ndef main():", 1)
    shutil.copy2(P, P + ".bak-w1060")
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("PATCHED", P, "prov_fn=", s.count("def check_provenance"))
