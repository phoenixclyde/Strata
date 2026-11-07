import difflib, re

A = open('albus/w823/mmvq_old.cu', encoding='utf-8', errors='replace').read().splitlines()
B = open('albus/w823/mmvq_new.cu', encoding='utf-8', errors='replace').read().splitlines()
d = list(difflib.unified_diff(A, B, 'old', 'new', n=6, lineterm=''))
open('albus/w823/mmvq.diff', 'w', encoding='utf-8', newline='\n').write('\n'.join(d) + '\n')

# 按 hunk 切
hunks, cur = [], None
for x in d:
    if x.startswith('@@'):
        cur = [x]; hunks.append(cur)
    elif cur is not None:
        cur.append(x)

pat = re.compile(r'__HIPCC__|HIP|gfx9|kq|KQ|K-quant|k-quant|Q4_K|Q5_K|Q6_K|Q5_1|q4_K|MMQ_K|sm6|SM6|SM7|SM8|arch|__CUDA_ARCH__', re.I)
for i, h in enumerate(hunks, 1):
    body = h[1:]
    hits = [l for l in body if l[:1] in '+-' and pat.search(l)]
    print('### hunk %d  %s   (+-%d lines, %d 命中关键词)' % (i, h[0], len([l for l in body if l[:1] in '+-']), len(hits)))
    for l in hits[:6]:
        print('    ', l.strip()[:150])
