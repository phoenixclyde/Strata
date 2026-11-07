# -*- coding: utf-8 -*-
'''AUDIT24 round 2c: the "status line still says the old verdict" cases (纪律24).'''
import io

D = 'D:/workbuddy_space/strata_ws/deploy/'

def rep(name, old, new):
    p = D + name
    s = io.open(p, encoding='utf-8').read()
    if new in s:
        return name + ' already'
    if old not in s:
        return name + ' MISS'
    io.open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new, 1))
    return name + ' ok'

print(rep('W919_RELEASE_NOTES_READ.md',
    '状态：零停服；**一条已实证的现成损失**（PLE 表未锁定），三条待执行',
    '状态：零停服；~~一条已实证的现成损失（PLE 表未锁定）~~ **已撤回（`W920` 实测为 0，`R67 = DONE_NEG`）**，三条待执行'))

print(rep('W923_R61_PMC_FAILED.md',
    '状态：**R61 = DONE_NEG（工具不可用）**；**R60 = 关闭（依据预判，非实测）**；生产已恢复',
    '状态：~~**R61 = DONE_NEG（工具不可用）**；**R60 = 关闭（依据预判，非实测）**~~ '
    '**均已撤回**：rocprof 只在 `HSA_TOOLS_LIB` 注入下不可用，`W942` 用启动器路径采到 VALUBusy 67.1%；'
    '**R60 现为 OPEN**（关闭不合规，见 `W947`）；生产已恢复'))

print(rep('W926_R64_ATTN_INT8.md',
    '状态：**DONE_NEG**（技术前提部分不成立；上限仅 4.0% 刚过噪声门，但需改 Q 量化 → 精度风险）',
    '状态：**DONE_NEG**（技术前提部分不成立；上限仅 4.0% 刚过噪声门，但需改 Q 量化 → 精度风险）。'
    '**注（`AUDIT24`）**：占比段应写 **14.8–15.3%**（不是 15–19%），上限段以 **3.4–4.3%** 为准；`R64` 仍 OPEN（窄化为只做 Q·K）'))

print(rep('W927_DOT8_Q4K_PORT.md',
    '''prefill 提升 = 26.7% × VALU占用 0.81 × MMQ占prefill 0.346 = 7.5%
端到端       = 7.5% × prefill占端到端 73.1%               = 5.5%''',
    '''prefill 提升 = 26.7% × VALU占用 0.81 × MMQ占prefill 0.346 = 7.5%
端到端       = 7.5% × prefill占端到端 73.1%               = 5.5%   ← 【AUDIT24】作废：分母/占比均为模块口径'''))

# PROGRESS: the last "吻合" that still backs the module number
P = 'D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv'
s = io.open(P, encoding='utf-8').read()
import re
for m in re.finditer(r'.{60}吻合.{20}', s):
    print('CONTEXT:', m.group(0).replace('\n', ' '))
