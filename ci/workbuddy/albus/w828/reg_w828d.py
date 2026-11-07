# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P189\t') for l in body)

out = []
for l in body:
    c = l.split('\t')
    if c[0] == 'P184':
        c[10] = ('采纳：**无参数变更**。五项全部结清：pcie-frac 0.20 最优、spec-min-p 0.5 只高 0.4%、pool-workers 默认最优、'
                 'adapt-* 慢 2-4%（P188）、STRATA_SH_STREAM ±2% 噪声（P189）。')
        l = '\t'.join(c)
    out.append(l)

new = '\t'.join([
    'P189', 'PARAM', 'STRATA_SH_STREAM 在本机否（四臂，512 token + ms/window）', 'off（维持 HIP 默认）', 'param', 'ADOPTED', '—', '—', 'P184/P188/P182',
    '测前先查机理：`STRATA_DECODE_TIMING` 的 per layer-window 段是 `CPU experts 0.58 (0.70 entries), VRAM hits 21.41, PCIe 0.01` ⇒ 命中率 97.3%，**每层窗口仅 0.58 个专家走 CPU**。上游 docs/AMD_HIP.md 讲 fork 的收益来自"跑在 GPU 干等 CPU 池的那段时间"（例：4859 槽位、GPU-reach wait 20.7/39.1 ms）；我们 27-31 ms 的 GPU-reach wait 不是等 CPU，**没有洞可填**。四臂实测 ms/window 中位 ta 39.80/38.23，tc 38.19/39.21 ⇒ 对 1 tc 快 4.0%、对 2 tc **慢 2.6%**，方向相反、均值差 0.7%。上游三份实测本身矛盾（#816 Windows gfx1030 on 慢 12-22%；#1272 Linux gfx1030 on 快 7-10%；R9700 gfx1201 on 慢 45%）。',
    '不采纳。附带证据：同臂 tok/s 在不同时间 44.17 vs 47.46（+7.5%），ms/window 四次同配置 38.23-39.80（±2%）⇒ 再次证明 tok/s 不可作判据。',
])

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(out + [new]) + '\n')
print('rows', len(out) + 1)
