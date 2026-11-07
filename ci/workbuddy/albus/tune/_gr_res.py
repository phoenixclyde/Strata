#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 fused_gr 全部实例的 vgpr/私有段，并用 c++filt 还原签名，便于判断"实际在跑的那个"有没有溢出。"""
import subprocess, base64

REMOTE = "albus@192.168.50.166"

PY = r'''
import re, subprocess, os
COB='/opt/rocm/llvm/bin/clang-offload-bundler'; OC='/opt/rocm/llvm/bin/llvm-objcopy'; RO='/opt/rocm/llvm/bin/llvm-readobj'
D='/src/build-906/CMakeFiles/strata_kernels.dir/src/kernels/cuda'
f='fused_gr'
o=D+'/'+f+'.cu.o'
fat='/tmp/f.fat'; hs='/tmp/f.hsaco'
for p in (fat,hs):
    if os.path.exists(p): os.remove(p)
subprocess.run([OC,'--dump-section','.hip_fatbin='+fat,o],capture_output=True)
ids=subprocess.run([COB,'--list','--type=o','--input='+fat],capture_output=True,text=True).stdout
idl=[x for x in ids.splitlines() if 'amdgcn' in x]
subprocess.run([COB,'--unbundle','--type=o','--targets='+idl[0],'--input='+fat,'--output='+hs],capture_output=True)
txt=subprocess.run([RO,'--notes',hs],capture_output=True,text=True).stdout
rows=[]; cur=None
for ln in txt.splitlines():
    m=re.match(r'\s*-?\s*\.name:\s*(\S+)',ln)
    if m:
        if cur: rows.append(cur)
        cur={'name':m.group(1)}; continue
    if cur is None: continue
    m=re.match(r'\s*\.(vgpr_count|sgpr_count|private_segment_fixed_size|group_segment_fixed_size):\s*(\S+)',ln)
    if m: cur[m.group(1)]=m.group(2)
if cur: rows.append(cur)

def dem(n):
    return subprocess.run(['c++filt',n],capture_output=True,text=True).stdout.strip()

def num(x):
    try: return int(x)
    except: return 0

# 只关心 gr_ 内核
rows=[r for r in rows if 'gr_' in r['name']]
rows.sort(key=lambda r:(-num(r.get('private_segment_fixed_size')), -num(r.get('vgpr_count'))))
print('%-72s %5s %6s %6s' % ('kernel', 'vgpr', 'priv', 'lds'))
for r in rows:
    d=dem(r['name'])
    d=d.replace('strata::kernels::(anonymous namespace)::','')
    print('%-72s %5s %6s %6s' % (d[:72], r.get('vgpr_count'), r.get('private_segment_fixed_size'), r.get('group_segment_fixed_size')))
print('TOTAL', len(rows))
'''

b = base64.b64encode(PY.encode()).decode()
outer = 'docker run --rm --entrypoint bash strata-gfx906:0.2.3 -c "echo %s | base64 -d > /tmp/g.py && python3 /tmp/g.py" 2>&1' % b
p = subprocess.run(["ssh","-o","BatchMode=yes",REMOTE,"base64 -d | bash"], input=base64.b64encode(outer.encode()),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
print(p.stdout.decode("utf-8","replace")[:6000])
