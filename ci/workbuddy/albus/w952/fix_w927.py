# -*- coding: utf-8 -*-
'''AUDIT24: W927 banner (module-level denominator + unreferenced external numbers).'''
import io

p = 'D:/workbuddy_space/strata_ws/deploy/W927_DOT8_Q4K_PORT.md'
s = io.open(p, encoding='utf-8').read()
MARK = '【AUDIT24'
banner = '''
> **【AUDIT24 P1 · 2026-11-04】§79-91 的端到端 5.5% 用的是模块级分母**：它按「dot 占 53.3%」推，
> 而 53.3% 是**整个 mmq-instance 模块**求和；真 kernel 里 dot4 = **30.0%**（`W943`）⇒ 端到端改判 **−2.05%**。
> dot8 的方向（W4A4 下 8 个 i4 只需 1 条指令）**仍成立**，现由 `R84`（内核原型，数值 dp4a 0.00319 / dot8 0.06481）
> 与 `R91`（生产接入，P4 KL 门决定生死）在办。
> 另：§24-36 引用的 `K100LC-RT4` / `gfx926` 数据**没有 URL 或 commit**，`gfx926` 也不是标准架构名 —— 该段仅作线索，不得当判据。
'''
if MARK not in s:
    lines = s.split('\n')
    idx = next((i for i, l in enumerate(lines) if l.startswith('# ')), 0)
    lines.insert(idx + 1, banner.rstrip())
    io.open(p, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('W927 banner added')
else:
    print('W927 already has one')
