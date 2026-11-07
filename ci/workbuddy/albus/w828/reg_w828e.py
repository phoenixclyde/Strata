# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P190\t') for l in body)

new = '\t'.join([
    'P190', 'MEASUREMENT', 'calibrate 重跑两次：单实例内扫描可信、每值重启不可信', '两次建议完全不同', 'measurement', 'CONFIRMED', '—', '—', 'P184/P185/P188/P189',
    '同一机器/引擎/配置跑两次（3425 s、3273 s），settings 完全不同：pcie-frac 0.20 vs 0.00，spec-min-p 0.50 vs 0.70，adapt 1/80 vs 1/160，SH_STREAM 1 vs 未设。逐项：pcie_sweep 排序完全一致（数值差 ≤3.3%）；workers 几乎逐位相同（20:43.59/43.46、13:43.57/43.37、10:42.93/42.93、5:40.90/40.16）；confirm 两次都显示引擎默认 0.36 比最优慢 13.7% / 17.8%。但 adapt **两次结论相反**（run1 1/80 赢 +10.3%，run2 1/160 赢 +9.1%，同一候选两次差 5-7 tok/s）；sh_stream 也相反（run1 1 赢 +7.5%，run2 0 赢 −1.0%）。',
    '**规则**：(1) calibrate 的"单实例内 strata_tune 扫描"结果直接用；(2) "每值重启引擎"的项一律视为不可用，必须自己 ABBA（噪声 ±10% 足以让任意候选看起来赢 7-10%）；(3) `--spec-min-p` 的"最优点"本身在噪声内（0.5 与 0.7 差 0.5%，两次各选一个），只能得出"0.3 明显差、0.5-0.7 等价"。',
])

rows2 = []
for l in body:
    c = l.split('\t')
    if c[0] == 'P184':
        c[9] = c[9] + (' ｜ **P190 重跑**：两次 settings 完全不同（0.20/0.00、0.50/0.70、1/80/1/160、SH_STREAM 1/未设），'
                       '证明"每值重启"项不可用；但 `confirm` 两次一致显示引擎默认 `pcie_frac 0.36` 比最优慢 **13.7% / 17.8%** ——'
                       '这是显式 `--pcie-frac 0.20` 的必要性证据。')
        l = '\t'.join(c)
    rows2.append(l)

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(rows2 + [new]) + '\n')
print('rows', len(rows2) + 1)
