# -*- coding: utf-8 -*-
'''AUDIT24: fix the markdown table in W832 (unescaped |Δ| breaks 8+ rows; R89 row has wrong cells).'''
import io

P = 'D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md'
s = io.open(P, encoding='utf-8').read()
n_before = s.count('|Δ|')

# 1) escape the bare |Δ| that splits cells (rows with an extra pipe render as garbage)
s = s.replace('|Δ|', '\\|Δ\\|')

# 2) R89 row: the last two cells say "已结 / 复核中" -- replace with the real gate + criterion
old = '| 已结 | 复核中 |'
new = '| 停服 A/B 三档深度（1x / 3x / 6x）的绝对 ms 差 < 2xCV ⇒ 不做 | `|Δ| ≥ 2×CV`；每档 `0 reused`；同时记录 attn 相位占比 |'
hit = s.count(old)
s = s.replace(old, new)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('escaped %d occurrences of |Δ|; R89 cells replaced %d' % (n_before, hit))

# verify table shape
lines = s.split('\n')
bad = [(i, l.count('|')) for i, l in enumerate(lines, 1)
       if l.startswith('|') and 460 < i < 810 and l.count('|') - l.count('\\|') not in (3, 4, 5, 6, 7)]
print('rows still misaligned (lines 460-810):', bad[:10])
