# -*- coding: utf-8 -*-
import io

p = 'D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md'
s = io.open(p, encoding='utf-8').read()
ins = io.open('D:/workbuddy_space/strata_ws/albus/w828/mem2_section.md', encoding='utf-8').read()

anchor = '## 待办'
i = s.rfind(anchor)
assert i > 0
head, tail = s[:i], s[i:]
body = tail.split('\n', 1)[1]
s2 = head + ins + '\n' + anchor + '\n' + body
io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
print('new len', len(s2))
print('sections:', [l for l in s2.split('\n') if l.startswith('## ')])
