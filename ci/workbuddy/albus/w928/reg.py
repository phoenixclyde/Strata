# -*- coding: utf-8 -*-
"""W928: 修正 R74 的 Amdahl 覆盖面、提级 M3、加方法纪律。"""
import io, os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy")
D = os.path.abspath(D)

# ---------- 1. PROGRESS: R74 修正 + M3 提级 ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")

for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "R74":
        f[2] = ("W4A4 精度门（先用离线模拟，不动内核）：int4 激活量化 vs Q8_1 的 KL / top-1；"
                "过门才谈 dot8 工程")
        f[3] = "W928 §3/§6；W927"
        f[8] += (
            " 【W928 修正 2026-11-04 00:4x】①**覆盖面算错了**：W927 用 MMQ 整体 34.6% 算上限，"
            "但 dot8 只覆盖 gate/up（Q4_K，47/48 层）= **20.4% of prefill**，down 的 Q5_1/Q8_0 "
            "位宽 5/8 bit 塞不进 i4 ⇒ 上限从 5.5% 修正为 **3.22% 端到端**（= 噪声门 3.2%，刚好压线）。"
            "②**不是二选一**：W4A4 是「激活精度档位」，dot8 是「指令」，两者正交；而且可按张量类型混合"
            "（gate/up 走 dot8、down 保持 dp4a），MMQ 本来就是每类型一个编译实例（`DECL_MMQ_CASE`）。"
            "证据：我们树里 `mmq_nvfp4_w4a4.cu` 与 `mmq_nvfp4_w4a8.cu` **两个 TU 并存**"
            "（`CMakeLists:2169/2214`），靠一句 `#define blackwell_mma_available(cc) false` 切换档位。"
            "③**先验**：上游自己的 W4A4（NVFP4/E2M1）自述 *the first token's distribution drifts by "
            "KL 0.0004-0.03 from the exact FP16 prefill (8 prompts)* ⇒ 跨两个数量级，我们的门是 0.005，"
            "**五五开**。④做法改为：先用离线模拟（XOR+修正项已位精确，量化器可离线复现）算 KL，"
            "**过门才动内核**——省掉一次编译+重启")
        lines[i] = "\t".join(f)
        print("R74 updated")

    if f[1] == "M3":
        f[2] = ("k8v8 的 prefill 代价核对（`--kv int8`；K 与 V 都 int8，KV_MODE 1）"
                "——零代码，只换一个 CLI 参数")
        f[7] = "OPEN"
        f[8] += (
            " 【W928 提级 2026-11-04 00:4x｜提到 R74 之前】机主问「那 k8v8 呢」——核实："
            "**k8v8 就是 `--kv int8`**，`generate.cpp:3835` 白名单 `fp16/int8/q4_0/k8v4` 里没有 k8v8 这个名字；"
            "源码 `qsa_prompt_attn.cu:89` 写明 `KV_MODE 1: int8 codes + fp16 scale per 64 values`（K 和 V 都 int8）。"
            "**已有账（P04/P50/P247）**：1056 vs 816 B/cell（+29.4%）、省 3.8 GiB ≈ 1700 专家槽、"
            "decode **−7.7~−16.6%**、**质量 KL 0.0416 优于 k8v4 的 0.0704**；且 `AUDIT21/C5` 已澄清 "
            "k8v4 的采纳理由是「省 3.8 GiB」不是「质量已证」。**未核的一半**：k8v4 的 V 是 q4_0、"
            "gather 时**反量化成 fp16**（多一次 4-bit 解包 + scale），int8 的 V 是 int8、少这一步但多读 29.4% 字节 "
            "⇒ prefill 净效应从未量过。**做法**：`--kv int8` 一次重启，同 prompt 比 "
            "`strata prefill timing: qsa attn` 绝对毫秒与 `qsa proj`；判据 |Δ| ≥ 2×CV。"
            "**为什么排前面**：①零代码、只改一项 config；②它可能「免费」——质量更好 + prefill 可能更快，"
            "代价仅是显存；③它决定 R74 该不该继续：若 int8 的 attention 明显更快，说明 V 的 q4 解包是真成本，"
            "dot8 的「少解包」先验变强；若无差别，说明 attention 早已带宽受限，dot8 的 3.22% 更没戏")
        lines[i] = "\t".join(f)
        print("M3 promoted")

io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("PROGRESS written")

# ---------- 2. W832: 方法纪律 + 队列 ----------
q = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(q, encoding="utf-8").read()

anchor = "> **执行顺序（2026-11-04"
rule = (
    "> **方法纪律追加（`W928` 2026-11-04 00:4x）**：⑥报「某优化能覆盖多少」时，必须逐项核对"
    "**它的作用对象**（张量类型 / 位宽 / 相位 / 子系统），**不能用子系统总量代替它实际能碰到的量**"
    "（本轮实测：dot8 只覆盖 gate/up 的 Q4_K = 20.4% of prefill，而错误口径用了 MMQ 整体 34.6%，"
    "上限虚高 1.7 倍）。⑦**「档位」与「指令」是两个维度**：精度档位（W4A4/W4A8/fp16）由量化器决定，"
    "指令（dot8/dp4a/FMA）由位宽决定，二者正交且**可按张量类型分别设**——凡出现「A 或 B 二选一」的表述，"
    "先检查是不是把两个维度压成了一维。\n>\n"
)
assert anchor in s, "anchor not found"
s = s.replace(anchor, rule + anchor, 1)

# 队列行：把 M3 提到 R74 前
old_q = "~~R64~~ → **R69** → R70 → R65"
new_q = "~~R64~~ → **M3**（k8v8 的 prefill，零代码） → **R74** 精度门 → R69 → R70 → R65"
if old_q in s:
    s = s.replace(old_q, new_q, 1)
    print("queue reordered")
else:
    # 找实际队列行
    for ln in s.split("\n"):
        if "执行顺序" in ln:
            print("ACTUAL:", ln[:220])

io.open(q, "w", encoding="utf-8").write(s)
print("W832 written")
