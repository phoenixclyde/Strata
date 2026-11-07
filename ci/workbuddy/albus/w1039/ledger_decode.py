import io

P = "deploy/PROGRESS.tsv"
rows = [
    ("B1参数轴", "P482",
     "decode 的真实分解（400 个窗口样本）：verify 90.3%（GPU 69.4% + host 13.6%）、**draft 只占 5.1%**；而 host 里 **CPU 专家占 86% = 全窗 11.7%**（p90 17.11 ms = 43%）⇒ decode 有一半是 CPU 侧的账",
     "W1039", "count", "1", "1", "DONE",
     "**数据**：`STRATA_DECODE_TIMING` 已在产，日志 `strata decode timing:` 行共 400 条（`albus/w1039/decode_timing.txt`）。中位："
     "**39.76 ms/窗**、1.00 tokens/窗（⚠ 这是被采样到的那些请求，含 128-token 生成）＝ 25.2 tok/s；"
     "verify **35.89（90.3%）** 其中 GPU-reach **27.59（69.4%）**、per-layer host **5.43（13.6%）**、stage 0.09；"
     "**draft 2.04（5.1%）**、adapt wait 0.11、commit 0.04。"
     "**host 内部**：plan 0.17 + actq 0.18 + jobs 0.04 + **CPU 4.64**（占 host **86%**，占全窗 **11.7%**）；CPU 的 p10/p50/p90 = **0.00 / 4.66 / 17.11 ms** ⇒ **双峰**：一部分请求完全不碰 CPU 专家，一部分被它吃掉 40%+ 的窗口。"
     "**⇒ 三条结论**：① 草稿流优化（DRY/优先级）天花板只有 5.1%；② **decode 的第二个大项是 CPU 专家（11.7%，尾部 43%）**，它由「缓存装不下的专家」驱动，所以**加槽（`R104`）不只是不加分项，它直接把这一项往下压**；③ 任何「decode 已到地板」的说法要限定在 GPU 段。",
     "P424;R104", "KW:decode 分解|CPU 专家|双峰"),

    ("B5本机缺口", "P483",
     "两个新旋钮按判据提前否掉/降级：`STRATA_MTP_HIP_PRIO` 天花板 5.1%（现实 2–6%）**不值得单独开窗**；`STRATA_HIP_QUEUE_PRIME` 在我们自己的数据里**没有可重复的首请求惩罚**（中位 +0.23%）",
     "W1039", "count", "1", "1", "DONE",
     "**MTP 优先级**：draft 占窗口 5.1% ⇒「draft→0」是 5.1% 上限；照 R9700 外证（5.8→3.5 ms/窗，−2.3 ms）在 39.76 ms 的窗口上折 **5.8%**，照比例（−40%）只有 **2.1%**。decode 的 2×CV 常年在 5–8% ⇒ **单独为它开窗不划算**，只能搭车。**候选 `hipk` 保留，不排窗口。**"
     "**queue prime**：拿 18 个 arm 文件、42 组「同 target 首个 vs 其余」比对，首请求偏差 **中位 +0.23% / 均值 +1.41% / p90 +5.54%**，>0.5% 的只占 36% ⇒ **没有系统性惩罚**，右尾是噪声。"
     "**诚实的边界**：这组数据前面都有 warm-up，**测不到「重启那一刻的队列落位」**；要测那个，只能用窗口里重启后第一条实质请求。所以结论是「没有可重复的首 target 惩罚」，不是「队列落位一定不存在」。",
     "P481;P482", "KW:天花板|首请求|搭车"),
]
lines = io.open(P, encoding="utf-8").read().splitlines()
for r in rows:
    assert len(r) == 11
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", ", ".join(r[1] for r in rows))

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**424 条 / 已结 337 / 79.5%**", "**426 条 / 已结 339 / 79.6%**", 1)
a = "三处可选开关已解开并建候选 `hipk`=`67ab8836`，三个 env 只在它里面，默认不变）** "
b = ("三处可选开关已解开并建候选 `hipk`=`67ab8836`，三个 env 只在它里面，默认不变；"
     "**`MTP_HIP_PRIO` 天花板 5.1% 判不单独开窗、`QUEUE_PRIME` 无首请求惩罚（`P483`）**）** ")
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: denom + R105 state")
