# -*- coding: utf-8 -*-
"""W709 步17：P22（--prefill auto:32768 族）实测无效果 => REJECTED"""
import io, os, shutil, time, hashlib

REG = r'D:/strata166/params/PARAM_REGISTER.tsv'
os.makedirs(r'D:/strata166/params', exist_ok=True)
bak = REG + '.bak_w709b_' + time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(REG, bak)
b0 = open(REG, 'rb').read()
print('backup ->', os.path.basename(bak), '| before %d B md5=%s' % (len(b0), hashlib.md5(b0).hexdigest()))

raw = io.open(REG, encoding='utf-8-sig').read()
lines = raw.splitlines()
hdr = lines[0].split('\t')
assert len(hdr) == 11

EV = ('W709 交错 A/B 实测（auto:16384，18,083-token 冷 prompt，各 2 轮）：'
      '预填 454.05 vs 455.05 = -0.22%（预填分辨力 1.2~1.4%）=> 无效果；'
      '解码 46.4 vs 45.7 = +1.5%（解码分辨力 11.6~13%）=> 亦无效果')
done = 0
for i, ln in enumerate(lines):
    f = ln.split('\t')
    if f[0] == 'P22':
        d = dict(zip(hdr, f))
        d['status'] = 'REJECTED'
        d['evidence'] = EV
        d['verdict'] = '实测 auto:16384 无效果 => 不采用（auto:32768 未单独测：同族更大 chunk，机制无新增收益且借槽更多）'
        lines[i] = '\t'.join(d[c] for c in hdr)
        done += 1
assert done == 1, done
out = ('\n'.join(lines) + '\n').encode('utf-8')
assert out.count(b'\r') == 0 and not out.startswith(b'\xef\xbb\xbf')
open(REG, 'wb').write(out)
import collections
print('after  %d B md5=%s CR=%d' % (len(out), hashlib.md5(out).hexdigest(), out.count(b'\r')))
print('status =', dict(collections.Counter(x.split('\t')[5] for x in lines[1:] if x.strip())))
for rid in ('P22',):
    for ln in lines:
        f = ln.split('\t')
        if f[0] == rid:
            print('  %-4s %-16s val=%-14s %-9s %s' % (f[0], f[2], f[3], f[5], f[10][:80]))
