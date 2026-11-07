# -*- coding: utf-8 -*-
"""Append P198: TTFT baseline + the MMQ prefill factor (and the PREFILL_MMQ=0 footgun)."""
import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')

row = ['P198', 'MEASUREMENT',
       'TTFT 基线：1.20 s + 1.316 ms/token（760 tok/s）；prefill 走 MMQ 值 64%',
       '基线口径，不改配置（但 PREFILL_MMQ 不得设 0）',
       'measurement', 'CONFIRMED', '—', '—', 'P103/P104/P112/P113/P194',
       '不停服在生产上测（不同文本避免缓存命中，max_tokens=1，每长度 3 条，重复性 ±1%）：1151 tok 2.87 s、'
       '2213 tok 4.00 s、4365 tok 6.86 s ⇒ 拟合 TTFT = 1197 ms + 1.316 ms/token（边际 760 tok/s）。'
       '同一 7123-token prompt 再发一次 0.296 s（≈27k tok/s）⇒ 固定项是新 prompt 一次性成本。'
       'A/B STRATA_PREFILL_MMQ=0（全 FP16，其余配置相同、prompt 种子相同）：固定 3.06 s + 2.158 ms/token（463 tok/s），'
       '1151 tok 6.22 s、4365 tok 12.42 s ⇒ MMQ 值 +64% 吞吐、固定项少 1.86 s。'
       '固定项随数学路径变化 ⇒ 它是第一个 chunk 的 staging+计算，不是框架开销。'
       '另：--prefill-pipe 是层切分专用（generate.cpp:712），单卡无效。',
       'TTFT 报数口径固定；STRATA_PREFILL_MMQ 严禁设 0']
assert len(row) == len(head), (len(row), len(head))
lines.append('\t'.join(row))
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines))
print(lines[-1].split('\t')[0], lines[-1].split('\t')[5], lines[-1].split('\t')[2][:60])
