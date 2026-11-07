# -*- coding: utf-8 -*-
'''Replace the shell-mangled AUDIT24 memory block with the clean one; patch the last stale number in W832.'''
import io

mem = 'D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-11-04.md'
s = io.open(mem, encoding='utf-8').read()
i = s.find('## AUDIT24')
clean = io.open('D:/workbuddy_space/strata_ws/albus/w952/mem_block.md', encoding='utf-8').read().rstrip() + '\n'
if i >= 0:
    s = s[:i] + clean
else:
    s = s.rstrip() + '\n\n' + clean
io.open(mem, 'w', encoding='utf-8', newline='').write(s)
print('memory block replaced, len now', len(s))

# W832 line 666: "端到端上限 5.5% 过 3.2% 门" -> the真-kernel number
p = 'D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md'
t = io.open(p, encoding='utf-8').read()
old = 'W4A4 下指令减半、端到端上限 5.5% 过 3.2% 门'
new = 'W4A4 下指令减半（端到端上限按真 kernel 分母为 **−2.05%**，原 5.5% 是模块分母，`AUDIT24` 更正）'
n = t.count(old)
t = t.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('W832 stale 5.5% fixed:', n)
