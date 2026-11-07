#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1050 R106: align gen_config with production -- fix the nine drifts at the register
# (改参唯一道: the register is the source) and harden gen_config with a negative self-test.
import io
import os
import re

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------ 1. register row fixes
P = "deploy/params/PARAM_REGISTER.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
hdr = lines[0].split("\t")
n_fix = 0
for i, ln in enumerate(lines[1:], 1):
    f = ln.split("\t")
    if len(f) < len(hdr):
        continue
    r = dict(zip(hdr, f))
    if r["id"] == "P55" and r["status"] == "ADOPTED":
        f[5] = "SUPERSEDED"
        f[10] = f[10] + "（W1050 R106：与 P110 同义重复行；value 内注释会生成垃圾 env 键，由 P110 承载 emission）"
        lines[i] = "\t".join(f); n_fix += 1
    elif r["id"] == "P56" and r["status"] == "ADOPTED":
        f[5] = "REJECTED"
        f[10] = f[10] + "（W1050 R106：对齐 P111 与 P541——生产未设 REDUCE12，W1049 证数值无辜但未采纳；停止 emission）"
        lines[i] = "\t".join(f); n_fix += 1
    elif r["id"] == "P156" and "=" in r["name"]:
        f[1] = "MEASUREMENT"
        f[2] = "STRATA_GFX906_ATTN_REDUCE12"
        f[5] = "CONFIRMED"
        f[10] = f[10] + "（W1050 R106：name 内嵌 = 与中文注释会生成垃圾 env 键，改为测量记录行，不再 emission）"
        lines[i] = "\t".join(f); n_fix += 1
    elif r["id"] == "P230" and "userland" in r["name"]:
        f[1] = "PLATFORM"
        f[10] = f[10] + "（W1050 R106：整句 name 走 ENV scope 会生成垃圾键；环境事实记录行改为 PLATFORM，不 emission）"
        lines[i] = "\t".join(f); n_fix += 1
assert n_fix == 4, n_fix

new_rows = [
    ["P543", "ENV", "STRATA_GFX906_TUNED", "1", "attention", "ADOPTED", "", "", "P224",
     "【W1050 R106 生产对齐】gfx906 配方总开关，生产 config 实设 =1（P224 的配方行 scope=MEASUREMENT 不会被 gen_config 产出，故补 ENV 声明行）。",
     "采纳（W1050）。改参唯一道对齐生产。"],
    ["P544", "ENV", "STRATA_DECODE_TIMING", "1", "attention", "ADOPTED", "", "", "P248",
     "【W1050 R106 生产对齐】decode 窗口计时，生产 config 实设 =1（P248/P255 为测量与 REFERENCE 行，不产出；补 ENV 声明行）。",
     "采纳（W1050）。观测 env，按需可关。"],
    ["P545", "ENV", "STRATA_SPEC_DEPTH", "1", "attention", "ADOPTED", "", "", "P251",
     "【W1050 R106 生产对齐】MTP 深度，生产 config 实设 =1（P251 为 MEASUREMENT 行，不产出；补 ENV 声明行）。",
     "采纳（W1050）。维持 1。"],
    ["P546", "ENV", "STRATA_PREFILL_TIMING", "1", "attention", "ADOPTED", "", "", "P216",
     "【W1050 R106 生产对齐】prefill 21 相位计时，生产 config 实设 =1（P104/P216 为测量行，不产出；补 ENV 声明行）。",
     "采纳（W1050）。观测 env，按需可关。"],
]
for r in new_rows:
    assert len(r) == len(hdr) and all("\t" not in x for x in r)
    assert not any(l.split("\t")[0] == r[0] for l in lines[1:] if l.count("\t") >= 5), r[0]
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("register fixed 4 + added 4")

# ------------------------------------------------ 2. gen_config hardening
G = "deploy/params/gen_config.py"
s = io.open(G, encoding="utf-8").read()
s = s.replace('"tokenizer": "/data/packs/huihui-ud-iq4_xs/tokenizer"',
              '"tokenizer": "/data/packs/ud-q4_k_xl/tokenizer"')
s = s.replace('"model_name": "qwen3.8-flash-next-ud-iq4_xs-abliterated"',
              '"model_name": "qwen3.8-flash-next-ud-q4_k_xl-abliterated"')

# insert validate() before rows() and call it in build(); add --self-test
anchor = "def rows():"
assert s.count(anchor) == 1
validate = '''ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CLI_NAME = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate(rs):
    """W1050 R106: bad rows must FAIL, never silently generate garbage keys.

    The W1040 drift included an ENV name containing '=' plus Chinese commentary and a
    whole-sentence Chinese name -- both would emit broken env keys.  Fail closed."""
    bad = []
    for r in rs:
        if r["status"] != "ADOPTED":
            continue
        sc, name, val = r["scope"], r["name"], r["value"]
        if sc == "ENV":
            if not ENV_NAME.match(name):
                bad.append("%s ENV name invalid: %r" % (r["id"], name))
            if any(c in val for c in ("(", "（", " ", "=")):
                bad.append("%s ENV value has comment/eq/space: %r" % (r["id"], val))
        elif sc == "CLI":
            if not (CLI_NAME.match(name) or name.startswith("--")):
                bad.append("%s CLI name invalid: %r" % (r["id"], name))
    if bad:
        raise SystemExit("REGISTER VALIDATE FAIL\\n  " + "\\n  ".join(bad))


'''
s = s.replace(anchor, validate + anchor, 1)
s = s.replace("def build():\n    args, env, sect_cfg, top_cfg, pending, adopted = [], {}, {}, {}, [], []",
              "def build():\n    validate(rows())\n    args, env, sect_cfg, top_cfg, pending, adopted = [], {}, {}, {}, [], []")
# add self-test
anchor2 = "if __name__ == '__main__':"
assert s.count(anchor2) == 1
selftest = '''def self_test():
    ok = 0
    cases = [
        ("ENV name with = and Chinese", dict(id="T1", scope="ENV", name="STRATA_X=1（注释）",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV whole-sentence name", dict(id="T2", scope="ENV", name="ROCm userland 10.1.0 + rocBLAS",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV value with comment", dict(id="T3", scope="ENV", name="STRATA_OK",
         value="1(在 k8v4 下不可达)", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV good row", dict(id="T4", scope="ENV", name="STRATA_OK2",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), True),
        ("non-ADOPTED bad name ignored", dict(id="T5", scope="ENV", name="bad=name（x）",
         value="1", family="", status="REJECTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), True),
    ]
    for label, row, want_ok in cases:
        try:
            validate([row])
            got = True
        except SystemExit:
            got = False
        good = got == want_ok
        ok += good
        print("  %-32s %s (verdict=%s)" % (label, "PASS" if good else "FAIL", got))
    print("GEN_CONFIG_SELF_TEST: %d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


'''
s = s.replace(anchor2, selftest + anchor2, 1)
s = s.replace("def main():\n    a = sys.argv[1:]",
              "def main():\n    a = sys.argv[1:]\n    if '--self-test' in a:\n        raise SystemExit(self_test())")
# ensure re import
if "\nimport re" not in s and "import io, os, sys, json, difflib, time, shutil" in s:
    s = s.replace("import io, os, sys, json, difflib, time, shutil",
                  "import io, os, re, sys, json, difflib, time, shutil")
io.open(G, "w", encoding="utf-8", newline="\n").write(s)
print("gen_config hardened")
