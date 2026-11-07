#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 amdhsa YAML 元数据：每 kernel 的 vgpr/sgpr/private(溢出)/lds/wave。"""
import subprocess, base64, sys

REMOTE = "albus@192.168.50.166"

INNER_T = r'''
set +e
COB=/opt/rocm/llvm/bin/clang-offload-bundler
OC=/opt/rocm/llvm/bin/llvm-objcopy
D=/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda
f=__F__
cd /tmp; rm -f $f.fat $f.hsaco
$OC --dump-section .hip_fatbin=/tmp/$f.fat $D/$f.cu.o 2>/dev/null
[ -s /tmp/$f.fat ] || { echo "NODEV $f"; exit 0; }
ID=$($COB --list --type=o --input=/tmp/$f.fat 2>/dev/null | grep -m1 amdgcn)
[ -n "$ID" ] || { echo "NOID $f"; exit 0; }
$COB --unbundle --type=o --targets=$ID --input=/tmp/$f.fat --output=/tmp/$f.hsaco 2>/dev/null
[ -s /tmp/$f.hsaco ] || { echo "UNBUNDLEFAIL $f"; exit 0; }
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/$f.hsaco 2>/dev/null > /tmp/$f.txt
python3 - "$f" <<'PY'
import sys, re
f = sys.argv[1]
txt = open('/tmp/%s.txt' % f, encoding='utf-8', errors='replace').read()
cur = None
rows = []
for ln in txt.splitlines():
    m = re.match(r'\s*-?\s*\.name:\s*(\S+)', ln)
    if m:
        if cur: rows.append(cur)
        cur = {'name': m.group(1)}
        continue
    if cur is None: continue
    m = re.match(r'\s*\.(vgpr_count|sgpr_count|private_segment_fixed_size|group_segment_fixed_size|wavefront_size):\s*(\S+)', ln)
    if m: cur[m.group(1)] = m.group(2)
if cur: rows.append(cur)
for r in rows:
    print('%-52s vgpr=%-4s sgpr=%-4s priv=%-7s lds=%-6s wave=%-2s' % (
        r.get('name'), r.get('vgpr_count'), r.get('sgpr_count'),
        r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size'), r.get('wavefront_size')))
print('TOTAL_KERNELS %d' % len(rows))
PY
'''

def probe(name):
    inner = INNER_T.replace("__F__", name)
    b = base64.b64encode(inner.encode()).decode()
    outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d | bash" 2>&1' % b
    p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"],
                       input=base64.b64encode(outer.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    return p.stdout.decode("utf-8","replace").strip()

for n in sys.argv[1:]:
    print("#### %s" % n)
    r = probe(n)
    print(r if r else "(empty)")
