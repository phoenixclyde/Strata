import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R86":
        c[8] = (c[8] or "") + (
            " 【W997 推进 %s】**纠正 W995 的错误**：`ref/mx` **不是** sparse clone 缺文件，"
            "它本身就是 repack 源码目录（8 文件：`repack.cuh`/`repack-common.cuh`/`repack-kernels.cuh`/`repack-common.cu`/`buffer.cu`/`mul-mat*.cu`/README），"
            "Q5_1 接口 = `repack_q51_host()`(repack-common.cu:285) + `repack_gcn_nbytes()` + `mmq_gemm_repacked`。"
            "**本机形状扫描**（kq_bench，16 专家，Q5_1 down 640×2560）：rows/expert 32/64/128/320/1024 ⇒ "
            "**3.55/4.62/6.22/6.77/7.69 TMAC/s**（小行数掉 54%%，正对应 2K 短档）；Q4_K 5.67/5.13/5.83/6.56/7.94。"
            "**PMC 实测**（rocprofv3，Q5_1 `mul_mat_q<7,64>`）：SALUInsts 674 vs VALUInsts 21,233（标量地址仅 3.1%%）。"
            "**外网核对**：mx README 里**没有** Q5_1 +84%% 的表，唯一数字是 MoE mat-vec 的 +3.5%%/−15.9%%（decode，非 prefill）；"
            "另一 gfx906 fork 实测 PP16384 +14.1%%。⇒ **+84%% 口径存疑，不得直接引用**；R86 期望上限按 ~20%% 估，先做单内核 A/B。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B4上游移植", "P273", "Q5_1/Q4_K 的形状扫描（每专家行数 → TMAC/s）", "W997", "count", "1", "1", "DONE",
               "**W997（%s）** 16 专家、3 reps：Q5_1 32→3.55 / 64→4.62 / 128→6.22 / 320→6.77 / 1024→7.69 TMAC/s；"
               "Q4_K 5.67/5.13/5.83/6.56/7.94。小行数时 Q5_1 掉 54%%，与 R95 的 2K 首块吻合。" % TS]),
    "\t".join(["B4上游移植", "P274", "Q5_1 MMQ kernel 的 PMC 指令构成", "W997", "count", "1", "1", "DONE",
               "**W997（%s）** rocprofv3 采 `mul_mat_q<(ggml_type)7,64,false>`：SALUInsts 674.125、VALUInsts 21,232.875、"
               "SALUBusy 1.7–1.9%%、VALUBusy 53–59%% ⇒ 标量地址指令仅占 3.1%%。W944 的「v_add_u32/v_mul_lo_u32 19.7%%」是 VALU 特定 opcode，"
               "本机尚未复核（roc-obj-extract 未产出，列为待办）。" % TS]),
    "\t".join(["B4上游移植", "P275", "外网核对 mx repack 的收益口径", "W997", "count", "1", "1", "DONE_NEG",
               "**W997（%s）** mx README 无 Q5_1 +84%% 表；唯一数字是 MoE mat-vec +3.5%%/−15.9%%（decode）。"
               "iacopPBK/mxxm-t gfx906 fork 的公开实测是 PP16384 +14.1%%、120k fill +9.3%%。⇒ 把 +84%% 当本机预期不成立。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R86 补推进 + P273/P274/P275")
