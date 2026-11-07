# -*- coding: utf-8 -*-
"""W861: 按新证据改写三行状态（X17 判否 / R19·M3 降级），只动状态列与备注前缀。"""
import io

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
src = io.open(P, encoding="utf-8").read().split("\n")
out = []
changed = []

for ln in src:
    f = ln.split("\t")
    if len(f) < 9:
        out.append(ln)
        continue
    bid = f[1]
    if bid == "X17":
        f[7] = "DONE_NEG"
        f[8] = ("**收尾判否（W861 §4）**：能力已证完（rocisa 自建→主机库 61/61→加载→`status=0`→"
                "codegen→190968 B gfx906 ELF→63 条 v_fma_mix_f32），但**收益上限 ≈0**："
                "TCL 吃的是 rocBLAS 自己那批 solution，天花板就是 rocBLAS 的调优表；"
                "而 W861 §3 证明 decode 瓶颈在 GEMV 带宽（22–75%）、不是 GEMM，hipBLASLt 优化的恰是 GEMM。"
                "格式转换逐层定位：真因是 **YAML 锚点**（原文件 21 处 `ThreadTile: &id001`，"
                "`parse_general` 遇 AliasEvent 返回 None 且不消费事件⇒状态机错位），不是 flow style 也不是 null；"
                "展开后 loader 全通，再卡在结构代差（旧 9 元素 list vs 新 12 元素 / dict schema，缺 data[11] LibraryType）。"
                "上游 `Logic/asm_full/` 里**没有 vega20/gfx906**（只有 aldebaran/arcturus/navi3x/gfx11x/gfx12x/gfx950）"
                "⇒ AMD 已放弃 gfx906 的 hipBLASLt 支持。详见 W861 §4 + W858 §7–§11")
        out.append("\t".join(f))
        changed.append("X17")
        continue
    if bid == "R19":
        f[7] = "OPEN"
        f[8] = ("**降级（W861 §1，2026-11-01）**：时间加权账否决了原排序 —— 0–128 档 766 条（14.3%）"
                "只占 read 时间的 **1.2%**、总时间 3.3%；「每 token 贵 9.5×」的倍数对，但乘上 30030 个 read token "
                "就微乎其微（64K+ 档是 8087886 个，269×）。⇒ 压到 0 也只省 1.2%，**不再单独占停服**。"
                "原有观察仍成立：" + f[8])
        out.append("\t".join(f))
        changed.append("R19")
        continue
    if bid == "M3":
        f[7] = "OPEN"
        f[8] = ("**降级（W861 §2）**：decode ms/token 在 19.0–25.1 之间、**不随上下文长度变化**"
                "（65 倍 ctx 差 <5%）⇒ 瓶颈不在 KV 读取，int8 KV 对 decode 无收益。"
                "只保留「prefill 代价」这一个评估角度，不再当作 decode 手段。原文：" + f[8])
        out.append("\t".join(f))
        changed.append("M3")
        continue
    out.append(ln)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("changed:", changed)
