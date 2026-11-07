# -*- coding: utf-8 -*-
"""修正 W776 的两条核心判断（第 3 条 GPU 空转、第 5 条 3.35 GiB 可挖）。
"""
import io

P = r"D:/workbuddy_space/strata_ws/deploy/W776_TUNING_MASTER_PLAN.md"
s = io.open(P, encoding="utf-8").read()

old3 = ("3. **预填 = CPU-bound（GPU 空转），decode = GPU-bound。** 预填 105K 用 229.6 s（457 tok/s）、"
        "decode 206.5 s（GPU 94-100%）。两段各占一半墙钟，必须分别下手。")
new3 = ("3. **[2026-10-25 04:5x 修正] 预填不是「GPU 空转」。** 原文写「预填 = CPU-bound（GPU 空转）」，"
        "依据是 netdata 在 2026-10-22 那次 105K 请求上报的 `GPU 0%`。用 `rocm-smi --showuse` 每 1 s 直读复核"
        "（M 档热态，49 样本）：`100 x42 / 99 x4 / 98 x1 / 68 x1 / 0 x1`，中位 100、零值 2% "
        "=> **预填期间 GPU 与 CPU 同时满载**，是纯算力 bound（日志同时证 `file tier 0.0 GiB` 即磁盘 0 读、"
        "`PCIe 12.0 GB/s` 未饱和）。**这条修正的直接后果**：`--prefill-pipe`（重叠 I/O）与 "
        "`STRATA_PREFILL_CPU_SHARE`（借 idle CPU 池）两个方向的前提都不成立，已从队列移除（W786 §4.2）。"
        "两段的墙钟占比也需改写：prefill 占 57%（S 2.8K）/ 90%（M 21.8K）/ 99.5%（L 99K），见 W786 §1。")

old5 = ("5. **[重开] 显存侧还有 3.35 GiB 可挖，不是 214 MiB。** register `P32` 把 "
        "`262144 x 816 B = 214 MiB` 当成 KV 总量，**那只算了一层**；源码 `generate.cpp:7735` 原文是 "
        "\"the K/V of a 262K context (**3.35 GiB** with the drafter's at int8)\" => 真实可腾 "
        "**1487 槽（+15.2%）**，不是 +0.95%。这是本轮唯一被**算错**的历史结论。")
new5 = ("5. **[2026-10-25 04:5x 作废] 显存侧那 3.35 GiB 拿不到。** 原文按源码注释算出「可腾 1487 槽（+15.2%）」，"
        "但 `--kv-grow` 的门要求 `vmm_available()`，而 `src/core/vmm.cpp:158/167` 把 HIP VMM 限定在 "
        "`!defined(STRATA_HIP_GFX906)`，`:299-303` 恒返回 false（同处注释逐字点名 gfx906）。"
        "三臂实测（含去 `--resident-experts`）`expert_slots` 恒为 9901、引擎日志打出 `--kv-grow is off`。"
        "=> P32 的 214 MiB 算术确实错（816 B/cell 是每层），但结论更强：**不是收益小，是根本不可达**。")

assert s.count(old3) == 1, ("3", s.count(old3))
assert s.count(old5) == 1, ("5", s.count(old5))
s = s.replace(old3, new3, 1).replace(old5, new5, 1)

# 第 8 条补一句：这条早就指对了，但没被采纳
old8 = ("8. **一个实测事实而不是猜想**：`conversation_cache: requests_reused 0 / reused_tokens 0 / parked 2` —— "
        "4 GiB 会话缓存预算一次都没复用上，这是多轮对话体感差的直接原因。")
new8 = ("8. **一个实测事实而不是猜想**：`conversation_cache: requests_reused 0 / reused_tokens 0 / parked 2` —— "
        "4 GiB 会话缓存预算一次都没复用上，这是多轮对话体感差的直接原因。"
        "**[2026-10-25 04:5x] 这条是本方案里最早、也最被忽视的一条**：从 W776 到 W785 五个版本都把它排在队列末尾或判成"
        "「外部问题」，直到 W786 实测出「修复后 M 档第二轮 44 s -> 0.5 s」（88 倍）才升为第一。"
        "教训：**已经在手的实测事实，优先级不该低于新挖的机理**。")
assert s.count(old8) == 1, ("8", s.count(old8))
s = s.replace(old8, new8, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W776 3 items fixed")
