# -*- coding: utf-8 -*-
"""Correct P199 (its 8K claim was an invalid extrapolation) and add P200 (the measurement rule)."""
import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')
assert head[5] == 'status' and head[10] == 'verdict', head

n = 0
for k, ln in enumerate(lines):
    f = ln.split('\t')
    if f[0] != 'P199':
        continue
    f[5] = 'CORRECTED'
    f[9] = (f[9] +
            ' || 更正（同日补测 7.2K 与 14.3K，各 2 条不同文本）：CPU_SHARE=0 在 7186 tok 得 11.68/11.34 s、'
            '14324 tok 得 20.26/20.34 s，与 auto 的 11.80/11.26 与 20.25/20.36 完全一致（差 0.1-0.5%）；'
            '而 <=4.3K 仍明显更慢。原"8K 8.69 s（-26%）"是三点线性拟合外推，实测不成立：'
            '=0 的曲线在 4K 后上弯（4.3K->7.2K 边际 1.69 ms/tok，比 auto 的 1.32 还差）。')
    f[10] = '撤回：任何长度都不赢，生产维持 auto / 3072（原"长文档切 =0"建议作废）'
    lines[k] = '\t'.join(f)
    n += 1
assert n == 1, n

row = ['P200', 'MEASUREMENT',
       '三段式线性拟合不许外推到取样区间 2 倍以上（否则会得出反向结论）',
       '测量规矩',
       'measurement', 'CONFIRMED', '—', '—', 'P199/P190',
       'P199 的教训：只用 1151/2213/4345 三点拟合出 auto=1.20s+1.316ms/tok、=0=4.74s+0.493ms/tok，'
       '按此外推 8K 得 8.69 s（-26%），实测 7.2K 是 11.68 s，方向反了。'
       '机理：=0 的曲线在 4K 后上弯，边际从 0.493 变 1.69 ms/tok ⇒ 拟合只在区间内有效。'
       '做法：任何"边际速率/每 token 成本"型结论，外推前必须在取样区间的一半与两倍处各补一个实测点。',
       '已作为硬规矩执行']
assert len(row) == len(head)
lines.append('\t'.join(row))
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines))
for l in lines[-2:]:
    f = l.split('\t')
    print(f[0], '|', f[5], '|', f[2][:52])
