# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 01:2x W930 · R69 结项：`#4590` penalty 窗口「机制在、症状不复现」（零重启零编译）
- **补丁**：`ed76b12f` 156 行 / 5 文件，核心是 `sampler.hpp` 的两个 inline 函数；**不受 HIP 宏门控**（P257 不适用）。**关键：它不是 opt-in** —— 默认就把窗口从「prompt+回复」改成「只算回复」，`STRATA_PENALTY_PROMPT=1` 才恢复旧行为 ⇒ 移植会改默认采样。
- **penalty 在我们部署开不开（三段证据）**：①**默认关闭** —— `SamplerParams.penalty_last_n=0`、config 无 `sampling` 块、`/props` 只有 `{temperature 1.0, top_p 0.95, top_k 20}`、模型卡 `qwen4exp` 的 **thinking 组压根没有 presence_penalty**（只有 instruct 组有 1.5），而我们跑的就是 thinking（响应带 reasoning_content）；②**显式传则生效** —— `pp=10` 对 "repeat yes ×20" 只给 6 个还写 "NOPE 😂"，`pp=0` 给满 20；③模型卡 instruct 的 1.5 是否自动注入**测不出**（1.5 太弱抑制不了那个重复）。
- **重要方法论纠正**：`grep penalty_last_n` 得 **0 不是判据** —— `keys` 是拼进 prompt 文本传给引擎的，引擎解析进 SamplerParams 后不打印。我一开始据此判「penalty 未生效」并跑出「两臂 3/3 都正确」的**假阴性**，后来用极端值（pp=10 的行为差）才验明。
- **两个症状都不复现**（instruct + 贪心）：①抄写 12 位十六进制串 `7F3A9C21DE4B` —— pp=0/1.5/**10** 全部 **9/9 一字不差**；②新任务返回旧答案（turn1 JSON 配置 → turn2 写 Python 函数）—— pp=0/1.5/**10** 全部 **0/9 返回旧答案**（pp=10 只导致输出崩坏 `defadd(aba+breturna+ba+a-a-bb...`，即 penalty 过强的退化，不是旧答案）。
- **不复现的原因不是运气**：上游复现条件是 **P100+IQ2_XS（2-bit）** 与 **R9700+IQ3_S**、32/16 seeds；我们 **Q4_K/Q5_1 + 贪心**。penalty 确实在打 prompt 尾部（pp=10 的崩坏证明了），但 Q4_K 模型有余量在被打压后仍选对，IQ2_XS 没有 ⇒ **这是低精度场景的 bug**。且上游自报 reply-only 的质量是 **56/55 → 55 → 54（持平或略降）**，不是质量改进。
- **⇒ R69 = DONE_NEG，不移植**：机制在但症状 0/9，改默认行为只有风险没有收益。**保留条件**：换 IQ2/IQ3 或更小模型、W4A4 进生产、或用户报告「新任务返回旧答案」时，重测 W930 §3.1/§3.2（各 3×3 请求约 2 分钟、零重启）。
- **对 R74 的新判据（此前缺失）**：既然这类 bug 只在低精度显现，**W4A4 若推向生产必须重跑这两个正确性测试**。已补进 R74 备注。
- **生产零改动**：无重启、无编译、无 config 变更，只发了约 40 个 instruct 短 prompt 请求。`/health ok`、restarts=0、config `51ef8837`、engine `a97f4479`。
- **队列**：`~~…~~ → ~~M3~~ → ~~R69~~ → **R70** → **R65** → **R74**（已加正确性门） → R49 → R50 → R30′`。进度 **158 条 / 96 已结 = 60.8%**，主线 **130 / 96 = 73.8%**。
- 产物：`deploy/W930_R69_PENALTY_WINDOW.md`；`PROGRESS.tsv` R69(DONE_NEG) + R74 备注；`W832` 队列；探针 `albus/w930/{repro,pp_effect,card_effect,hex,oldtrap}.py`。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
