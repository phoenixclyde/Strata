# -*- coding: utf-8 -*-
"""Append P199: prefill CPU share is a curve pair with a ~4.3K crossover."""
import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')

row = ['P199', 'PREFILL',
       'STRATA_PREFILL_CPU_SHARE 是两条曲线：auto=1.20s+1.316ms/tok，=0=4.74s+0.493ms/tok，交叉 ≈4.3K token',
       '按用途选：对话维持 auto/3072；长文档(>=5K)临时置 0',
       'prefill', 'CONFIRMED', '—', '—', 'P198/P124/P193',
       '同日同 prompt 种子，只改一个 env：auto/MAX3072 → 1151 tok 2.87 s、2213 4.00 s、4345 6.86 s，拟合 1197 ms + 1.316 ms/tok（760 tok/s）；'
       'CPU_SHARE=0 → 5.42 / 5.46 / 6.87 s，拟合 4743 ms + 0.493 ms/tok（2029 tok/s）。交点 (4743-1197)/(1.316-0.493) ≈ 4308 token。'
       '8K 拟合：11.7 s vs 8.69 s（-26%）。机理：=0 时先做一次 PCIe 搬运（并集 94 GB - 缓存 21.8 GiB ≈ 72 GB，72/4.74 ≈ 15 GB/s，'
       'PCIe 3.0 x16 实测带宽），之后每 token 纯 GPU 算；auto 不搬运，固定项只有 1.20 s，但每 token 被 CPU 拖到 760 tok/s。'
       'auto 不会按长度自己切换（1151 与 4345 行为一致）。质量：CPU/GPU 舍入不同，share 一变答案可能变（P124），长文档用前须过 KL 门。',
       '对话场景不动；长文档手动切 =0']
assert len(row) == len(head), (len(row), len(head))
lines.append('\t'.join(row))
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines), '|', lines[-1].split('\t')[0], lines[-1].split('\t')[5])
