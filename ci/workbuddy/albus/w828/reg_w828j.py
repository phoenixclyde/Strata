# -*- coding: utf-8 -*-
"""Append P196 (adapt tier off rejected) / P197 (Q3_K_XL cost-benefit, deferred)."""
import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')

rows = [
    ['P196', 'ENGINE',
     '关掉自适应层（--adapt-swaps 0）：慢 4-6%，自适应层是赚的',
     '不采纳（维持 --adapt-every 4 / --adapt-swaps 96）',
     'engine', 'REJECTED', '—', '—', 'P184/P188/P194',
     '4 臂 ta/tm/tm/ta（各 3 条 512-token，ms/window）：ta 46.28、tm 44.52（-3.8%）、tm2 43.49（-6.0%）、ta2 45.48；'
     '两臂方向一致且都低于两次基线。机理：关掉后 VRAAM 命中/层-窗口 20.3→14.3、'
     'CPU 专家/层-窗口 0.61→2.93（+380%），省下的 swap 开销远不够付 host 计算。'
     '顺带纠正前提：稳态 adapt wait 只有 0.11 ms/窗口（首请求 1.5 ms 是冷启动），上一轮读到的 1.4-2.4 ms 是含冷启动的臂均值。',
     '默认值正确，不改'],
    ['P197', 'QUALITY',
     '换 UD-Q3_K_XL：约 +6% decode，代价是 KL 翻 2.3 倍，且专家路径支持未验证',
     'DEFERRED（不建议）',
     'quality', 'DEFERRED', '—', '—', 'P193/P194/P195',
     '家底（native_experts.txt + conversions.json，类型 id 按 ggml.h:389-429）：专家载荷 77.0 GB = 111.3 GB 的 69%；'
     '单专家 3.07 MB（Q4_K/Q5_1）到 3.93 MB（Q5_K/Q8_0）；每窗口读 ~3.9 GB，对应 VRAM hits 10.51 ms ⇒ ~375-400 GB/s'
     '（MI50 HBM2 峰值 1 TB/s 的 37-40%）。换 Q3_K_XL（111.3→90.0 GB，专家约 -27%）：专家读取 10.51→~7.7 ms，decode +6%。'
     '质量（Unsloth 官方 KLD 表）：top-1 92.3%→88.3%，KLD 0.047→0.107；叠加我们的 0.0293 后总量 0.076→0.136（+79%）。'
     '支持风险：现役专家类型只有 12/13/7/8，Q3_K(11)/Q2_K(10) 在 Qwen 专家路径无显式分派（kQ3_K 只在 dense native_mmvq 表与 DeepSeek 引擎）。',
     '不换：+6% 换质量降一级不划算；要更快优先「更大显存」或「降上下文换 --batch」，都不动质量'],
]
for r in rows:
    assert len(r) == len(head), (len(r), len(head))
    lines.append('\t'.join(r))
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines))
for l in lines[-2:]:
    print(l.split('\t')[0], '|', l.split('\t')[5], '|', l.split('\t')[2][:56])
