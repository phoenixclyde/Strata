#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量扫描 build-906 里所有 kernel TU：输出每内核 vgpr/sgpr/private(溢出)/lds。
按 private_segment_fixed_size 降序，突出溢出者。一次容器内完成。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

PY = r'''
import sys, re, glob, subprocess, os
COB='/opt/rocm/llvm/bin/clang-offload-bundler'; OC='/opt/rocm/llvm/bin/llvm-objcopy'; RO='/opt/rocm/llvm/bin/llvm-readobj'
D='/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda'
rows=[]
for o in sorted(glob.glob(D+'/*.cu.o')):
    tu=os.path.basename(o).replace('.cu.o','')
    fat='/tmp/f.fat'; hs='/tmp/f.hsaco'
    for p in (fat,hs):
        if os.path.exists(p): os.remove(p)
    subprocess.run([OC,'--dump-section','.hip_fatbin='+fat,o],capture_output=True)
    if not os.path.exists(fat) or os.path.getsize(fat)==0: continue
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
print('TOTAL %d kernels from scan' % len(rows))
def num(x):
    try: return int(x)
    except: return 0
rows.sort(key=lambda r:-num(r.get('private_segment_fixed_size')))
sp=[r for r in rows if num(r.get('private_segment_fixed_size'))>0]
print('SPILLING %d' % len(sp))
for r in sp[:40]:
    print('%-34s %-46s vgpr=%-4s priv=%-7s lds=%-6s' % (r['tu'], r['name'][:46], r.get('vgpr_count'), r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size')))
rows.sort(key=lambda r:-num(r.get('vgpr_count')))
print('--- top VGPR ---')
for r in rows[:25]:
    print('%-30s %-46s vgpr=%-4s priv=%-6s lds=%-6s' % (r['tu'], r['name'][:46], r.get('vgpr_count'), r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size')))
'''

b = base64.b64encode(PY.encode()).decode()
outer = ('docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c '
         '"echo %s | base64 -d > /tmp/scan.py && python3 /tmp/scan.py" 2>&1') % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"],
                   input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1500)
print(p.stdout.decode("utf-8","replace")[:8000])
