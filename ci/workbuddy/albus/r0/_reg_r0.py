import io, shutil, time

REG = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
shutil.copy2(REG, REG + '.bak_w790_' + time.strftime('%Y%m%d_%H%M%S'))

lines = io.open(REG, encoding='utf-8-sig').read().splitlines()
header, body = lines[0], lines[1:]
out, hit = [], {'P97': 0}

for ln in body:
    f = ln.split('\t')
    assert len(f) == 11, (len(f), f[0])
    if f[0] == 'P97':
        f[3] = 'schedutil 更优 -2.3%(实测) / performance 为历史'
        f[9] += (' 【W790 实测 2026-10-25 14:10-14:19，同进程交错 A/B，3 对】'
                 'performance 47.28/46.04/47.03（中位 47.03）vs schedutil 46.72/45.68/45.94（中位 45.94），'
                 '**三对全部同向，-2.3%**；hc_down -3.1%、hc_up -2.0%、gemv -2.6% 同步下降。'
                 '切换 governor 不需要重启引擎（`tee /sys/.../scaling_governor`），所以这组是同进程、同页缓存、逐轮交替。')
        f[10] = ('已量化：schedutil 比 performance 快 2.3%。把 W776 遗留的 performance 改回 schedutil **不是回归而是改善**；'
                 '现存 performance 时代基线（P91 46.35、W788 51.58、R5 53.17/53.02）偏悲观约 2%')
        hit['P97'] += 1
    out.append('\t'.join(f))

assert hit['P97'] == 1

rows = [
    '\t'.join([
        'P98', 'decode', 'schedutil 三档基线（R0）', 'S/M/L', 'measure', 'REFERENCE', '', '', '',
        ('【W790 实测 2026-10-25 13:56-14:08，0.2.4/0.1.49.2，去 resident，HC_Q8=1，governor=schedutil】'
         'M（97 窗口）：total 47.19 / 47.51，hc_down 3.60-3.62，hc_up 3.51-3.53，gemv 6.09-6.11，router 3.81-3.87，'
         'attn 3.34-3.36，专家流 10.35-10.55。S（97 窗口）：46.50（另一次 48.29 为第 1 次偏冷）。'
         'L（16 窗口）：46.90 / 47.68，attn 4.98（显著高于 M 的 3.35）。'
         '**协议要求**：重启后第 1 次请求专家流 17.44（稳态 10.3），第 2-3 次 47.5/47.2，'
         '而同一配置在第 4-9 次为 45.7-46.7 => **必须丢弃重启后前 2 个请求**，否则基线偏高约 3%。'),
        ('R0 完成。当前唯一有效的对照基线；比 performance 时代的 P91 低约 2%（governor）+3%（预热），两者叠加解释了旧数字'),
    ]),
    '\t'.join([
        'P99', 'decode', 'HC_Q8 复核 + up 的结构余量', 'HC_Q8=0 臂', 'container', 'REFERENCE', '', '', '',
        ('【W790 实测 2026-10-25 14:21-14:27，zero-code 单臂，丢弃 2 请求后 M×3】'
         'HC_Q8=0：total 47.38/47.45/47.68（中位 47.45），hc_down 3.47，**hc_up 2.96**，**hc_norm 1.54**，gemv 6.13，slots 9732。'
         '对照 HC_Q8=1（P98，同 governor）：total 45.94，hc_down 3.47，hc_up 3.44，hc_norm ~0.58，gemv 5.92，slots 9901。'
         '=> ① HC_Q8=1 更优（-3.2% 墙钟且 +169 槽），P78 成立；② **hc_down 对表示法完全不敏感**（int8/bf16 都是 3.47），'
         '所以 down 的 9 倍差不是带宽/精度而是内核效率，换量化不解决；'
         '③ `up` 在 Q8 关时快 14%，机制是 `fused_gr.cu:1321 if (fast && !q8w) gr_up_fast_kernel` —— '
         '该"消掉依赖链"的内核被 `!q8w` 排除（`gr_fast()` 在 HIP 下默认 true）。补 Q8 支持理论收益 -0.48 ms（-1.0% 墙钟）。'),
        ('R5 目标由 down 改为 up：判据 hc_up 3.44 -> <=3.10（-10%），且 hc_down/total 不劣化；down 暂不排（需 profiler）'),
    ]),
]
out.extend(rows)
io.open(REG, 'w', encoding='utf-8', newline='\n').write(header + '\n' + '\n'.join(out) + '\n')
print('register updated: P97 + P98 + P99; rows=%d' % (len(out) + 1))
