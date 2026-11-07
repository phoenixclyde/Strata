import json

P = '/home/albus/strata166/data/packs/ud_q4k_tmp'

idx = '/home/albus/strata166/data/packs/ud-q4_k_xl/index.txt'
print('=== index.txt 前两行 ===')
with open(idx, encoding='utf-8') as f:
    for i, ln in enumerate(f):
        print('  ' + ln.rstrip()[:190])
        if i >= 1:
            break

print('')
print('=== 一条 hc 的全行 ===')
with open(idx, encoding='utf-8') as f:
    for ln in f:
        if 'blk.0.hc_attn_down' in ln:
            c = ln.split()
            print('  cols=%d' % len(c))
            for k, v in enumerate(c):
                print('    [%d] %s' % (k, v))
            break

print('')
print('=== compat-bf16.json 的记录 ===')
d = json.load(open('/home/albus/strata166/data/packs/ud-q4_k_xl/compat-bf16.json'))
print('  top keys:', list(d))
print('  rounding:', json.dumps(d.get('rounding'), ensure_ascii=False)[:300])
for e in d.get('tensors', []):
    s = json.dumps(e, ensure_ascii=False)
    if 'blk.0.hc_attn_down' in s:
        print('  entry:', s[:500])
        break
