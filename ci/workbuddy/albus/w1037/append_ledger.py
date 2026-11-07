import io, os, shutil, sys

P = "deploy/PROGRESS.tsv"
BAK = P + ".bak_w1037"
shutil.copy2(P, BAK)
s = io.open(P, encoding="utf-8").read()
lines = s.splitlines()

P425 = "\t".join([
    "B8工程", "P425",
    "A5 在 pa0 里是死代码：8-wide gather 的派发仍包在 STRATA_EXPERIMENTAL_SM60 里，开关字符串根本没进二进制",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机械前置门：开关必须在二进制里看得见）**：pa0（W1036 构建，md5 `e99455a0`）里 "
    "`strings <bin> | grep -c` 五个 gfx906 开关只找到 4 个——`STRATA_GFX906_Q8_GATHER8` = **0**。"
    "根因：`kv_q8.cu:221` 的**派发**仍在 `#if defined(STRATA_EXPERIMENTAL_SM60)` 内，W1036 只把 8-wide 内核定义与 "
    "`pre75_q8_gather()` 放进了 `STRATA_HIP_GFX906` 分支 ⇒ 函数无人调用、链接时被整个丢掉。"
    "不修就开窗，A5 会被记成「零收益」而不是「没跑」。已修（派发处加 `|| defined(STRATA_HIP_GFX906)`，默认仍由 env 关着），"
    "重建 pa1 = md5 `36bc1be7` / 43,043,424 B，五开关 **5/5 在册**，且 `build-port2/strata` 与候选件同 md5。"
    "**新增门**：任何「一分支一编译、逐项开关」的 A/B，开窗前先 `strings` 点开关，成本 0。",
    "P421", "KW:死代码|strings 点开关"])

P426 = "\t".join([
    "B6判定探针", "P426",
    "否掉「Q4_K 的 J≤64 让 MoE 白算」：全量 pick_J 统计 padding 中位数 7.9%，上游表 pin 与新 tag 逐字节相同",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立**：① 生产日志 **12,268 行** `pick_J`（type 7/8/12/13）统计 `ceil(ncols/J)*J/ncols`——"
    "中位数 **7.9%**、均值 **12.4%**，尾部全在 `ncols` 极小的退化样本（ncols=1 → 8×）；"
    "gate/up 这类 ncols≈3000–4000 的调用 padding **≤1.8%**（3144 → 3200 列）。"
    "② `ref/llama_3cf0325`（pin b11062）与 `ref/llama_b12169` 的 `mmq-config-gcn.cuh` **diff 为空**，"
    "即「Q4_K 只给 J≤64、Q8_0 给到 128」是上游全局现状，没有可移植的表改进；"
    "③ 两者 FLOPs 相同（都按 ceil 补到同一列数），差别只有块数与权重重读（按 tile 算 −26% 流量）。"
    "⇒ R103 吸收的「J 上限」一支**判否**：不做表扩展、不开窗。",
    "R103", "KW:padding|pick_J"])

P427 = "\t".join([
    "B6判定探针", "P427",
    "更正 P423 的「还有 5.4× 空间」：Q4_K 内环每 4 个 MAC 至少要 3 条 lane 指令，实测等价 5.1 条，剩余上限 1.7×",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（更正 P423 的表述，不动它的事实）**：`vecdotq.cuh:542-556` 的 Q4_K×Q8_1 MMQ 内环是 "
    "`dp4a((v[j] >> (4*i)) & 0x0F0F0F0F, u[...], acc)`——**每 4 个 MAC 至少 3 条 lane 指令**（移位 / 与 / dot4），"
    "外加 v、u 的取数。dp4a 峰值 26.5 TMAC/s（60CU×64lane×1.72GHz×4MAC）若按「1 条 dot4 = 4 MAC」计，"
    "3 条指令给出的上限就是 **8.8 TMAC/s**；实测 gate/up 2.5K = 3.93 TMAC / 754 ms = **5.21 TMAC/s** ⇒ "
    "等价 **≈5.1 条指令 / 4 MAC**，剩余空间 **8.8/5.21 = 1.69×**，而不是 26.5/5.21 = 5.1×。"
    "要吃掉这 1.69× 只能减少每 4 MAC 的指令数，唯一路径是让**激活也变 4-bit**（`v_dot8_i32_i4`），"
    "而 P38 已判否（精度 + 格式代价）。⇒ **Q4_K MoE GEMM 无内核级空间**，预填剩余杠杆只在 R95 的固定项与调度侧（D2）。",
    "P423", "KW:指令上限|5.21 TMAC/s"])

new_lines = []
patched_r103 = False
for ln in lines:
    if "\tR103\t" in ln:
        f = ln.split("\t")
        f[3] = "W1037"
        f[8] = ("**机主 2026-11-07 06:36 定：把 `albus/gfx906_survey/PORT_PLAN.md` 作为本方案的一个 R，置顶最优先。**"
                "子项状态（W1036 实测 + W1037 修正）：A0 dp4a 已落地并**实测零结果**（10.8K prefill 差 0.1%，CV 0.2%/0.0%）"
                "⇒ 不记收益；A1/A2/A3/B1/B2 在分支 `gfx906/port-all`，A5 曾是**死代码**（`P425`）已修；"
                "候选件 pa1 = `36bc1be7` / 43,043,424 B，五开关 `strings` 5/5 在册，D1 与 `build-port2/strata` 同 md5。"
                "**B3/C1/A4 defer**（B3 前提被 `P421` 否掉）。**两支已判否、不再开窗**：J≤64 表扩展（`P426`，padding 中位数 7.9%）"
                "与「内核还有 5.4× 空间」（`P427`，实际上限 1.69×）。**待机主点头**：一窗三臂（ctl / +ATTN_DP4A / "
                "+DPP+LDS_PAD+ROUTE_DPP），三次重启约 5–8 min 不可用；预期 B1+B2 在 3.4K 拿 2–4%、10.8K 拿 4–6%"
                "（attn 占比实测 10.7% → 16.5%）。D2/D3 仍需独占窗口。")
        ln = "\t".join(f)
        patched_r103 = True
    new_lines.append(ln)

assert patched_r103, "R103 row not found"
out = "\n".join(new_lines + [P425, P426, P427]) + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("rows before", len(lines), "after", len(out.splitlines()), "| backup", BAK)
