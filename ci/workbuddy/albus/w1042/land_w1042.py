#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: ledger rows + §0.1 / 回写 block + PORT_PLAN + REBUILD_RECIPE + SNAPSHOT."""
import io
import os
import re
import shutil
import time

ROOT = r"D:/workbuddy_space/strata_ws"
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
PORT = os.path.join(ROOT, "albus", "gfx906_survey", "PORT_PLAN.md")
RECIPE = os.path.join(ROOT, "deploy", "REBUILD_RECIPE.tsv")
HAND = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")

# ---------------------------------------------------------------- 1. ledger
lines = io.open(PROG, encoding="utf-8").read().splitlines()

ROWS = [
 ["B5本机缺口", "P499",
  "W1042 三阶段窗口：把 R103 的 attn OPT 从 `port-all` 移植到生产树 `pr/k10`（`gfx906/attn-opt @ deb41e12`），并用 R104 的取样面验 build floor、数值、计时、任务级门",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 实测（窗口 14:53:33→15:09:04，停机 931 s、重启 1 次、零装机）**。**移植**：`port-all@62d10e25` 的 `qsa_decode_attn.cu` 整文件覆盖到 `k10@af797b90`（两树该文件在共同祖先 `e181bda5` 上逐字节相同，是拷贝不是合并），commit `deb41e12`，构建 38 s 出 `strata-0.1.57-attn`（`3b758f88…` / 43,452,008 B）。**P1 数值**：A=`kvg` / B=`attn` 无开关 / C=`attn`+`ATTN_DP4A`，四个长度 1000/8000/16000/20000 的 fp32 全词表 logits —— **B≡A 四点逐字节相同（build floor）**，C 相对 A 的 KL = `0.00037/0.00345/0.01429/0.18750`，与 W1041 的 `pa5` 分支**逐位一致**（argmax 前三 same、20K DIFF 也一致）⇒ 移植行为等价，`--kv-grow` 未扰动取样面。**P1 同 run 计时**：`qsa attn` C vs B = 66/1401/3043/3878 vs 74/1579/3418/4367 ms（−10.9…−11.3%），整条 GPU 5430/10361/21144/30313 vs 5586/10691/21553/30738 ms（−1.6…−2.8%）。**P2 生产形状配对**：2.5K gpu −1.89% vs 2×CV 5.97%（within noise）、8K −2.72% vs 1.34%（REAL）、16K −1.72% vs 0.36%（REAL）；attn 相位 −10.5…−11.8% 三点全 REAL。**P3 任务级门**：16K/28K needle 两臂（off / DP4A on）**4/4 命中**，`cached_tokens=0`，28K 为 28,695 token。**未装机**：生产仍是 `kvg`。",
  "P497;P498", "KW:build floor|931 s|needle"],
 ["B5本机缺口", "P500",
  "**作废上一轮的错误结论（取样面错第四次）**：`hip_compat/intrinsics.hpp` 不在生产编译链，gfx906 的 dot4 早就是硬件指令",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 源码核实 + ISA 实测**。`include/strata/hip_compat/intrinsics.hpp`（W1036/A0 提交 `79516b21` 改的那份）**没有任何 `.d` depfile 引用它**；真正生效的 `__dp4a` 在 `include/strata/platform/hip_compat/strata_hip.h:236-247` 的 `strata_dp4a`，那里**已经写了** `#if defined(__gfx906__) … return __builtin_amdgcn_sdot4(a,b,c,false)`。拆 `.hip_fatbin` 后 `qsa_decode_attn.cu.o` 的设备 ISA：`v_dot4_i32_i8` **384 条**、`v_mad_i32_i24` **0 条**（没有软件回退）。⇒ 上一轮我说的「gfx906 走 28 指令软件 fallback、补 A0 还有大收益」**整段作废**；W1042 的 −11% 本来就是硬件 dot4 带来的。**同族**：`P493`（日志整文件 grep）、`P496`（交接门验错件）——**门验的对象错了，看起来还是绿的**；这次是读源码读错了文件。修法：给死文件加顶部警示 + 把 A0 分支同步进去（避免两份漂移），生效层保持不动。",
  "P493;P496", "KW:不在生产编译链|strata_hip.h|384"],
 ["B5本机缺口", "P501",
  "移植 dot8 核心：生效层 `strata_hip.h` 新增 `strata_dp8a/__dp8a`，独立头 `gfx906_dot.hpp` 带 bit-exact 回退，自检真跑 `v_dot8_i32_i4`",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 实测（零停机）**，commit `gfx906/dot48 @ e0ce7c96`（5 文件 / +248 行）。**dot4**：`strata_hip.h` 里早有硬件分支（ISA 384 条），本轮只对齐死文件 + 标注陷阱。**dot8**：新增 `include/strata/platform/hip_compat/strata_hip.h` 的 `strata_dp8a`（`__builtin_amdgcn_sdot8(a,b,c,false)`，非 gfx906 走 signed-nibble 标量回退）、`include/strata/kernels/gfx906_dot.hpp`（两个核心 + 同语义回退）、`tools/gfx906_dot48_selfcheck.cu`。**自检**：8192 随机 + 9 边界（含累加器正/负溢出），device 侧 `HW_device=1`，**dot4_bad=0 / dot8_bad=0**，溢出值 `-2147419148 / -2147483464` 证明 `clamp=false` 是回绕不是饱和。拆 fatbin 后自检 ISA = `v_dot4_i32_i8` 1 条 + `v_dot8_i32_i4` 1 条。**诚实边界**：候选二进制与 `attn` **逐字节相同**（`3b758f88…`），因为 dot8 **尚无生产调用点**，链接器把 helper DCE 掉了 —— 这不算「已接入生产」，只算「核心可用 + 已被硬件验证」。接入需要 4-bit 打包数据：k8v4 的 V 是 q4 code 但注意力概率是 float，得先做 `p→int4` 量化并过数值门（`PORT_PLAN` C2），已立 `R108`。外证：gfx906 有 `v_dot8_i32_i4` 但**没有** `v_dot8c_i32_i4`；`gfx9-generic` 目标会排除 dot4/dot8，必须 `--offload-arch=gfx906`（`build.ninja` 的 FLAGS 实测如此）。",
  "P500", "KW:strata_dp8a|自检|R108"],
 ["B5本机缺口", "P502",
  "ISA 验证链修正：`-S` 只出 host stub、直接 `llvm-objdump` 只出 x86 ⇒ 两次「0 条指令」都是假的",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 实测**。第一次探针用 `ninja -t commands` 把 `-c` 换成 `-S`，base 与 a0 两份 `.s` 都 69,186 行、所有 GPU opcode 计数为 0 ⇒ 曾误以为「两个版本一样」。实际 `-S` 生成的是 **host stub**，device 代码在 `.hip_fatbin` bundle 里。第二次对 host 可执行文件直接 `llvm-objdump -d --mcpu=gfx906`，同样是 0 条。**正确链路**（`albus/w1042/isa_final.sh`）：`llvm-objcopy --dump-section .hip_fatbin=fat.bin` → `clang-offload-bundler -list -type=o` 取 `hip-amdgcn-amd-amdhsa--gfx906` → `-unbundle` → `llvm-objdump -d --mcpu=gfx906 code906.o`。结果：自检 `v_dot4=1 / v_dot8=1`；生产 `attn_tu` `v_dot4=384 / v_dot8=0 / v_fmac_f32=7725`。**规矩**：GPU 指令数只在拆包后的设备 code object 上数，对全零结论先怀疑观测手段（`SOUL.md`）。",
  "P500;P501", "KW:llvm-objcopy|unbundle|0 条"],
 ["B5本机缺口", "P503",
  "计时 harness 在 `DEC=0` 时崩在 `statistics.mean([])`，t_T1/T2.json 未落；从 window.log 原始行重算配对统计与 2×CV",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 实测**。`albus/w1042/ab_w1042.py` 把 `DEC` 改成 0 后仍无条件执行 `decode_summary` 的 `st.mean(r)`，两臂各抛 `StatisticsError: mean requires at least one data point`，rc=1，**结构化 JSON 没写**。但每个 prefill 行已打到 `window.log`，样本逐字可恢复（`albus/w1042/collect.py` 解析，注意 harness 在 `attn=` 前打了两个空格，写死单空格的正则会全空 —— 又一个取样面）。重算结果写在 `albus/w1042/p2_stats.json`：2.5K/8K/16K 的 gpu Δ = −1.89/−2.72/−1.72%，2×CV = 5.97/1.34/0.36%，attn 相位 −11.81/−11.29/−10.53% vs 0.87/1.32/0.83%。**修法**：`decode_summary` 在 `DEC=0` 时跳过；harness 的 prefill 行改固定宽度或 JSON 输出，别再靠正则对齐。",
  "P493", "KW:statistics|2×CV|取样面"],
 ["B5本机缺口", "P504",
  "移植脚本首次失败时把生产源码树留在 `gfx906/dot48` 分支上；`fail()` 必须自动切回并验证",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 实测**。第一次构建因 `gfx906_dot.hpp` 被 `dp4a.hpp` 带进无运行时头的 TU 而挂（6 个 `unknown type name '__forceinline__'`），脚本 `fail()` 直接 `exit 1`，**没有切回生产分支**，树停在 `gfx906/dot48`。第二次跑前置检查才把它拦下。修法：`fail()` 里 `git checkout -q gfx906/lcpp-k10` + 记录 branch/head/dirty；`checkout -B` 支持重跑；新头改成自包含（自己 include `hip/hip_runtime.h` 或 `cuda_runtime.h`），并且**不再**从 `dp4a.hpp` include 它（那个头被 host-only TU 包含）。最终 `DONE` 时树 `af797b90` / 脏 0 行。**规矩**：任何碰生产源码树的脚本，失败路径也要还原，且还原结果必须被断言。",
  "P493", "KW:fail|切回|af797b90"],
 ["B5本机缺口", "P505",
  "外证校准任务级门：短上下文 KL 是压力指标不是判决；P3 只跑 16K/28K 单深度不够，装机前要补",
  "W1042", "count", "1", "1", "DONE",
  "**W1042 上网核实（用于校准判据，不代替实测）**。① vLLM 2026-04 的 128K needle 在 FP8 KV 下从 **91% 掉到 13%**，延迟直方图、短上下文 eval、perplexity 全绿（根因是 Hopper FP8 累加精度，两级累加修回 89%）；② RDNA4 TurboQuant 实测：turbo3 的 `KLD@512 = 3.0985` / same-top-p 41%，但 8K–33K 的 needle **9/9**，原话「KLD@512 is a strict stress metric, not a verdict」；③ 运维侧建议「不要 gate 在 perplexity / 短 prompt，要 gate 在 max-context needle、多跳 QA、长输出一致性，且同 prompt diff 输出」。⇒ 本轮 P3 的 **16K/28K、单深度、fact 在开头** 只能算通过了一个弱门；**装机前**应补：max-context 附近（≥128K）× 3 深度 × 两臂输出逐 token diff，以及多跳检索。已并入 `R108` 的前置条件。",
  "P498", "KW:needle|短上下文|装机前"],
 ["B6判定探针", "R108",
  "把 dot8 核心接进生产内核（`v_dot8_i32_i4` 目前 0 个调用点），并补齐 max-context 任务级门",
  "W1042", "count", "1", "0", "OPEN",
  "**W1042 立**。`strata_dp8a/__dp8a` 已在生效层且自检通过，但 `qsa_decode_attn.cu.o` 的 ISA 里 `v_dot8_i32_i4 = 0`，候选二进制与 `attn` 逐字节相同（无调用点被 DCE）。**候选接入面（按风险排序）**：① k8v4 的 **V 侧 q4 code**（V 本来就是 4-bit，一个 int32 装 8 个值，正好是 dot8 的一个操作数），但需要把 softmax 概率 `p` 量化成 int4 —— **新的量化误差源**，须自带锚臂 + 数值门（`PORT_PLAN` C2）；② Q4_K / IQ4 权重 MMVQ（需先核数据布局是否已 4-bit 打包）；③ 仅作微基准 / 诊断入口（零数值风险，但零性能收益）。**判据**：ISA 里 `v_dot8_i32_i4 >= 1`、build floor 逐字节、四长度 KL 不劣于现役 KV 档、top-1、以及 `P505` 要求的 max-context × 3 深度 × 两臂 token diff。**停机**：需要一个新窗口（估 10–15 min），与 `R103` 装机合并做更省。**风险**：dot4 已是硬件路径（384 条），dot8 的收益上限要先用 roofline 判 attn 是否 ALU-bound，别凭「指令更少」下结论（`GFX906_OPT_INVENTORY §8`）。",
  "P501;P505", "KW:v_dot8_i32_i4|接入|max-context"],
]

for r in ROWS:
    assert len(r) == 11 and all("\t" not in x for x in r), r[1]
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
lines += ["\t".join(r) for r in ROWS]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

tot = done = 0
for l in io.open(PROG, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
print("ledger", tot, done, round(100.0 * done / tot, 1))

# ---------------------------------------------------------------- 2. plan
shutil.copy2(PLAN, PLAN + ".bak_w1042_" + time.strftime("%Y%m%d_%H%M%S"))
s = io.open(PLAN, encoding="utf-8").read()
s = re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1041；",
           "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1042；" % (tot, done, 100.0 * done / tot),
           s, count=1)
# insert R108 into the unique queue, right before R105
qold = "→ **R105（"
assert qold in s
s = s.replace(qold, "→ **R108（新立，`P501`：dot8 核心已移植并自检通过，但 `v_dot8_i32_i4` 还是 0 个调用点，接入需 `p→int4` + 数值门 + max-context 任务级门）** "
              "→ **R105（", 1)
# R103 wording: ported and gated, install still pending
s = s.replace("**R103 重开并结、待移植（", "**R103 重开并结、已移植且过任务级门、待装机（", 1)

BLOCK = """
---

### 回写 · W1042（2026-11-07 14:53–15:57）R103 移植 + dot4/dot8 两个核心

> 停机 **931 s / 重启 1 次 / 零装机**（窗口 14:53:33→15:09:04；窗口正常收尾日志因会话中断缺失，停机数与重启数由 `downtime starts now` 与容器 `StartedAt` 反推）。dot8/dot4 移植段**零停机**。生产仍是 `kvg`（`a85743d7`）+ config `ee69ebc2`。

- **R103 移植完成**（`P499`）：`gfx906/attn-opt @ deb41e12`，`strata-0.1.57-attn`（`3b758f88…`）。**build floor 四点逐字节相同**；C 臂 KL `0.00037/0.00345/0.01429/0.18750` 与 W1041 的 `pa5` 逐位一致；生产形状计时 8K gpu −2.72% vs 2×CV 1.34%、16K −1.72% vs 0.36%，attn 相位 −10.5…−11.8% 三点全 REAL；16K/28K needle 两臂 4/4 命中。**仍未装机**：等一个独立停机批准，且 `P505` 的 max-context 门要补。
- **我上一轮的一句话整段作废**（`P500`）：`hip_compat/intrinsics.hpp` **不在任何生产 depfile 里**；真正生效的 `__dp4a` 是 `strata_hip.h:236` 的 `strata_dp4a`，**本来就有** `__builtin_amdgcn_sdot4`。设备 ISA 实测 `v_dot4_i32_i8` **384 条 / `v_mad_i32_i24` 0 条**。所以 dot4 核心早已在产、且是硬件指令；「补 A0 还能再快一大截」是读错文件推出来的。与 `P493`/`P496` 同族第四次：**取样面错，门还是绿的**。
- **dot8 是真缺口，本轮补上**（`P501`）：`gfx906/dot48 @ e0ce7c96`（5 文件 +248 行）——生效层 `strata_hip.h` 加 `strata_dp8a/__dp8a`（`__builtin_amdgcn_sdot8(a,b,c,false)` + 标量回退），独立头 `include/strata/kernels/gfx906_dot.hpp`，`tools/gfx906_dot48_selfcheck.cu`。自检 8192 随机 + 9 边界 **dot4/dot8 均 0 mismatch**、`HW_device=1`、溢出回绕正确，自检设备 ISA `v_dot4=1 / v_dot8=1`。**诚实边界**：候选二进制与 `attn` **逐字节相同**，因为 dot8 尚无生产调用点、被链接器 DCE ⇒ 只算「核心可用且验证」，**不算已接入生产**，已立 `R108`。
- **验证链本身也修了**（`P502`）：`-S` 只出 host stub、对 host 文件直接 `llvm-objdump` 只出 x86，两次「0 条 GPU 指令」都是假的。正确链路写进 `albus/w1042/isa_final.sh`：`llvm-objcopy --dump-section .hip_fatbin` → `clang-offload-bundler -unbundle` → `llvm-objdump -d --mcpu=gfx906`。
- **两个脚本缺陷**（`P503`/`P504`）：计时 harness 在 `DEC=0` 时崩在 `statistics.mean([])`（结构化 JSON 没落，改从 `window.log` 原始行重算，正则还要注意 attn 前是两个空格）；移植脚本首次失败时**把生产源码树留在侧分支**，已给 `fail()` 加自动切回 + 断言。最终 `pr/k10 @ af797b90`、脏 0 行。
- **外证**（`P505`，只用于校准判据）：vLLM 128K needle 在 FP8 KV 下 91%→13% 而延迟与短上下文 eval 全绿；RDNA4 的 turbo3 `KLD@512=3.10` 但 needle 9/9（「短上下文 KLD 是压力指标，不是判决」）。⇒ 本轮任务级门只用了 16K/28K 单深度，**装机前补 max-context × 3 深度 × 两臂 token diff**。
"""

DIR_ROW = ("| `回写 · W1042（2026-11-07 14:53–15:57）R103 移植 + dot4/dot8 两个核心` | "
           "R103 移植完成：build floor 逐字节、KL 与 W1041 同位、生产形状 8K/16K 全 REAL、needle 4/4；"
           "作废「gfx906 走软件 dot4」的误判（生效层是 strata_hip.h，ISA 已有 384 条 v_dot4）；"
           "dot8 核心移植 + 自检通过但尚无调用点（R108）；ISA 验证链与两处脚本缺陷一并修 |")

i0 = s.index("### 6.5.0 回写块目录")
t0 = s.index("| 小节 |", i0)
tend = s.find("> **【AUDIT27", t0)
tend = tend if tend > 0 else t0 + 60000
last = s.rfind("| `回写 ·", t0, tend)
i1 = s.index("\n", last) + 1
s = s[:i1] + DIR_ROW + "\n" + s[i1:]
s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated")

# ---------------------------------------------------------------- 3. PORT_PLAN
p = io.open(PORT, encoding="utf-8").read()
p = p.rstrip("\n") + """

---

## W1042 移植状态（2026-11-07，机主 15:26「移植 gfx906 专用的 dot8 和 dot4 两个核心」）

| 核心 | 指令 | 生产树位置 | 状态 |
|---|---|---|---|
| **dot4** | `v_dot4_i32_i8` | `include/strata/platform/hip_compat/strata_hip.h:236-247`（`strata_dp4a` / `__dp4a`） | **早已在产且是硬件指令**：拆 fatbin 后 `qsa_decode_attn.cu.o` 有 **384 条**、`v_mad_i32_i24` 0 条。W1036/A0 改的 `include/strata/hip_compat/intrinsics.hpp` **不在任何 depfile 里**，是死文件；本轮给它加警示并把 A0 分支同步过去，防止下一个人再改错文件。 |
| **dot8** | `v_dot8_i32_i4` | 新增 `strata_hip.h::strata_dp8a/__dp8a` + `include/strata/kernels/gfx906_dot.hpp` + `tools/gfx906_dot48_selfcheck.cu` | **核心已移植、自检通过、尚无生产调用点**（`R108`）。8192 随机 + 9 边界用例 dot4/dot8 均 0 mismatch，`HW_device=1`，自检设备 ISA `v_dot4=1 / v_dot8=1`；候选二进制与 `attn` 逐字节相同，因为新 helper 被 DCE。 |

**硬件前提（`llvm-mc -mcpu=gfx906` 与 ROCm `AMDGPUAsmGFX906` 核实）**：`v_dot4_i32_i8` / `v_dot8_i32_i4` / `v_dot2_f32_f16` 在**具体 gfx906 目标**上可用；`v_dot4c` / `v_dot8c` **不可用**；`gfx9-generic` 目标会排除这些指令 ⇒ 构建必须 `--offload-arch=gfx906`（`build-masterp/build.ninja` 的 FLAGS 实测如此）。`sdot4/sdot8` 的第 4 参数 `clamp=false` 时 int32 累加器**回绕**（自检溢出用例已验），与 CUDA `__dp4a` 的模 2^32 契约一致。

**接入面（未做，别当成完成）**：k8v4 的 V 是 4-bit code，正好能填 dot8 的一个操作数，但 softmax 概率是 float ⇒ 需要 `p→int4` 量化（新误差源，见 §C2）+ 自带锚臂的数值门 + max-context needle。先做 roofline 判 attn 是否 ALU-bound：`GFX906_OPT_INVENTORY §8` 已记「ALU 换指令在 gather 型 kernel 上无效，dp4a 已满速」。
"""
io.open(PORT, "w", encoding="utf-8", newline="\n").write(p)
print("PORT_PLAN updated")

# ---------------------------------------------------------------- 4. recipe
rl = io.open(RECIPE, encoding="utf-8-sig").read().splitlines()
for name in ("strata-0.1.57-attn", "strata-0.1.57-dot48"):
    assert not any(l.split("\t")[0] == name for l in rl if l.count("\t") >= 7)
base = [l for l in rl if l.startswith("strata-0.1.57-kvg\t")][0].split("\t")
attn = ["strata-0.1.57-attn", "3b758f88ddad25cdad236be267810a9e", "43452008",
        "gfx906/attn-opt @ deb41e12", base[4], base[5], base[6],
        "W1042/R103 移植：把 port-all@62d10e25 的 qsa_decode_attn.cu 整文件覆盖到 k10@af797b90（共同祖先 e181bda5 上该文件逐字节相同）；**未装机**，生产仍 kvg。四臂数值/计时/needle 见 P499"]
dot48 = ["strata-0.1.57-dot48", "3b758f88ddad25cdad236be267810a9e", "43452008",
         "gfx906/dot48 @ e0ce7c96", base[4], base[5], base[6],
         "W1042 机主指令「移植 dot8 和 dot4 两个核心」：dot4 生效层 strata_hip.h 早已硬件化（ISA 384 条），dot8 新增 strata_dp8a + gfx906_dot.hpp + 自检。**与 attn 逐字节相同**：dot8 尚无生产调用点被 DCE（P501/R108）。自检 ISA v_dot4=1/v_dot8=1"]
rl += ["\t".join(attn), "\t".join(dot48)]
io.open(RECIPE, "w", encoding="utf-8", newline="\n").write("\n".join(rl) + "\n")
print("recipe updated")

# ---------------------------------------------------------------- 5. snapshot
h = io.open(HAND, encoding="utf-8").read()
old = "> SNAPSHOT: round=W1041 date=2026-11-07"
assert h.count(old) == 1
io.open(HAND, "w", encoding="utf-8", newline="\n").write(h.replace(old, "> SNAPSHOT: round=W1042 date=2026-11-07"))
print("SNAPSHOT -> W1042")
