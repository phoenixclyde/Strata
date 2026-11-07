import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R86":
        c[6] = "1"
        c[7] = "DONE_NEG"
        c[8] = (c[8] or "") + (
            " 【W999 正式判否 %s】**做了 repack 单内核 A/B，不是推断**。实现：把 `ref/mx` 8 个文件摆成 "
            "`build-tab/repacktest/ggml-cuda/repack/`，用 `llama_b12110`(ggml 0.29) 的 common/mmq/unary 头补齐相对 include，"
            "仅 stub 掉 mx 的 `ggml_cuda_q8_1_cache_acquire`（返回 nullptr/hit=false，bench 不调用），"
            "host 端内联 `repack_q51` 生成 repacked 权重，启动 `mmq_gemm_repacked<true,2,4,GGML_TYPE_Q5_1>`"
            "（grid=(10,~tiles)、block=(64,4)）。产物 `build-tab/repacktest/repack_bench` 可复跑。"
            "**实测（16 专家、640×2560）**：rows/expert 32/128/320/1024 ⇒ repacked "
            "**0.543/0.557/1.464/3.582 ms**，canonical（W997/W998 同形状）**0.238/0.540/1.243/3.489 ms** ⇒ "
            "**分别慢 2.28× / 1.03× / 1.18× / 1.03×**，四档一致、无一处更快。"
            "**局限**（如实记）：mx kernel + 0.29 头混搭、激活用全零标准 block_q8_1（计时用）、mx 自带的松散 grid 有少量空转；"
            "但四档同向且与 W997 反汇编(16–18%% 地址指令)/W998 代理实验(平面布局净慢)一致 ⇒ 判否稳健。"
            "**R86 = DONE_NEG，不做生产移植。**" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B4上游移植", "P278", "repack 单内核 A/B 实测（R86 结案数据）", "W999", "count", "1", "1", "DONE_NEG",
               "**W999（%s）** 可复现路径：`/home/albus/strata166/build-tab/repacktest/repack_bench.cu` + 同目录 `repack_bench`；"
               "canonical 臂 = `build-tab/kq_bench 16 <rows> 3 7 640 2560`（需 `STRATA_MMQ_KQ=1`）。"
               "repacked 0.543/0.557/1.464/3.582 ms vs canonical 0.238/0.540/1.243/3.489 ms（rows 32/128/320/1024）。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R86→DONE_NEG + P278")
