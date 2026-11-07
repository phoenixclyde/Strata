# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P193\t') for l in body)

new = '\t'.join([
    'P193', 'QUALITY', '数值债 8 项叠加的总量：KL 0.0293（底噪 0）', '8 项结清', 'quality', 'CONFIRMED', '—', '—', 'P171/P158/P184',
    '口径 W824 §10（STRATA_LOGPOS + LOGPOS_TOPK=64 → kl_prop 配对 KL），硬前提 `STRATA_PREFILL_CPU_SHARE=0`。三臂同引擎同 8 prompt 顺序：E0 生产全量（k8v4/RT_SKIP=7/PROMPT_F16=1/SELECT_SIMT=1/HC_Q8=1）、E0b 同 E0、Eall 最小近似（fp16/0/0/0/0）。**底噪逐字节为 0**：E0r 与 E0br 的 md5 完全相同（f224eccc…，各 48 行）。45 个共同位置：E0‖Eall **KL mean 0.0293**、median 0.0001、argmax 一致 **97.8%**、top-10 重叠 **0.85**、mean|Δlp_tgt| 0.13327；E0b‖Eall 完全相同。',
    '落在 0.02-0.05 区间 ⇒ 不必立刻二分，记账即可。median≪mean 说明一半以上位置几乎不动、代价集中在少数位置。对照上游单 RT_SKIP 的 0.003-0.006，8 项叠加是它的 5-10 倍，量级自洽。口径提醒：E0 已是 UD-Q4_K_XL，0.0293 是"4-bit 之上再加的近似"，不是相对 fp16 模型的偏差。**这一项结清**；要压它先二分 RT_SKIP 与 k8v4 各占多少（需另开两个窗口）。',
])

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(body + [new]) + '\n')
print('rows', len(body) + 1)
