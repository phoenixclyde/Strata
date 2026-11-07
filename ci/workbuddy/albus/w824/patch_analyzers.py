import io

def patch(path, subs):
    s = io.open(path, encoding='utf-8').read()
    for a, b in subs:
        if a not in s:
            print('  MISS in %s: %r' % (path, a[:50]))
            continue
        s = s.replace(a, b)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched', path)


D0 = "D = '/home/albus/strata166/data/w824kl'"
D1 = "D = sys.argv[1] if len(sys.argv) > 1 else '/home/albus/strata166/data/w824kl'"
A0 = "A = {a: load(a) for a in ('Q1', 'Q0', 'Q1b')}"
A1 = ("ARMS = tuple(sys.argv[2].split(',')) if len(sys.argv) > 2 else ('Q1', 'Q0', 'Q1b')\n"
      "A = {a: load(a) for a in ARMS}")

patch('albus/w824/kl_pair2.py', [
    ('import io, math, os, sys, statistics as st', 'import io, math, os, sys, statistics as st'),
    (D0, D1),
    (A0, A1),
    ('for p, q in PAIRS:',
     'for p, q in ((ARMS[0], ARMS[2]), (ARMS[0], ARMS[1]), (ARMS[2], ARMS[1])):'),
])

patch('albus/w824/kl_shape.py', [
    ('import io, os, statistics as st', 'import io, os, statistics as st, sys'),
    (D0, D1),
    (A0, A1),
    ("for p, q in (('Q1', 'Q1b'), ('Q1', 'Q0'), ('Q1b', 'Q0')):",
     'for p, q in ((ARMS[0], ARMS[2]), (ARMS[0], ARMS[1]), (ARMS[2], ARMS[1])):'),
])
