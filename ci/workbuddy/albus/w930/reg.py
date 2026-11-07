# -*- coding: utf-8 -*-
"""W930: R69 结项 + R74 补一条判据 + 队列"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

# ---------- PROGRESS ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "R69":
        f[6] = "1"
        f[7] = "DONE_NEG"
        f[8] += (
            " 【W930 实测 2026-11-04 00:5x-01:2x｜零重启零编译】补丁 `ed76b12f` 156 行、"
            "**不受 HIP 宏门控**（P257 不适用）；但**它不是 opt-in**——默认就把 penalty 窗口从"
            "「prompt+回复」改成「只算回复」，`STRATA_PENALTY_PROMPT=1` 才恢复旧行为 ⇒ 移植会改默认采样。"
            "**三段证据**：①默认关闭（`SamplerParams.penalty_last_n=0`、config 无 sampling 块、"
            "`/props` 只有 temperature/top_p/top_k、模型卡 qwen4exp 的 **thinking 组没有 presence_penalty**）；"
            "②**显式传则生效**（`pp=10` 对 \"repeat yes ×20\" 只给 6 个 + \"NOPE 😂\"，`pp=0` 给满 20）"
            "——注意 `grep penalty_last_n` 得 0 **不是判据**（keys 拼进 prompt、引擎不打印）；"
            "③模型卡 instruct 的 1.5 是否自动注入**测不出**（1.5 太弱抑制不了那个重复）。"
            "**两个症状都不复现**（instruct + 贪心）：抄写 12 位十六进制串 **0/9 错**（含 pp=10）；"
            "新任务返回旧答案 **0/9**（pp=10 只导致输出崩坏，不是旧答案）。"
            "**不复现的原因**：上游是 P100+**IQ2_XS**、R9700+**IQ3_S**（2–3 bit、32/16 seeds），"
            "我们 Q4_K/Q5_1 + 贪心 ⇒ 差距在模型有效能力，不在引擎逻辑；且上游自报 reply-only 的质量是 "
            "**56/55 → 55 → 54（持平或略降）**，不是质量改进。"
            "**⇒ 不移植**：改默认行为只带来风险。**保留条件**：换 IQ2/IQ3 或更小模型、或 W4A4 进生产、"
            "或用户报告「新任务返回旧答案」时，重测 W930 §3.1/§3.2（各 3×3 请求约 2 分钟）"
        )
        lines[i] = "\t".join(f)
        print("R69 -> DONE_NEG")

    if f[1] == "R74":
        f[8] += (
            " 【W930 补判据 2026-11-04 01:2x】#4590 的复现条件是 **2–3 bit 权重（IQ2_XS/IQ3_S）**，"
            "我们 Q4_K 下 0/9 不复现。若 W4A4 把有效精度推向那一侧，**R74 必须加一条正确性门**："
            "W930 §3.1（长十六进制串抄写 3 rep）与 §3.2（新任务是否返回旧答案 3 rep），"
            "各约 2 分钟、零重启。这条此前不在 R74 判据里"
        )
        lines[i] = "\t".join(f)
        print("R74 note appended")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))

# ---------- W832 队列 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 01:2x 修，`W930`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69（penalty 窗口："
            "机制在、症状 0/9 不复现，低精度才有）~~ → **R70** → **R65** → **R74**（W4A4 精度门；"
            "已加正确性门 W930 §3.1/3.2） → R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))
print("done")
