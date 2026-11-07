cd /home/albus/strata166
python3 - <<'PY'
import hashlib, json, os
S27='/home/albus/strata166/src0271'
S28='/home/albus/strata166/src028'
U27=json.load(open('/home/albus/strata166/tmp/tree_0271.json'))
U28=json.load(open('/home/albus/strata166/tmp/tree_028.json'))
SKIP={'build-0271','build-0271_out','build-028','build-028w','.git','__pycache__','.cache'}

def sha(p):
    h=hashlib.sha1()
    h.update(b'blob %d\0' % os.path.getsize(p))
    with open(p,'rb') as f:
        while True:
            b=f.read(1<<20)
            if not b: break
            h.update(b)
    return h.hexdigest()

def scan(root):
    out={}
    for dp,dn,fn in os.walk(root):
        dn[:]=[d for d in dn if d not in SKIP]
        for f in fn:
            p=os.path.join(dp,f)
            if os.path.islink(p): continue
            rel=os.path.relpath(p,root).replace('\\','/')
            try: out[rel]=sha(p)
            except OSError: pass
    return out

A=scan(S27); B=scan(S28)
print('files: src0271=%d  src028=%d' % (len(A), len(B)))

patched=[f for f,s in A.items() if f in U27 and U27[f]!=s]          # our edits to upstream files
added  =[f for f,s in A.items() if f not in U27]                     # files upstream has not
kept=lost=other=0
lost_list=[]; other_list=[]; added_lost=[]
for f in patched:
    if f not in B:
        lost+=1; lost_list.append((f,'deleted in src028')); continue
    if B[f]==A[f]: kept+=1
    elif B[f]==U28.get(f): lost+=1; lost_list.append((f,'replaced by upstream v0.2.8'))
    else: other+=1; other_list.append(f)
for f in added:
    if f not in B: added_lost.append(f)

print()
print('--- our edits to upstream files: %d  (kept %d / LOST %d / changed-on-both %d) ---'
      % (len(patched), kept, lost, other))
for f,why in sorted(lost_list):
    print('  LOST  %-58s %s' % (f, why))
for f in sorted(other_list):
    print('  BOTH  %-58s (edited here AND differs from upstream 0.2.8)' % f)
print()
print('--- our own added files: %d  (missing in src028: %d) ---' % (len(added), len(added_lost)))
for f in sorted(added_lost)[:40]:
    print('  GONE  ', f)
PY
