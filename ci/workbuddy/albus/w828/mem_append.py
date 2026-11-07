# -*- coding: utf-8 -*-
import io

p = 'D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md'
s = io.open(p, encoding='utf-8').read()
ins = io.open('D:/workbuddy_space/strata_ws/albus/w828/mem_section.md', encoding='utf-8').read()

anchor = '## 待办'
i = s.rfind(anchor)
assert i > 0, 'anchor missing'
head, tail = s[:i], s[i:]

add = ('- ~~投机窗口策略~~ 已结清（P194）。\n'
       '- 若要再往上，只剩改约束：Q3_K_XL（需先下 50 GB pack + KL 门）、降上下文到 16-32K、或更大显存。\n')

body = tail.split('\n', 1)[1]          # everything after the "## 待办" line
s2 = head + ins + '\n' + anchor + '\n' + add + body
io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
print('new len', len(s2))
print(s2[-800:])
