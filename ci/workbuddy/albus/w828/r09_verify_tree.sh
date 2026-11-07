cd /home/albus/strata166
python3 - <<'PY'
import hashlib, json, os
ROOT='/home/albus/strata166/src028'
up=json.load(open('/home/albus/strata166/tmp/tree_028.json'))
SKIP_DIRS={'build-028','build-0271','build-0271_out','.git'}

def blob_sha1(path):
    h=hashlib.sha1()
    h.update(b'blob %d\0' % os.path.getsize(path))
    with open(path,'rb') as f:
        while True:
            b=f.read(1<<20)
            if not b: break
            h.update(b)
    return h.hexdigest()

local={}
for dp,dn,fn in os.walk(ROOT):
    dn[:]=[d for d in dn if d not in SKIP_DIRS]
    for f in fn:
        p=os.path.join(dp,f)
        rel=os.path.relpath(p,ROOT).replace('\\','/')
        if os.path.islink(p): continue
        local[rel]=p

diff=[]; same=0
for rel,p in local.items():
    if rel in up:
        if blob_sha1(p)==up[rel]: same+=1
        else: diff.append(rel)
missing=[r for r in up if r not in local]
extra=[r for r in local if r not in up]
print('local files %d | identical to v0.2.8: %d | differ: %d | upstream-only: %d | local-only: %d'
      % (len(local), same, len(diff), len(missing), len(extra)))
print('\n--- DIFFER (we changed, or upstream changed something we did not fetch) ---')
for r in sorted(diff): print('  ', r)
print('\n--- UPSTREAM ONLY (missing here) ---')
for r in sorted(missing)[:60]: print('  ', r)
print('   ... total', len(missing))
print('\n--- LOCAL ONLY ---')
for r in sorted(extra)[:40]: print('  ', r)
print('   ... total', len(extra))
PY
