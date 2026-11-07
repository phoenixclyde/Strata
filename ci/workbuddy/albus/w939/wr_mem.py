#!/usr/bin/env python3
import io
sec = """
## 13:0x W939 · 源码任务审计：5 条「算出来的否定」全部重开
- **触发**：机主「梳理前天到现在涉及源代码的任务，说明处理与依据；没有本地实测依据的统统重开」。
- **分级尺**：A 本机实测（编译/部署后 A/B、KL、注入、硬件实跑）/ B 本机离线实测（ISA 计数、微基准、单编）/ C 推算（Amdahl、容量换算、噪声门）/ D 阅读。**只有 A，或 B + 已有的 A 先例，才允许写「不做」；C 一律重开。**
- **重开 5 条**（依据级别 C 或无数据）：**R60** stream-k（只有 ki 外部实测 + 我们 ISA 反推的 VALU 81%，`stream_k=true` 的二进制从未跑过）；**R61** PMC（三次注入静默失败 = 没测到）；**R63** readfirstlane（Amdahl 1.74%，一行代码没改）；**R64** attention int8（日志拟合 + 源码格式事实 + Amdahl，改动从未编译）；**R72** 扩 cache（容量换算 +145 槽，一次重启都没做）。
- **保留 24 条**，三条硬理由：①A 级实测（R51/R54/R55/R56/R66/R67/R68/R69/R70(以 W932 为准)/R71/R73/R75/R76/R77/R78/R82/R83）；②B + A 先例（R58：ISA 说明无段过半 + R51 实测解包会慢）；③只读任务不产出性能结论（R65 / W937）。
- **连带影响**：R60 的关闭依赖 R61 的 PMC，而 R61 无数据 ⇒ 这条推理链从一开始就没有测量支撑，两条同时重开。
- **账本**：`PROGRESS.tsv` 5 条 → OPEN、done=0；已结 104→**100**（降 4，R60 原为 CLOSED 且 done=0，本就未计入）；分母仍 167。`W832 §6.5` 加「重开区」5 行 + 依据分级规则，执行顺序改为 `R61 → R60 → R63 → R72 → R64 → R81 → R79 → R80 → R74 → R49 → R50 → R30′`。
- **R61 的新做法（不碰生产）**：独立驱动链 `libstrata_mmq.a`。已核实 `mul_mat_q_case<(ggml_type)12>`（Q4_K）是**可链接的弱全局符号 W**，`mmq_args` 是纯 struct ⇒ 可以写一个最小驱动（分配 Q4_K 权重 + Q8_1 激活 + dst），单独进程跑 `rocprofv3 --pmc` 采 VALUBusy/MemUnitStalled/FetchSize。这样既不需要注入生产、也不需要 71 GB 专家。备选：短暂停服 + `rocprofv3` 直接启动 `strata generate`（真实 shape，但 6–8 分钟停机）。
- 产物：`deploy/W939_SOURCE_TASK_AUDIT.md`（30 行逐条审计 + 5 条最低结题测量 + 保留理由）。
"""
p = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-11-04.md"
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("appended", len(sec))
