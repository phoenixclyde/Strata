# -*- coding: utf-8 -*-
'''AUDIT24 round 2b: fix the two anchors.'''
import io

D = 'D:/workbuddy_space/strata_ws/deploy/'

# W942: insert the conclusion-level retraction before item (2) in the existing banner
p = D + 'W942_R61_VALUBUSY_67.md'
s = io.open(p, encoding='utf-8').read()
old = '②**67.1% 是 M=1024 的形状**'
new = ('**②结论层也要撤**：本件据此把 **R60 = DONE_NEG**、**R84 = DONE_NEG**，但 `W947` 按纪律⑱ 判定'
       '「用别的量推断」不合规 ⇒ **R60/R63 改回 OPEN、R84 改 INFLIGHT**（`R91` 另立）。本件的 VALUBUSY **数字**保留，'
       '**由它推出的两条关闭不保留**。\n'
       '> ③**67.1% 是 M=1024 的形状**')
if '结论层也要撤' not in s:
    s = s.replace(old, new, 1)
    # the old ③ (dp4a 53.3%) becomes ④
    s = s.replace('③§4 仍引 dp4a 53.3%', '④§4 仍引 dp4a 53.3%', 1)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('W942 patched')
else:
    print('W942 already')

# W947: no banner at all yet -- add one after the H1
p = D + 'W947_BACKTRACK_AND_DOT8_V1.md'
s = io.open(p, encoding='utf-8').read()
banner = '''
> **【AUDIT24 P1 · 2026-11-04】§50-57 猜的根因是错的**：`W950/W951` 实测证明不是 `_Float16` 转换，
> 而是 **M=64 版缺 warp 归约**（32 个 lane 互相覆盖，只剩 1/32 的 K）+ host 参考多乘了一次激活 scale。
> 修正后 **dp4a 0.00319 / dot8 0.06481**（`W951`）。§1 的"4 条重开"结论**不受影响**（那是纪律判定，不是数值）。
'''
if '【AUDIT24' not in s:
    lines = s.split('\n')
    lines.insert(1, banner.rstrip())
    io.open(p, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('W947 banner added')
else:
    print('W947 already')
