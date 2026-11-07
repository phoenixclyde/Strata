# -*- coding: utf-8 -*-
'''Repair: the AUDIT24 notes were appended with real newlines, splitting 3 TSV rows. Join them back.'''
import io, re

P = 'D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv'
lines = io.open(P, encoding='utf-8').read().split('\n')
out, joined = [], 0
for ln in lines:
    if ln.startswith('**【AUDIT24') and out:
        out[-1] = out[-1].rstrip() + ' ' + ln.strip()
        joined += 1
    else:
        out.append(ln)
txt = '\n'.join(out)
# last ledger item from the teammate: R61 still said "与 W924 的 dp4a 占 53.3% 吻合"
before = txt.count('（与 W924 的 dp4a 占 53.3% 吻合）')
txt = txt.replace('（与 W924 的 dp4a 占 53.3% 吻合）',
                  '（口径更正：53.3% 是模块级分母，真 kernel 是 30.0%，见 `W943`/`AUDIT24`）')
io.open(P, 'w', encoding='utf-8', newline='').write(txt)

# verify
bad = [(i, len(l.split('\t'))) for i, l in enumerate(txt.split('\n'), 1) if l.strip() and len(l.split('\t')) != 10]
print('joined %d orphan lines | 53.3%% phrase fixed: %d' % (joined, before))
print('rows with != 10 cols:', bad[:6])
