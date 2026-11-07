#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定向扫描：prompt attention 各族内核 + 热路径关键族（mmvq/moe/router/select/iq）的 vgpr 与溢出。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

PY = r'''
import re, glob, subprocess, os
COB='/opt/rocm/llvm/bin/clang-offload-bundler'; OC='/opt/rocm/llvm/bin/llvm-objcopy'; RO='/opt/rocm/llvm/bin/llvm-readobj'
D='/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda'
KEY=('prompt_attn','attn_chunk','qsa_gate','block_topk','block_scores','native_mmvq','s2_expert','router','expdec','dequant')
rows=[]
for o in sorted(glob.glob(D+'/*.cu.o')):
    tu=os.path.basename(o).replace('.cu.o','')
    fat='/tmp/f.fat'; hs='/tmp/f.hsaco'
    for p in (fat,hs):
        if os.path.exists(p): os.remove(p)
    subprocess.run([OC,'--dump-section','.hip_fatbin='+fat,o],capture_output=True)
    if not (os.path.exists(fat) and os.path.getsize(fat)>0): continue
    ids=subprocess.run([COB,'--list','--type=o','--input='+fat],capture_output=True,text=True).stdout
    idl=[x for x in ids.splitlines() if 'amdgcn' in x]
    if not idl: continue
    subprocess.run([COB,'--unbundle','--type=o','--targets='+idl[0],'--input='+fat,'--output='+hs],capture_output=True)
    if not os.path.exists(hs): continue
    txt=subprocess.run([RO,'--notes',hs],capture_output=True,text=True).stdout
    cur=None
    for ln in txt.splitlines():
        m=re.match(r'\s*-?\s*\.name:\s*(\S+)',ln)
        if m:
            if cur: rows.append(cur)
            cur={'tu':tu,'name':m.group(1)}
            continue
        if cur is None: continue
        m=re.match(r'\s*\.(vgpr_count|sgpr_count|private_segment_fixed_size|group_segment_fixed_size|wavefront_size):\s*(\S+)',ln)
        if m: cur[m.group(1)]=m.group(2)
    if cur: rows.append(cur)

import subprocess as sp
def dem(n):
    return sp.run(['c++filt',n],capture_output=True,text=True).stdout.strip()

def num(x):
    try: return int(x)
    except: return 0

print("=== prompt_attn 各族 ===")
for r in rows:
    if 'prompt_attn' in r['name'] or 'prompt_attn' in r['tu']:
        print('%-20s %-58s vgpr=%-4s priv=%-5s lds=%-6s' % (r['tu'], dem(r['name'])[:58], r.get('vgpr_count'), r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size')))

print("\n=== 关键族中溢出者（priv>0）===")
sel=[r for r in rows if num(r.get('private_segment_fixed_size'))>0 and any(k in r['name'] or k in r['tu'] for k in KEY)]
sel.sort(key=lambda r:-num(r.get('private_segment_fixed_size')))
for r in sel[:30]:
    print('%-20s %-58s vgpr=%-4s priv=%-5s lds=%-6s' % (r['tu'], dem(r['name'])[:58], r.get('vgpr_count'), r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size')))
'''

b = base64.b64encode(PY.encode()).decode()
outer = ('docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c '
         '"echo %s | base64 -d > /tmp/s2.py && python3 /tmp/s2.py" 2>&1') % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"],
                   input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1500)
print(p.stdout.decode("utf-8","replace")[:9000])
