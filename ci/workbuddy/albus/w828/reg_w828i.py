# -*- coding: utf-8 -*-
"""Append P194 (spec-window axis closed) / P195 (correction of the '77% wait' reading)."""
import io, os

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')
assert head[0] == 'id', head[:3]

rows = []

rows.append([
    'P194', 'ENGINE',
    '投机窗口策略（--spec 上限 x --spec-min-p 门槛）全轴关闭：生产已在平地正中',
    '--spec 4 --spec-min-p 0.70 维持',
    'engine', 'CONFIRMED', '—', '—', 'P184/P188/P191',
    '8 臂 6 配置（每组 3 条 512-token 贪心，判据 tokens/window ÷ ms/window）：'
    '基线 ta 三条 47.05/46.27/45.71（漂移 2.9%）；'
    'tf=spec8/minp.70 44.97（上限不是约束：T 2.18→2.32，门槛先截断）；'
    'tg=spec8/minp.50 39.96（-15.1%：T +54% 但 tokens/win 仅 +13%，ms/win +29%；VRAM hits/层-窗口 19.9→31.4）；'
    'tk=spec8/minp.85 47.01；tl=spec8/minp.90 45.66；'
    'th=spec8/minp.50+SPEC_COST 46.03（引擎自己的成本感知规则把 T 收到 2.28，与基线 2.18 重合 = 独立验证最优）。'
    '按深度接受率 80.2%/76.9%/57.9%（深度 0/1/2），放松门槛后深度 1-4 只有 62%。',
    '不采纳任何改动：T 在 [1.6,2.4] 是平地（45.7-47.1），T>3 是悬崖'])
rows.append([
    'P195', 'MEASUREMENT',
    '更正 P191 的解释：窗口时间并非 77% 在等专家，而是摊在 15+ 个 kernel 上、最大单项 23.4%',
    '叙事更正（不改配置）',
    'measurement', 'CORRECTED', '—', '—', 'P191/P192',
    '引擎自打的分项（verify.cpp:2487-2488，strata decode GPU stages (ms/window)，合计 44.98）：'
    '专家 VRAM 读取 10.51 ms = 23.4%；两条 dense MLP（hc0/hc1 的 norm+down+up）7.46 = 16.6%；'
    'GDN 主体 7.01 = 15.6%；各类等待 6.50 = 14.5%；QSA 主体 5.88 = 13.1%；路由 3.84 = 8.5%；'
    'shared+量化 2.04 = 4.5%；head 1.73 = 3.8%。'
    'GPU-reach wait 是宿主机等 GPU 里程碑（host 空转），不是 GPU 等数据。',
    '以后判"省算力/省 launch"类开关，先看它对应多大规模的 kernel；最大单项仅 23.4%，所以单项都只值 ±1.5%'])

for r in rows:
    assert len(r) == len(head), (len(r), len(head))
    lines.append('\t'.join(r))

io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines))
for l in lines[-2:]:
    print(l.split('\t')[0], l.split('\t')[2][:60], '|', l.split('\t')[5])
