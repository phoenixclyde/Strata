# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P191\t') for l in body)

new = '\t'.join([
    'P191', 'ENGINE', '上游给 gfx1151 集的 15 项 exact 优化在 gfx906 上无效（5 项实测）', '全部不采纳', 'engine', 'CONFIRMED', '—', '—', 'P190/P189/P184',
    'arch_defaults.cpp 的 gfx1151 表有 15 项 "Exact (bitwise) on Aurora" 开关，代码里**无架构门**、上游只在 Strix Halo（RDNA3.5 集显、wave32）验过、从未在任何独显测量。本轮测 5 项（每组 6 条 512-token，ms/window）：基线 ta **38.22**；td（ATTN_LANECELL+MMVF_ROWS+LFUSE）**37.80（+1.1%）**、配对 +0.4%/−3.8%；te（EXPERT_V2+GDN_SPLIT）**38.74（−1.4%）**、配对 −3.4%/+1.8%。td 唯一的正面信号是方差减半（跨度 1.42 ms vs 4.26 ms），中位未动。',
    '**统一解释（比逐个否掉更有用）**：我们的窗口时间构成 `verify 34.0 (GPU-reach wait 28.0 + per-layer host 4.1) + draft` ⇒ **GPU-reach wait 占 77%**，GPU 四分之三时间在等专家数据。这 5 项全属"省算力/省 launch/小 kernel 提效"，被等待淹没；它们的设计场景是 16 GB 集显（统一内存、等待极短、算力才是瓶颈），前提与我们相反。⇒ 剩余 10 项同类别，优先度极低；真要提升应先攻那 77%，不是在剩 23% 里抠 1%。',
])

rows2 = []
for l in body:
    c = l.split('\t')
    if c[0] == 'P184':
        c[10] = c[10] + ' ｜ 另有 5 项 gfx1151 集显 exact 优化实测无效（P191），但同属"省算力"类，输在 77% 的数据等待上。'
        l = '\t'.join(c)
    rows2.append(l)

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(rows2 + [new]) + '\n')
print('rows', len(rows2) + 1)
