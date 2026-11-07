#!/bin/bash
# W1040: what does the OPT=2 (dp4a) instantiation actually compile to?
set -u
S=/home/albus/strata166
B=$S/build-pa3
IMG=strata-gfx906:0.2.11-101
OUT=$S/tmp/w1040
mkdir -p "$OUT"

# 1. pull the exact compile line ninja uses for this TU
grep -n "qsa_decode_attn" "$B/build.ninja" | grep -m1 "c++" > "$OUT/ninja_line.txt" || true
head -c 400 "$OUT/ninja_line.txt"

cat > "$OUT/isa.sh" <<'EOS'
set -u
cd /out
line=$(grep -m1 "qsa_decode_attn.cu.o" build.ninja | head -1)
# take the rule's FLAGS/INCLUDES/DEFINES from the build statement
python3 - <<'PY'
import re, subprocess, io, os
txt = io.open("/out/build.ninja", encoding="utf-8", errors="replace").read()
# find the build edge for qsa_decode_attn
m = re.search(r"build [^\n]*qsa_decode_attn[^\n]*\n((?:  [^\n]*\n)+)", txt)
if not m:
    print("NO EDGE"); raise SystemExit(1)
edge = m.group(0)
# collect the rule name
rule = re.search(r"^build [^\n]*: (\S+)", edge, re.M).group(1)
rules = re.search(r"^rule %s\n((?:  [^\n]*\n)+)" % re.escape(rule), txt, re.M)
if not rules:
    print("NO RULE"); raise SystemExit(1)
body = rules.group(1)
def var(name, src):
    mm = re.search(r"^  %s = (.*)$" % name, src, re.M)
    return mm.group(1) if mm else ""
def expand(s):
    for _ in range(6):
        s = re.sub(r"\$\{(\w+)\}", lambda m: var(m.group(1), body) or var(m.group(1), edge), s)
    return s
cmd = expand(var("command", body))
vars_edge = dict(re.findall(r"^  (\w+) = (.*)$", edge, re.M))
for k, v in vars_edge.items():
    cmd = cmd.replace("$" + k, v).replace("${%s}" % k, v)
for k in ("FLAGS", "INCLUDES", "DEFINES"):
    pass
cmd = cmd.replace("$in", "src/kernels/cuda/qsa_decode_attn.cu").replace("$out", "/tmp/qda.o")
cmd = cmd.replace(" -c ", " -S -o /tmp/qda.s ")
cmd = cmd.replace("-o /tmp/qda.o", "-o /tmp/qda.s")
print("CMD:", cmd[:400])
r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("RC", r.returncode, r.stderr[-800:])
PY
EOS

cp "$OUT/isa.sh" "$S/tmp/w1040/isa.sh"
docker run --rm -v "$S/pr/port-all":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp \
  -v "$OUT":/w -w /out "$IMG" bash /w/isa.sh 2>&1 | tail -8

echo "=== counts ==="
docker run --rm -v "$OUT":/w "$IMG" sh -c 'ls -l /tmp/qda.s 2>/dev/null; for p in v_dot4_i32_i8 v_fma_f32 v_cvt_f32_i32 v_rcp_iflag_f32 v_mul_f32 v_max_f32 v_ds_bpermute ds_write; do printf "%-18s %s\n" $p $(grep -c "$p" /tmp/qda.s 2>/dev/null); done' 2>&1 | tail -12
