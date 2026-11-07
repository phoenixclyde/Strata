# -*- coding: utf-8 -*-
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

desc = ("prefill 吞吐台阶（长档 801 -> >=850 tok/s，+6%）：这是**端到端验收口径**，"
        "手段按 R46(attention 效率) > R64(Q.K int8) > R60(stream-k) 排序；chunk 方向已封顶")

ev = ("**W941 立（2026-11-04 14:0x）**。"
      "**先纠一条观感**：机主说 prefill 800 多被回滚 —— 实测不是。801-804 tok/s 来自 prefill=auto:16384，"
      "**仍在生产**（本轮复测 60330 tok / 75030 ms = 804.1、60008 tok / 74987 ms = 800.2，均 0 reused，CV 0.1%）；"
      "被回滚的是同次实验的三补丁引擎 9d9cbe17 —— 它把 borrows 降 27% 但 TTFT 不动（801 vs 801）。"
      "**新 A 级实测**：chunk 32768 @64K = 80.300 s / 750 tok/s（CV 0.2%，0 reused）⇒ 比 16384 慢 6.4%；"
      "连同 8192 的 752（−6.2%）⇒ 倒 U 顶点就在 16384，chunk 方向到此为止。"
      "**R61 工具门（B 级）**：rocprofv3 作启动器可采 PMC（stream_roof 拿到 VALUBusy 5.97-7.93、引擎日志出现 queue-intercept）；"
      "但生产形状三次采集均未落盘（python 包裹=注入不到子进程；wrapper exec 引擎=注入生效却因容器终止未 finalize）"
      "⇒ 下一步只走**独立可执行自然退出**（tests/cuda/prefill_mmq_kquant_test.cpp；build-r28 未开 BUILD_TESTING，需手抽编译行）。"
      "**副产品**：开 PMC 后 16K prefill 只慢 1-6%（711-714 vs 759）⇒ 采集开销可承受。"
      "**外证核对**：milpster/gfx906-llama-cpp 的 +37% PP 主项是 upstream #27841 GCN MMQ config，"
      "**我们 pin 已含**（mmq-config-gcn.cuh 有 Q4_K CASE 256/512 × J=64/128 全套）⇒ 不是缺口。"
      "**判据**：每点必须 0 reused；|Δ|≥2×CV；写清 chunk / 长度 / T。")

row = ["B5本机缺口", "R85", desc, "W941 §2-§8", "count", "1", "0", "OPEN", ev, "W941;W932;W846"]

with io.open(P, "a", encoding="utf-8", newline="") as f:
    f.write("\t".join(row) + "\n")

print("appended cols=%d chars=%d" % (len(row), len(ev)))
