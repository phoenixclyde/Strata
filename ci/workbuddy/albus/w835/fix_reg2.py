import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
raw = io.open(P, encoding='utf-8').read().split('\n')

# 1) the 4 single-column rows: what are they?
print('--- single-column rows ---')
for n, l in enumerate(raw):
    if l.strip() and l.count('\t') == 0:
        print(n, '|', repr(l[:160]))

# 2) fix P222: pad to 11 columns (append verdict)
i = next(k for k, l in enumerate(raw) if l.startswith('P222'))
cols = raw[i].split('\t')
print('\nP222 cols =', len(cols))
if len(cols) == 10:
    cols.append('不采用；生产不变')
raw[i] = '\t'.join(cols)
print('P222 now cols =', len(raw[i].split('\t')))

io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(raw).rstrip('\n') + '\n')

raw2 = [l for l in io.open(P, encoding='utf-8').read().split('\n') if l.strip()]
bad = [(n, l.count('\t') + 1) for n, l in enumerate(raw2) if l.count('\t') != 10]
print('\nrows:', len(raw2) - 1)
print('rows with != 11 cols:', bad if bad else 'none')
