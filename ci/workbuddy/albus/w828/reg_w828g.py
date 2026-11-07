# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P192\t') for l in body)

new = '\t'.join([
    'P192', 'CONCURRENCY', '--batch 2：等待账算完，不可摊薄', '不采纳', 'concurrency', 'REJECTED', '—', '—', 'P191/P187',
    '代价实测：`filling the GPU\'s expert cache (7463 → 5447 experts, 21.79 → 15.88 GiB)`，槽位 **−27%**（与每 slot 2.95 GiB 的预测一致）。单流 44.37 tok/s（基线 45-47，−3~5%）。双流（两请求同时，各 512 token，3 轮）：25.75+25.15=**50.9**、25.41+23.77=**49.2**、24.67+23.00=**47.7**，中位合计 **49.18**，**只比单流高 5-8%，远非 2 倍**；每流 22 → **40 ms/token（+82%）**。',
    '**机理**：并发只能共享"每窗口读一次"的 dense 权重 / shared expert / head；我们的 77% 等待在**专家读取**上，K=10 路由、512 专家，两请求每层专家集合交集期望 `10×10/512 ≈ 0.2` 个，而每层 VRAM 命中 21.4 个 ⇒ **跨请求共享率 ~1%**。上游 +31~39% 是 dense 主导的小模型/短上下文。⇒ 77% 的等待既不能靠省算力绕开（P191），也不能靠并发摊薄（本条）；这台机器在 262144 上下文 + UD-Q4_K_XL + 32 GB 三个约束下已接近性能边界。',
])

rows2 = []
for l in body:
    c = l.split('\t')
    if c[0] == 'P187':
        c[10] = c[10] + ' ｜ **P192 更正**：本条"`--batch 2` 也要 5.9 GiB（槽位 −28%）"只算了 VRAM 账；等待账实测后结论不变（双流合计仅 +5-8%、每流 +82% 延迟），但理由换成"专家读取跨请求共享率 ~1%"。'
        l = '\t'.join(c)
    rows2.append(l)

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(rows2 + [new]) + '\n')
print('rows', len(rows2) + 1)
