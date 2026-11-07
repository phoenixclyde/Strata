# -*- coding: utf-8 -*-
'''AUDIT24 round 2: four banners said "口径改了" but left the conclusion standing.'''
import io

D = 'D:/workbuddy_space/strata_ws/deploy/'

def patch(name, old, new):
    p = D + name
    s = io.open(p, encoding='utf-8').read()
    if new in s:
        return name + ' already'
    if old not in s:
        return name + ' ANCHOR-MISS'
    s = s.replace(old, new, 1)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    return name + ' patched'

print(patch('W942_R61_VALUBUSY_67.md',
    '> ②**67.1% 是 M=1024 的形状**',
    '> ②**结论层也要撤**：本件据此把 **R60 = DONE_NEG**、**R84 = DONE_NEG**，但 `W947` 按纪律⑱ 已判定'
    '「用别的量推断」不合规 ⇒ **R60/R63 改回 OPEN、R84 改 INFLIGHT**（`R91` 另立）。本件的 VALUBUSY **数字**保留，'
    '**由它推出的两条关闭不保留**。\n'
    '> ③**67.1% 是 M=1024 的形状**'))

print(patch('W944_REASSESS_GFX906_PROJECTS.md',
    '> 端到端预期（down 占 prefill 13.8%）与 `R86` 的排序**不变**。',
    '> 端到端预期：本件 §60 的 **−6.3%** 已被 `W945 §6.3` 下调为 **0 ~ −6.3%（未知）** —— '
    '只有 down 占 prefill 13.8% 这个分母不变，**上限不能再当预期用**；判据是单内核 A/B（Δ≥40% 才动生产）。'))

print(patch('W946_GFX906_PROJECTS_LANDSCAPE.md',
    '> ②§56-63「我们 0.4.1 vs 社区 v0.7.0、差 3 个 minor」的判据已在 `W948` 自查中作废（版本号不是可比锚点），',
    '> ③**R89 的结论也撤**：本件 §6 表与 §7 仍写「当场判否（A 级源码）」「早已 gather-only」，'
    '但源码阅读按 `W939 §0` 是 **D 级**；`W947` 已把 `R89` 改回 **OPEN**（`W832@f40c8f39:803` 同步），待 depth 1×/3×/6× 实测。\n'
    '> ②§56-63「我们 0.4.1 vs 社区 v0.7.0、差 3 个 minor」的判据已在 `W948` 自查中作废（版本号不是可比锚点），'))

print(patch('W947_BACKTRACK_AND_DOT8_V1.md',
    '> **【AUDIT24 P1 · 2026-11-04】',
    '> **【AUDIT24 P1b · 2026-11-04】§50-57 猜的根因是错的**：`W950/W951` 实测证明不是 `_Float16` 转换，'
    '而是 **M=64 版缺 warp 归约**（32 lane 互相覆盖，只剩 1/32 的 K）+ host 参考多乘了一次激活 scale。'
    '修正后 dp4a **0.00319** / dot8 **0.06481**。\n'
    '>\n'
    '> **【AUDIT24 P1 · 2026-11-04】'))
