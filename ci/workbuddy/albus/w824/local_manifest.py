import hashlib, os, sys

ROOT = '/home/albus/strata166/src0271'
out = []
for base in ('src', 'include', 'cmake'):
    for dp, _, fns in os.walk(os.path.join(ROOT, base)):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT)
            try:
                h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            except OSError:
                continue
            out.append('%s %s' % (h, rel))
p = os.path.join(ROOT, 'CMakeLists.txt')
out.append('%s CMakeLists.txt' % hashlib.sha256(open(p, 'rb').read()).hexdigest())
open('/home/albus/strata166/tmp/local271_manifest.txt', 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('files', len(out))
