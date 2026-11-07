# -*- coding: utf-8 -*-
p = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
rows = open(p, encoding='utf-8').read().rstrip('\n').split('\n')
hdr = rows[0]
body = rows[1:]

def setcol(line, idx, val):
    c = line.split('\t')
    c[idx] = val
    return '\t'.join(c)

out = []
for l in body:
    cid = l.split('\t')[0]
    if cid == 'P178':
        c = l.split('\t')
        c[5] = 'SUPERSEDED'
        c[10] = (c[10] + ' ｜ **W828 推翻**：用户要求升上游最新 ⇒ P180 执行，本条判定的"暂不升"作废；'
                 '但"16 行窗口对我们无用"这一半**被源码证实并加强**（solo 窗口硬限 8，见 P182）。')
        l = '\t'.join(c)
    out.append(l)

new = [
    ['P180', 'ENGINE', 'engine 0.1.53 -> 0.1.54（v0.2.8）', '已升并上生产', 'governance', 'ADOPTED', '—', '—', 'P178/P181',
     'src028 = src0271 + v0.2.8 的 148 个变更文件 + 2 行 compat 补丁。全树 blob SHA 校验：本地 8012 文件里 5101 与上游逐字节相同、74 个不同（73 个不编译：.bat/.ps1/metal/dsv41/packaging/tests；1 个是**我们自己的** qsa_decode_attn.cu W794 补丁，上游 0.2.8 未改它）。构建 `strata 0.1.54`，`-DSTRATA_VERIFY_MAX_T=8`。生产 A/B：decode 45.90 → 45.74（−0.35%，噪声内），read 三档 −6.2/+3.7/+9.8%（方向不一）。serve 层同步换 0.1.54（镜像 strata-gfx906:0.2.8 = 0.2.4p4 + COPY serve/strata_control/strata_cli/tools）。',
     '升级 0 回归、0 速度收益。旧二进制 /data/bin/strata-0.1.53 保留；配置备份 *.bak-w828；回滚 = 改 exe 一行 + 镜像换回 0.2.4p4。'],
    ['P181', 'PLATFORM', 'gfx906 compat 层缺 stream priority 两宏（源码级移植）', 'strata_hip.h +2 行', 'build', 'ADOPTED', '—', '—', 'P180',
     '0.1.54 的 src/core/dflash2.cpp:205-207 直接调 `cudaDeviceGetStreamPriorityRange` / `cudaStreamCreateWithPriority`。上游 wave32 HIP 后端靠 hipify 改名，我们的 gfx906 compat（include/strata/platform/hip_compat/strata_hip.h，**手写宏表**）漏了这两个，全量构建报 undeclared identifier。这两个宏原本只存在于 include/strata/dsv41/hip_extra.h，而那个头只被 CMake 用 -include 喂给 dsv41 测试目标。0.1.53 没暴露是因为 build-0271 的 dflash2.cpp.o 比源码新、ninja 判 up-to-date 没重编（**旧账**）。',
     '补 `#define cudaStreamCreateWithPriority hipStreamCreateWithPriority` 与 `cudaDeviceGetStreamPriorityRange hipDeviceGetStreamPriorityRange`（语义一一对应）。单文件编译 51 warnings / 0 error。**可提上游**：这是 compat 层真实缺口。'],
    ['P182', 'ENGINE', '16 行窗口只属于 --batch，solo/spec 硬限 8', '—', 'engine', 'CONFIRMED', '—', '—', 'P178/P180',
     'src/program/generate.cpp 新增：`if (o.spec > kVerifyNarrowT) { "--spec %d: a speculative window holds 2..%d tokens"; return 1; }`，注释逐字 "A speculative (solo) window holds at most kVerifyNarrowT rows: the hand-offs, the penalty history and the drafters\' buffers are sized for that. Only a plain --batch forms the wider windows of a build with kVerifyMaxT > 8."。另 mtp.cpp 的 max_t 也改判 kVerifyNarrowT。',
     '⇒ 即使建 16 行宽版本，`--spec 8+` 仍被拒；想吃宽窗口只能开 `--batch`（9 行以上才有意义）。这条把 W827 的"16 行窗口不命中"从"我们没用"升级为"**结构上 solo 用不了**"。'],
    ['P183', 'MEMORY', '#4474 自动缓存留 256 MiB', '槽位 7551 -> 7463', 'engine', 'ADOPTED', '—', '—', 'P180',
     '0.1.54 的 auto_cache.hpp：`kLateAllocMib = 256`，`auto_cache_slots()` 按 `free - reserve - 256 MiB` 算槽位。实测：0.1.53 日志 `filling the GPU\'s expert cache (7551 experts, 22.04 GiB)` → 0.1.54 `7463 experts, 21.79 GiB`，正好 −0.25 GiB。decode 未见回归（−0.35%，噪声内）。',
     '采纳（跟随上游）。代价 −1.17% 槽位换真实 256 MiB 余量；命中率在 88.9-97.1% 区间正常。'],
    ['P184', 'PARAM', 'calibrate 标定结果（引擎 0.1.54n）', 'pcie-frac 0.20 已最优 / adapt 不采纳', 'param', 'ADOPTED', '—', '—', 'P177/P179',
     '跑完 tools/calibrate.py（55 min，每次重启 255 s 载入 71.73 GiB）。①`--pcie-frac`（单实例内 3 轮中位）：0:44.4 · **0.2:44.5** · 0.35:39.8 · 0.55:36.1 · 0.75:32.7 · 1.0:26.9 ⇒ **我们手选的 0.20 恰好是全局最优**，0.35 起掉 11%。②`--spec-min-p`：0.3:43.7 · 0.5:45.4 · 0.7:45.2 ⇒ 0.5 只高 0.4%，低于门槛，不动。③`--pool-workers`：默认最优（20/13=43.6, 10=42.9, 5=40.9）⇒ 不设。④`--adapt-*` 1/80/0.97：它报默认 44.8 → 49.4（+10.3%），**我们 ABBA 两轮复测 46.10/47.00 vs 47.80/46.80 ⇒ +1.6%，逐对 +3.7%/−0.4% 方向不一致 ⇒ 不采纳**。⑤`STRATA_SH_STREAM=1`：它报 40.4 → 43.5（+7.7%），**未复测，待办**。',
     '采纳：无参数变更（现值即最优）。待办：SH_STREAM 的 ABBA 复测（该项上游也说逐机不定、输出相同）。'],
    ['P185', 'MEASUREMENT', 'calibrate 的"需重启"结论必须自己 ABBA 复测', '—', 'measurement', 'CONFIRMED', '—', '—', 'P175/P184',
     'calibrate 的判据（MIN_GAIN=3% + SWEEP_ROUNDS=3 交替）只对**能在单实例内用 strata_tune 扫**的参数成立（pcie-frac / spec-min-p：3 轮中位，重复性 <1%）。对**每个值都要重启引擎**的参数（pool-workers / adapt-* / SH_STREAM）它**只测一次**，而跨容器 decode 漂 12-16%（P175/P98）⇒ adapt 的 +10.3% 在我们 ABBA 下只剩 +1.6% 且方向不稳。',
     '规则：calibrate 的"单实例内扫描"结果直接用；"每值重启"结果一律先 ABBA（≥2 对）+ 幅度 >8% 才进生产。'],
    ['P186', 'SERVE', 'serve 层 0.1.54：工具调用容错默认开', 'tool_call_recovery=True', 'serve', 'ADOPTED', '—', '—', 'P180',
     '0.2.8 的 serve/frontend.py(+242/−35) 与 server.py(+77/−13)：`tool_call_recovery` 默认 True（上游 1462 轮实测可读率 92.9%→98.3%）、`_Lenient` 读坏 JSON（尾逗号/单引号/True-False-None/裸字符串/括号未闭）、`param_end` 修 #4427（缺 `</function>`）与 #4078（值里引用了调用）、#4077（多余的 closing think 丢弃）、`end_token_ids()`（tokenizer 未命名家族时的停止 id）、`LEFTOVER_SETTLE_S=120`（#4051 服务侧等旧引擎还内存）。已随镜像 strata-gfx906:0.2.8 上生产。',
     '冒烟通过：普通对话 2.7 s；工具调用 `finish=tool_calls`，`get_weather{"city":"北京","days":[1,2]}`；日志 `writing a tool call: get_weather: 113 of max 160 tokens`。'],
]
new = ['\t'.join(r) for r in new]
open(p, 'w', encoding='utf-8').write(hdr + '\n' + '\n'.join(out + new) + '\n')
print('rows now', len(out) + len(new))
print('P178:', [l for l in out if l.startswith('P178')][0][:200])
