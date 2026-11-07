# -*- coding: utf-8 -*-
'''AUDIT24 final: adjudicate the R86 vs W945 conflict and record the ordering rule.'''
import io

P = 'D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md'
s = io.open(P, encoding='utf-8').read()
edits = []

old = '手段按 **R86（Q5_1 repack）** > R46（attention 效率）> R64（Q·K int8）排序'
new = ('手段按 **R86（Q5_1 repack，先做单内核 A/B）** > R46（attention 效率）> R64（Q·K int8）排序。'
       '**【AUDIT24 裁决】R86 排第一是"最便宜且 bit-exact（无精度门）"，不是"预期最大"** —— '
       '外证 +84% 是 dense 27B 的形状，本机是每专家 ~320 token，端到端**未知（0 ~ −6.3%）**；'
       'A/B 判据：单内核 Δ ≥40% 才动生产、<20% 立即判否。')
if old in s and 'AUDIT24 裁决' not in s:
    s = s.replace(old, new, 1); edits.append('R85-row')
else:
    edits.append('R85-row-MISS/already')

old2 = '> ⇒ 我们上一轮把权重压在"指令层"，实际最大杠杆在 **拷贝/调度层（R88）**，其次 **repack（R86）**。'
new2 = ('> ⇒ 我们上一轮把权重压在"指令层"，实际最大杠杆在 **拷贝/调度层（R88）**，其次 **repack（R86）**。\n'
        '> **【AUDIT24 补充】** 这两句与 `§6.5` 的排序不矛盾但口径不同：`R88` 的**预期**更大（外证同模型 pp8192 877→1978），'
        '`R86` 的**成本**更低（单内核 A/B、bit-exact）。⇒ 队列按"先便宜后贵"排（R86 先测），'
        '但 R86 的收益**不得**按 +84% 预期 —— `W945` 已把它下调为 0 ~ −6.3% 未知。')
if old2 in s and 'AUDIT24 补充' not in s:
    s = s.replace(old2, new2, 1); edits.append('637')
else:
    edits.append('637-MISS/already')

io.open(P, 'w', encoding='utf-8', newline='').write(s)

import hashlib
b = io.open(P, 'rb').read()
print('edits:', edits)
print('W832 md5 now', hashlib.md5(b).hexdigest())
