# -*- coding: utf-8 -*-
"""W943: close R63 (no removable instructions) and R84 (denominator fix -> under the gate)."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

R63_EV = (" 【W943 结题 2026-11-04 14:3x｜A 级】`mul_mat_q<(ggml_type)12,64,false>`（Q4_K，J=64，W942 PMC 里占 98.59% 的那个）"
          "ISA census：3,411 条指令，dot 30.0% / 地址 19.7% / 缩放 13.1% / LDS 10.6% / 解包 8.4% / 同步 6.0% / 搬运 3.1%。"
          "`v_readlane`+`v_readfirstlane`+`v_writelane` 全部在 top-25 之外（<=15 条、<=0.4%）、`s_load_dword` 仅 2 条 ⇒ "
          "readfirstlane hoisting **无可消项**（地址本来就在 SGPR/常量）；`global_load_dword` 40 + `buffer_load_dword` 10 已是常量偏移形态、"
          "`ds_read2_b32` 304 条说明 LDS 已双通道 ⇒ prefetch 也无可消项 ⇒ **判否（判据原文就是『无可消项 ⇒ 关』）**。")

R84_EV = (" 【W943 改判 2026-11-04 14:3x｜A 级，推翻同轮初稿】W942 初稿用 W924 的『dp4a 占 53.3%』得端到端 −3.65%；"
          "**但那个分母是整个 mmq-instance 模块（多 J / fallback 实例求和），实际只 dispatch 一个 kernel**。"
          "按真 kernel 的 ISA：dot4 1,024/3,411 = **30.0%** ⇒ 减半 = 总指令 −15.0% ⇒ kernel −10.1%（VALU 67.1%）⇒ "
          "× gate/up 20.4% = 端到端 **−2.05%**；乐观情形（顺带省解包 ≈ −3.4% 指令）也只到 −2.4%，**均低于 2xCV 门 3.2%** ⇒ **判不做**。"
          "方法教训（已写进 W925 分母纪律）：组件占比的分母必须是**实际 dispatch 的那个 kernel**，模块/实例库求和只能当上界的上界。")

R85_ADD = (" 【W943 增补】R84 判否后，MMQ 四扇门（R51/R58/R60/R63/R84）全部关闭 ⇒ **prefill 再往上只剩 attention（R46/R64）与 GDN/入口**，"
           "R85 的手段顺序不变：R46 拆三段 > R64 Q.K int8。")

R74_ADD = (" 【W943 挂起】R84 已判否 ⇒ 没有内核要接 W4A4，本条**不付精度门的成本**；若将来 R84 复活（例如 dot8 顺带省掉解包被实测证实）再解冻。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9:
            if f8[1] == "R63" and f8[7] != "DONE_NEG":
                f8[7] = "DONE_NEG"; f8[6] = "1"; f8[8] += R63_EV; changed.append("R63"); ln = "\t".join(f8)
            elif f8[1] == "R84" and f8[7] != "DONE_NEG":
                f8[7] = "DONE_NEG"; f8[6] = "1"; f8[8] += R84_EV; changed.append("R84"); ln = "\t".join(f8)
            elif f8[1] == "R85":
                f8[8] += R85_ADD; changed.append("R85"); ln = "\t".join(f8)
            elif f8[1] == "R74":
                f8[8] += R74_ADD; changed.append("R74"); ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed)
