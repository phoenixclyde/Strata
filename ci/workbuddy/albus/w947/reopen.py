# -*- coding: utf-8 -*-
"""W947: global backtrack — a row closed on measurement-of-something-else (ISA/PMC/source reading) is NOT a
closed experiment. Reopen R60/R63/R84/R89 until each arm has actually been RUN."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

NOTE = {

"R60": (" 【W947 全局回溯 2026-11-04 15:4x｜重开】**依据不合规**：W942 用 PMC 测出 VALUBusy 67.1%（A 级），"
        "但 stream-k 的二进制**从未在本机跑过**（W906 只做到单编 rc=0）。「VALU 忙 ⇒ stream-k 无用」是推断，不是实测。"
        "按机主 2026-11-04 定的规矩：**没有实测数据不得关闭**。最低结题：实验树把 gcn 表 11 行翻 stream_k=true → 换对象重链 → "
        "32K/64K 各 3 rep（0 reused）+ KL 门（<=0.005，分辨率 0.0032）。"),

"R63": (" 【W947 全局回溯 2026-11-04 15:4x｜重开】**依据不合规**：W943 的 ISA 计数（v_readlane<=0.4%、s_load_dword=2）"
        "只说明「按现有代码没有可搬运的 lane 值」，没有证明「把地址算术 hoist 到 SGPR 之后不变慢/变快」——R51 的先例恰恰是"
        "推断很漂亮、实测慢 6-10%。必须跑：改 mmq-load-tiles 的 q5_1/q4_k 取数为 readfirstlane + 预计算偏移，A/B。"),

"R84": (" 【W947 全局回溯 2026-11-04 15:4x｜重开，并升级为交付项（机主明确要）】**依据不合规**：W943 用「kernel ISA 里 dot4 占 30%」"
        "× Amdahl 算出 -2.05% < 门，判否；**dot8 的二进制从未存在过**（W909 只在探针里验证过 i4xi4 的语义与吞吐）。"
        "机主要「移植一个出来」⇒ 本条按 INFLIGHT 执行，交付物是能跑的内核 + ISA 断言（v_dot8>0 且 v_dot4 减半）+ KL + A/B。"),

"R89": (" 【W947 全局回溯 2026-11-04 15:4x｜重开】**依据不合规**：W946 只用源码阅读证明 `qsa_prompt_attn` 是 gather-only（D 级证据，"
        "虽强但不是实测）。必须跑：同一 prompt 在 depth 1x / 3x / 6x selection 下的 `qsa attn` 绝对 ms —— "
        "若 gather-only，core 部分应恒定；若随 depth 涨，说明还有全量扫描。"),
}

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] in NOTE:
            f8[6] = "0"
            f8[7] = "INFLIGHT" if f8[1] == "R84" else "OPEN"
            f8[8] += NOTE[f8[1]]
            changed.append(f8[1])
            ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("reopened:", changed)
