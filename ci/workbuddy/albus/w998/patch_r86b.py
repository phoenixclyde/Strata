import io, time
TS = time.strftime("%Y-%m-%d %H:%M")
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R86":
        c[8] = (c[8] or "") + (
            " 【W998 两条独立判否证据 %s】**①反汇编复核**（`clang-offload-bundler` 提取 "
            "`mmq-instance-q5_1.cu.o` 的 gfx906 code object + `llvm-objdump` 逐函数数 opcode，69 函数/87k 指令）："
            "主 GEMM `mul_mat_q<Q5_1,J=64>` 的 `v_add*+v_mul*` 占 **16.8–18.1%%**，11 个主 GEMM 合计 **16.2%%**；"
            "`stream_k_fixup`（我们 stream_k=false **根本不跑**）是 19.0%%。⇒ W944 的「19.7%%」量级成立，"
            "但它是**地址指令占比，不是可拿到的加速**；repack 的理论上限 ≈16–18%%。"
            "**②代理实验**（同形状 Q8_0 平面布局 vs Q5_1 交错，16 专家 640×2560）："
            "rows 32/128/320/1024 ⇒ Q5_1 0.238/0.540/1.243/3.489 ms，Q8_0 0.246/0.731/1.442/3.576 ms ⇒ "
            "**平面布局并不更快**（Q8_0 每字节效率虽高 15–30%%，但字节数 +33%% 全吃掉）。"
            "⇒ 两条独立证据都指向 **单内核收益 <20%%**，正落在 W944 自定的「<20%% 判否」线内。"
            "**但按机主「测完才能判断」的规矩，R86 保持 OPEN**：唯一剩余动作是 repack 单内核 A/B，"
            "不达标即正式判否。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B4上游移植", "P276", "Q5_1 MMQ 主 kernel 的地址指令占比（反汇编实测）", "W998", "count", "1", "1", "DONE",
               "**W998（%s）** 工具链：`objcopy --dump-section .hip_fatbin` → `clang-offload-bundler --unbundle "
               "--targets=hip-amdgcn-amd-amdhsa--gfx906` → `llvm-objdump -d --mcpu=gfx906`。"
               "主 GEMM J=64 两变体 16.8%%/18.1%%、11 个主 GEMM 16.2%%、fixup 19.0%%（不跑）、全对象按正确口径 ~18%%。"
               "**注**：W998 中途一次 8.1%% 的读数是正则漏匹配 `v_add_u32_e32` 的低估，已作废。" % TS]),
    "\t".join(["B4上游移植", "P277", "Q8_0 平面布局 vs Q5_1 交错布局（repack 收益的代理实验）", "W998", "count", "1", "1", "DONE",
               "**W998（%s）** 16 专家、3 reps、640×2560：rows 32/128/320/1024 时 Q5_1 "
               "0.238/0.540/1.243/3.489 ms，Q8_0 0.246/0.731/1.442/3.576 ms。Q8_0 是 8bpw（Q5_1 6bpw，多 33%% 字节）；"
               "折算每字节效率高 15–30%% 但净耗时仍慢 2–35%% ⇒ **平面布局本身不足以解释 +84%%**。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R86 补两条证据 + P276/P277")
