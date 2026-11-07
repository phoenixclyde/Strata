import io, os, statistics as st, sys

D = sys.argv[1] if len(sys.argv) > 1 else '/home/albus/strata166/data/w824kl'


def load(arm):
    rows = {}
    with io.open(os.path.join(D, 'w803_logpos_%s.tsv' % arm), encoding='utf-8') as f:
        for line in f:
            c = line.rstrip('\n').split('\t')
            if len(c) < 9:
                continue
            rows[int(c[0])] = (float(c[2]), int(c[3]))
    return rows


ARMS = tuple(sys.argv[2].split(',')) if len(sys.argv) > 2 else ('Q1', 'Q0', 'Q1b')
A = {a: load(a) for a in ARMS}
hdr = '%-12s %5s %8s %6s %11s %11s' % ('pair', 'n', 'identical', 'n=0', 'max|dlp|', 'p95|dlp|')
print(hdr)
for p, q in ((ARMS[0], ARMS[2]), (ARMS[0], ARMS[1]), (ARMS[2], ARMS[1])):
    P, Q = A[p], A[q]
    pos = sorted(set(P) & set(Q))
    d = [abs(P[i][0] - Q[i][0]) for i in pos]
    same = sum(1 for x in d if x == 0.0)
    ds = sorted(d)
    p95 = ds[min(len(ds) - 1, int(0.95 * len(ds)))]
    line = '%-12s %5d %7.1f%% %6d %11.6f %11.6f' % (p + '||' + q, len(pos), 100.0 * same / len(pos), same, max(d), p95)
    print(line)

print('')
print('=== raw sample rows (columns 1-8) ===')
for a in ('Q1', 'Q1b'):
    with io.open(os.path.join(D, 'w803_logpos_%s.tsv' % a), encoding='utf-8') as f:
        first = f.readline().rstrip('\n').split('\t')
    print(a, ' | '.join(first[:8]))
