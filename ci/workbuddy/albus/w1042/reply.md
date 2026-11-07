# W1042 报告 · R103 移植 + gfx906 的 dot4 / dot8 两个核心

> 一句话：**dot4 核心早就以硬件指令在产（`v_dot4_i32_i8` 384 条），我上一轮说它「走软件回退」是读错了文件；dot8 核心是本轮真正补上的缺口**——已进生效层、自检 8192+9 用例零失配、设备 ISA 实发 `v_dot8_i32_i4`，但**还没有生产调用点**，所以候选二进制与 `attn` 逐字节相同，这点不粉饰。同时 R103 的 attn OPT 已移植到生产树并过了 build floor / 数值 / 计时 / 任务级四道门，**仍未装机**。

---

**一、生产容器（10 字段，2026-11-07 16:0x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `2026-11-07T07:09:04Z`（= 15:09:04，窗口还原后的那次启动） |
| 2 | 运行中引擎 | `strata-0.1.57-kvg` · md5 `a85743d7f554159e8ac1e2d432d2e5ea` · 43,214,976 B（**本轮未换件**） |
| 3 | config | md5 `ee69ebc272ce41a116f50ecb3bf0edc2` · `exe=/data/bin/strata-0.1.57-kvg` · args 38 / env 9（**未改**） |
| 4 | 健康 | `/health` `{"status":"ok","max_context":262144,...}` · restarts=0 · 日志全文 `could not map` / `ERR the K/V could not` 计数 **0** |
| 5 | 资源隔离 | `memlock=-1:-1` · `VmLck 0 kB` · `ulimit -l` unlimited |
| 6 | 显存 | used **33,493,676,032** / total 34,342,961,152 ⇒ **VRAM free 849,285,120 B（0.79 GiB）**；expert cache **8301 槽 / 24.23 GiB**；the prompt path **borrows 2609 CUDA0 cache slots (7.62 GiB)**；`elastic K/V: 16384 of 262144 cells（0.21 of 2.65 GiB）` |
| 7 | 回滚件 | `/data/bin` **55 件**（本轮 +2：`attn` `3b758f88…`、`dot48` 同 md5，均**未装机**）；上一版 `b12180`（`d24f8293…`）→ `k10p` → `-001`；rollback = 停容器 → `cp` 回 `tmp/w1040/cfg_w1040.bak` → 起容器（≈45 s） |
| 8 | 本轮改动 | **引擎无变更 / config 无变更 / disk = build = running 三方一致**；窗口停/起一次：**重启 1 次 / 停机 931 s / 装机 0 / 回滚 0**。dot4/dot8 移植与自检在独立容器里跑，**零停机** |
| 3a | args 明细 | 38 项未改：`--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`；四臂/计时跑的是**副本**（`tmp/w1042/cfgP_*.json`、`cfgA–D.json`），生产 config 一个字节没动 |
| 3b | env 明细 | 9 项全部未改：`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING`；被测开关只加在容器内（C/T2/S2 臂 `STRATA_GFX906_ATTN_DP4A=1`） |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git · `--offload-arch=gfx906`（`build-masterp/build.ninja` FLAGS 实测） |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；**生产源码树 `pr/k10` @ af797b90，相对 `origin/gfx906/mi50` 领先 2 / 落后 0，脏 0 行**。本轮两个新分支都只作候选、构建完即切回：`gfx906/attn-opt @ deb41e12`（R103 的 OPT 移植）、`gfx906/dot48 @ e0ce7c96`（dot4/dot8 核心，5 文件 +248 行）。`pr/port-all` 的实验树本轮只读，未改。上游 `upstream/main` 本轮未重算（`ghup` remote 只读、`upstream` 走 gh-proxy，上次读数 behind 0），换基线是另一件事，不在本轮。

**三、本次落生产** — **零**：引擎未换件、config 未改字节（`ee69ebc2` 全程不变）。本回合 **重启 1 次 / 停机 931 s / 装机 0 / 回滚 0**（窗口 14:53:33 → 15:09:04；窗口正常收尾日志因会话中断缺失，这两个数由 `downtime starts now` 与容器 `StartedAt` 反推，属**实测时间戳**，不是脚本自报）。dot4/dot8 移植、全量重编、自检、ISA 反汇编全部零停机。**装 `attn` 仍需你单独批准一次停机（估 40 s）**。

**四、进度** — **451 条 / 已结 361 / 80.0%**（本轮 +8：`P499`–`P505` + 队列行 `R108`）。队列：**R103（重开已判、已移植且过任务级门、待装机）** → R106（`gen_config` 工具链）→ R107（`AUDIT29`）→ **R108（新立：dot8 接入生产内核 + max-context 门）** → R105（`hipk`）→ R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 正文

**1. 先回答「移植 gfx906 专用的 dot8 和 dot4 两个核心」**

查完源码与 ISA 后的结论是：**这两个核心的状态不一样，不能一起说「移植完成」**。

- **dot4（`v_dot4_i32_i8`）本来就在产，而且就是硬件指令**。真正生效的实现在 `include/strata/platform/hip_compat/strata_hip.h:237`（`strata_dp4a` / `__dp4a`，宏在 `include/strata/platform/hip_compat/strata_hip.h:249`），那里写着 `#if defined(__gfx906__) … return __builtin_amdgcn_sdot4(a, b, c, false)`。拆 `.hip_fatbin` 后 `src/kernels/cuda/qsa_decode_attn.cu` 的设备 ISA 有 **`v_dot4_i32_i8` 384 条、`v_mad_i32_i24` 0 条**（没有软件回退）。本轮做的是：把 W1036/A0 的 gfx906 分支同步进那份**死文件**（`include/strata/hip_compat/intrinsics.hpp:18` 是它的 `dp4a()`）、并在文件头加警示，防止下一个人再改错对象。调用侧的统一入口是 `include/strata/kernels/dp4a.hpp:42` 的 `STRATA_DP4A` 宏。
- **dot8（`v_dot8_i32_i4`）两棵树原本都完全没有**，这是真缺口。本轮在 `include/strata/platform/hip_compat/strata_hip.h` 新增 `strata_dp8a/__dp8a`（gfx906 走 `__builtin_amdgcn_sdot8(a,b,c,false)`，其它目标走 signed-nibble 标量回退），另加独立头 `include/strata/kernels/gfx906_dot.hpp` 与 `tools/gfx906_dot48_selfcheck.cu`。

**2. 我上一轮的结论整段作废（`P500`）**

上一轮我读的是 `include/strata/hip_compat/intrinsics.hpp` —— W1036/A0 提交 `79516b21` 改的那份 —— 看到它的 `__dp4a` 没有 gfx906 分支，就推出「gfx906 走 28 指令软件 fallback、补 A0 还有大收益」。**这是错的**：`build-masterp` 里**没有任何 `.d` depfile 引用 `hip_compat/intrinsics.hpp`**，它不是编译链上的文件。第一次按这个判断去打补丁（改的就是 `include/strata/hip_compat/intrinsics.hpp:18`），构建出来的二进制与旧候选**逐字节相同**（`3b758f88…`），正是这条错链的可复现证据。

与 `P493`（日志整文件 grep 会假通过）、`P496`（交接门 md5 写死旧件）同族，这是**第四次「门验的对象错了，看起来还是绿的」**。修法不是补一句说明，而是把生效路径写进 `include/strata/kernels/dp4a.hpp` 的注释里，并给死文件加顶部警示。

**3. 验证链本身也修了（`P502`）：两次「0 条指令」都是假的**

第一次用 `ninja -t commands` 把 `-c` 换成 `-S`，base 与 a0 两份 `.s` 都是 69,186 行、所有 GPU opcode 计数 0 ⇒ 那是 **host stub**，device 代码在 bundle 里。第二次对 host 可执行文件直接 `llvm-objdump -d --mcpu=gfx906`，同样 0 条。正确链路（写进 `albus/w1042/isa_final.sh`）：`llvm-objcopy --dump-section .hip_fatbin=fat.bin` → `clang-offload-bundler -list -type=o` 取 `hip-amdgcn-amd-amdhsa--gfx906` → `-unbundle` → `llvm-objdump -d --mcpu=gfx906 code906.o`。

源码侧 OPT 的 score 路径在 `src/kernels/cuda/qsa_decode_attn.cu:83`（`dot8_dp4a`），新核心定义落在 `include/strata/kernels/gfx906_dot.hpp:38`。修好之后的两组硬数据：自检 `v_dot4_i32_i8=1 / v_dot8_i32_i4=1`；生产 `qsa_decode_attn.cu.o` `v_dot4_i32_i8=384 / v_dot8_i32_i4=0 / v_fmac_f32=7725`。**规矩**：GPU 指令数只在拆包后的设备 code object 上数。

**4. dot8 核心的验收：真跑、真对、真发指令（`P501`）**

`tools/gfx906_dot48_selfcheck.cu` 在卡上跑了 8192 个随机三元组 + 9 个边界（全 0x7f、全 0x80、单 lane、累加器正/负溢出），device 侧 `HW_device=1`，**`dot4_bad=0 / dot8_bad=0`**；溢出用例回绕到 `-2147419148 / -2147483464`，证明 `clamp=false` 是回绕而非饱和，与 CUDA `__dp4a` 的模 2^32 契约一致。`HW_host_macro=0` 只是因为在 host 编译阶段 `__gfx906__` 未定义 —— 打印位置本身也骗过我一次，所以改成从 device kernel 回读。

外证（上网核实，用于校准而非代替测量）：`llvm-mc -mcpu=gfx906` 与 ROCm `AMDGPUAsmGFX906` 都列 `v_dot4_i32_i8` / `v_dot8_i32_i4`，而 **`v_dot4c` / `v_dot8c` 在 gfx906 不可用**；`gfx9-generic` 目标会排除这两条指令，所以 `--offload-arch=gfx906` 是硬前提。MI50 实测 dot8 吞吐约为 dot4 的 2×（社区 43.5 vs 21.7 TOPS），但 `GFX906_OPT_INVENTORY §8` 也记着「ALU 换指令在 gather 型 kernel 上无效」，所以**不能凭「指令更少」预测收益**。

**5. 诚实边界：dot8 还没进生产内核**

`gfx906/dot48 @ e0ce7c96` 构建的候选 `strata-0.1.57-dot48` 与 `attn` 候选 **md5 完全相同**（`3b758f88ddad25cdad236be267810a9e` / 43,452,008 B）：`strata_dp8a` 没有任何调用点，链接器把它 DCE 了。⇒ 本轮的准确说法是「**核心已移植、已验证可用**」，不是「已接入生产」。接入面按风险排序：① k8v4 的 V 侧本来就是 4-bit code，一个 int32 装 8 个值正好填 dot8 的一个操作数，但 softmax 概率 `p` 是 float，需要 `p→int4` 量化（**新误差源**，须自带锚臂 + 数值门，见 `albus/gfx906_survey/PORT_PLAN.md` §C2）；② Q4_K / IQ4 权重的 MMVQ（先核数据布局）；③ 只做诊断入口（零风险也零收益）。已立 `R108`，并把「ISA 里 `v_dot8_i32_i4 >= 1`」写成它的第一判据。

**6. R103 的移植结果（`P499`）：四道门全过，但没装机**

- **移植方式**：`port-all@62d10e25` 的 `src/kernels/cuda/qsa_decode_attn.cu` 整文件覆盖到 `k10@af797b90` —— 两树该文件在共同祖先 `e181bda5` 上逐字节相同，所以是**拷贝不是合并**；commit `deb41e12`，构建 38 s。
- **build floor**：A=`kvg` / B=`attn` 无开关 / C=`attn`+`ATTN_DP4A`，1000/8000/16000/20000 四个长度的 fp32 全词表 logits，**B≡A 四点逐字节相同**。
- **数值**：C 相对 A 的 KL = `0.00037 / 0.00345 / 0.01429 / 0.18750`，与 W1041 的 `pa5` 分支**逐位一致**（argmax 前三 same、20K DIFF 也一致）⇒ 移植行为等价，`--kv-grow` 没扰动取样面。
- **计时（生产形状，配对 2×CV）**：2.5K gpu −1.89% vs 带宽 5.97%（within noise）、8K −2.72% vs 1.34%（REAL）、16K −1.72% vs 0.36%（REAL）；attn 相位 −11.81/−11.29/−10.53% 三点全 REAL。隔离形状同 run 的 `qsa attn` 也是 −10.9…−11.3%、整条 −1.6…−2.8%。
- **任务级门**：16K / 28K（28,695 token）needle，off 与 DP4A on 两臂 **4/4 命中**、`cached_tokens=0`。

**7. 两个脚本缺陷，都已修并记账（`P503` / `P504`）**

计时 harness 把 `DEC` 改成 0 后仍无条件执行 `decode_summary` 的 `st.mean(r)`，两臂各抛 `StatisticsError`，结构化 JSON 没落 —— 改从 `window.log` 原始行重算（`albus/w1042/collect.py`；顺带发现 harness 在 `attn=` 前打了**两个空格**，写死单空格的正则会全空，又一个取样面）。移植脚本第一次构建失败时**把生产源码树留在 `gfx906/dot48` 分支**，已给 `fail()` 加自动切回 + 断言；最终 `pr/k10 @ af797b90`、脏 0 行。

**8. 外证：任务级门还不够（`P505`）**

vLLM 2026-04 的 128K needle 在 FP8 KV 下从 **91% 掉到 13%**，而延迟直方图、短上下文 eval、perplexity 全绿；RDNA4 TurboQuant 的 turbo3 `KLD@512 = 3.0985` / same-top-p 41%，needle 仍 **9/9**，原话是「短上下文 KLD 是压力指标，不是判决」。⇒ 本轮 16K/28K、单深度、fact 在开头只是**弱门**；装机前补 max-context × 3 深度 × 两臂逐 token diff，以及多跳检索。这条已并入 `R108` 的前置条件。

**9. 待你定的两件事**

1. **装 `attn`**：一次停/起 ≈ 40 s，回滚件 `kvg`（`a85743d7`）+ `tmp/w1040/cfg_w1040.bak` 在位，装机门六条判据可按 W1040 那套重跑。我建议**先补 `P505` 的 max-context 门**再装，理由是外证里 91%→13% 那种退化只在长上下文暴露。
2. **`R108` 要不要与装机合并窗口**：dot8 接入需要先做 roofline 判 attn 是否 ALU-bound；合并能省一次停机，但会破坏「一次只动一个变量」，我倾向分开。

**10. 文件**

本机 `albus/w1042/`：`reply.md`（本文件）、`port_attn.sh` / `port_dot48.sh`、`patch_intrinsics.py` / `patch_strata_hip.py` / `patch_dp4a.py`、`gfx906_dot.hpp`、`dot48_selfcheck.cu`、`isa_probe.py` / `isa_final.sh` / `probe_macros.py`、`collect.py`（`p2_raw.json` / `p2_stats.json` / `p3_needle.json`）、`land_w1042.py`、`window_w1042.sh` / `window.log` / `build.log` / `port_dot48.log`。166 上 `tmp/w1042/`：`n_{A,B,C}/` 各 4 个 fp32 dump、`isa/`（fatbin / 反汇编）、`dot48_selfcheck` 可执行、`cfgP_*.json`；`/data/bin/strata-0.1.57-{attn,dot48}` 为**未装机**候选。
