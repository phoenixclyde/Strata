import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
raw = io.open(P, encoding='utf-8').read().split('\n')

i = next(k for k, l in enumerate(raw) if l.startswith('P222'))
# collect the split block (223..230): the head line then the quoted fragments
j = i
while j + 1 < len(raw) and raw[j + 1].lstrip().startswith("'"):
    j += 1

head = raw[i].rstrip('\t')
frags = []
for k in range(i + 1, j + 1):
    t = raw[k].strip()
    if t.startswith("'"):
        t = t[1:]
    if t.endswith("'"):
        t = t[:-1]
    frags.append(t)

merged = head + ''.join(frags)
cols = merged.split('\t')
print('merged cols =', len(cols), '(want 11)')
out = raw[:i] + [merged] + raw[j + 1:]
# drop trailing empties
while out and out[-1] == '':
    out.pop()
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')

raw2 = [l for l in io.open(P, encoding='utf-8').read().split('\n') if l.strip()]
bad = [(n, len(l.split('\t'))) for n, l in enumerate(raw2) if l.count('\t') != 10]
print('rows:', len(raw2) - 1)
print('rows with != 11 cols:', bad[:6] if bad else 'none')
print('tail:', repr(raw2[-1][:120]))
