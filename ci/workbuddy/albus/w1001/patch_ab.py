import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R86":
        c[8] = (c[8] or "") + (
            " 【W1001 公平 A/B，结论转正 %s】修正 W999 两缺陷后重测：①按 mx `use_w32` 分派"
            "（rows<4096 走 `mmq_gemm_repacked_w32<true,1,8,Q5_1>`，否则 64-wide）；"
            "②激活改 grouped `block_q8_1_mmq` 尺寸/stride，并进一步做成**两臂共用同一份** "
            "`mmq::quantize` 输出（`build-tab/repacktest/ab_bench`，同一进程、同一 stream、hipEvent 计时）。"
            "**实测（16 专家 Q5_1 640×2560，3 reps 中位）**：rows 32 ⇒ canonical 0.237 / repacked **0.156**（ratio 0.659，快 34%%）；"
            "128 ⇒ 0.542 / 0.507（0.935，快 6.5%%）；320 ⇒ 1.245 / 1.430（1.149，慢 15%%）；"
            "1024 ⇒ 3.437 / 3.460（1.007，持平）。"
            "⇒ **repack 在小行数明显更快、大行数变慢**；W999 的「四档全慢」作废。"
            "**关键约束**：W991 实测 2K 请求的每专家 ncols p50=331 / p90=742 ⇒ 真实分布的大头正落在 repacked 变慢区间，"
            "端到端未必净赚。⇒ 正确设计不是全量替换，而是**按每专家行数混合分派**（见 R97）。R86 保持 OPEN。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B4上游移植", "P281", "公平 A/B：两臂共用同一份 grouped 激活", "W1001", "count", "1", "1", "DONE",
               "**W1001（%s）** 产物 `build-tab/repacktest/ab_bench.cu` + `ab_bench`（编链两步：hipcc -c 再链接 "
               "libstrata_mmq.a/libstrata_mmq_w4a4.a/libggml-base.a；运行时需 `STRATA_MMQ_KQ=1`）。"
               "rows 32/128/320/1024 的 canonical→repacked 中位：0.237→0.156 / 0.542→0.507 / 1.245→1.430 / 3.437→3.460 ms。" % TS]),
    "\t".join(["B5本机缺口", "R97", "按每专家 ncols 混合分派 repacked / canonical", "W1001", "count", "1", "0", "OPEN",
               "**W1001 立（%s）**：W1001 A/B 显示小行数 repacked 快 6.5–34%%、320 行慢 15%%、1024 持平；"
               "W991 的 2K 请求 ncols min4/p50 331/p90 742/max 7680。⇒ 不做全量替换，改**按 expert_bounds 的每段行数选路径**："
               "小段（<128 行）走 repacked w32，大段留 canonical，一次 group 内混合 launch。"
               "预期：吃到小专家的 34%% 而不付大专家的 15%%。判据：六长度档 + 2×CV，端到端 prefill@2K 提升 ≥5%% 才继续。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R86 补公平 A/B + P281/R97")
