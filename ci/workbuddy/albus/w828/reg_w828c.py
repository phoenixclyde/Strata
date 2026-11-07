# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr, body = rows[0], rows[1:]
assert not any(l.startswith('P188\t') for l in body)

old_ev = '**我们 ABBA 两轮复测 46.10/47.00 vs 47.80/46.80 ⇒ +1.6%，逐对 +3.7%/−0.4% 方向不一致 ⇒ 不采纳**'
new_ev = ('**两轮复测均否**：第一次（128 token，错）46.10/47.00 vs 47.80/46.80 = +1.6% 方向不一；'
          '**第二次（512 token + ms/window，见 P188）ta 39.80/38.78 ms vs tb 41.42/39.61 ms ⇒ tb 慢 4.1%/2.1%，两对同向**')

out = []
for l in body:
    c = l.split('\t')
    if c[0] == 'P184':
        assert old_ev in c[9], 'P184 evidence text changed'
        c[9] = c[9].replace(old_ev, new_ev)
        c[10] = '采纳：无参数变更（现值即最优）。⑤`STRATA_SH_STREAM` 是唯一还未复测的项。'
        l = '\t'.join(c)
    out.append(l)

new = '\t'.join([
    'P188', 'MEASUREMENT', '机制类参数复测规矩：512 token + ms/window + 机制计数器', '--adapt-* 否', 'measurement', 'ADOPTED', '—', '—', 'P184/P185/P175/P186',
    '`--adapt-*` 专项复测（ta/tb/tb/ta，各 3 条 512-token 贪心）：ms/window 中位 ta 39.80 / 38.78，tb 41.42 / 39.61 ⇒ **两对都是 tb 慢（4.1% / 2.1%）**；tok/s 44.17/45.37 vs 42.10/45.77（方向不一，印证 tok/s 不可信）。机制计数器 `swaps/window` 两臂 3-16 抖动、**无系统差异** ⇒ 我们的命中率已 95.1-97.4%，每轮可换候选只有约 14 个，`--adapt-swaps 80` 空转。内存实测 4 条 DDR4-2133 四通道（DIMM_A1/B1/C1/D1，dmidecode）≈68 GB/s，CPU 算 miss 专家没那么贵。上游 +7.9% 是 DDR3 ~24 GB/s 上的结论。',
    '**规矩定死**：(1) 跟随对话类机制参数必须用 ≥512 token 生成（上游 calibrate 自述 128 token 只得 +0.7%）；(2) 判据用 `STRATA_DECODE_TIMING` 的 ms/window（同臂 3 样本 ±3%）而不是墙钟 tok/s（同批漂 12-16%）；(3) 先看机制计数器（swaps/window、命中率）确认它真的动了，再看速度。第一次复测只看到 +1.6% 就下结论，正是漏了这三条。',
])

open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(out + [new]) + '\n')
print('rows', len(out) + 1)
print([l[:80] for l in out if l.startswith('P184')])
