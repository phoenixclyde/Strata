# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P187\t') for l in body)

new = '\t'.join([
    'P187', 'ENGINE', '16 行窗口在 262144 上下文/32 GB 上结构性不可用', '宽版编得出、跑不到', 'engine', 'CONFIRMED', '—', '—', 'P182/P180',
    '宽构建 build-028w（-DSTRATA_WINDOW_MAX_T=16）全量通过：strata 0.1.54，45,596,776 B（比窄版大 7.36 MB = 9..16 的额外实例），含 moe_grouped_s2_wide 符号 ⇒ gfx906 能编出全部宽 kernel。但 `--batch 16` 起不来：日志 `--batch 16: slot 8\'s session does not fit on CUDA0 (**2.95 GiB each**, 1.22 GiB free); 8 slots` → `--batch: 8 slot sessions ... 23.60 GiB` → `native head upload: out of memory (156 MiB of 32752 MiB free)`。每个 slot 的会话要 2.95 GiB（262144 上下文的 KV + buffer），**不是**按 k8v4×256K 估的 214 MiB。',
    '⇒ 16 行窗口本机永远用不上：solo 硬限 8 行（P182）+ batch 要 ≥9 slots 才进 9..16 行 + 9 slots 需 26.6 GiB。连带 `--batch 2` 也要 5.9 GiB（槽位 −28%），**"并发摊薄权重读取"这条路在 262144/32 GB 上没有空间**。宽版二进制留 /data/bin/strata-0.1.54w 不参与生产；若将来把上下文降到 32K（每 slot ~0.37 GiB），这条路才值得重开。',
])

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(body + [new]) + '\n')
print('rows', len(body) + 1)
