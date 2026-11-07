# W1045 报告 · 五问审计：R103 移植面 / dot4 现状 / dot8 该不该用 / K10 的 mmq 来源 / CI-CD 覆盖

> 一句话：**五个问题的答案都不乐观，而且审计过程中我自己踩了 W940 同款坑**——拆 ISA 时 `llvm-objcopy` 原地改写了在产二进制，
> 已用同 md5 副本恢复（disk = running = SNAPSHOT，health ok，零停机），并新增机械门；这正好成了第五问「CI/CD 是否全覆盖」的实证。

---

**一、生产容器（10 字段，2026-11-07 18:5x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `09:56:22Z`（17:56:22，本轮未重启） |
| 2 | 运行中引擎 | `strata-0.1.57-attn` · md5 `3b758f88ddad25cdad236be267810a9e` · 43,452,008 B（**本轮磁盘件曾被改坏后恢复，逐字节复原**） |
| 3 | config | md5 `3dde880125925d785a49da69fa1ebdfb` · `exe=/data/bin/strata-0.1.57-attn` · args 38 / env 10（**未改**） |
| 3a | args 明细（19 flag） | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细（10 个） | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1`（10 项全部未动） |
| 4 | 健康 | `/health` ok · restarts=0 · `could not map` 计数 0 · `binary_integrity.py --live` PASS（带 inode WARN） |
| 5 | 资源隔离 | `memlock=-1:-1` · `VmLck 0 kB` · `ulimit -l` unlimited |
| 6 | 显存 | used 33,618,952,192 / total 34,342,961,152 ⇒ **VRAM free 724,008,960 B（0.67 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `/data/bin` 55 件；`kvg`（`a85743d7…`）、`dot48`（**`3b758f88…`，本轮恢复源**）均在册；config 备份 `tmp/w1044/cfg_w1044b.bak`；rollback = 停容器 → `cp` 回 `cfg_w1044b.bak` → 起容器（≈45 s） |
| 8 | 本轮改动 | **引擎/config 零变更**；仅一次资产修复（恢复被改坏的磁盘二进制 + 把 6 个被改写的 `.o` 移出构建树）；**重启 0 次 / 停机 0 s / 装机 0 / 回滚 0** |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323 · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221`（混合树，见 §4） |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10` @ af797b90（`gfx906/lcpp-k10`，领先 2 / 落后 0，脏 0 行）。在产二进制来自 `gfx906/attn-opt @ deb41e12`；`gfx906/dot48 @ e0ce7c96`、`gfx906/port-all @ 91a7c5a4` 均未合主线。上游 `upstream/main` 本轮未重算。

**三、本次落生产** — **零**：引擎未换件、config 未改字节、源码树未提交任何 commit。本回合 **重启 0 次 / 停机 0 s / 装机 0 / 回滚 0**；唯一写操作是修复审计工具造成的资产损伤，见 §0。

**四、进度** — **467 条 / 已结 377 / 80.7%**（本轮 +6：`P517`–`P522`）。队列：~~R103 已装机~~ → R106 → R107（`AUDIT29`，**14 轮连续未审**）→ **R91（dot8 接入）** → R74（W4A4 精度门，R91 前置）→ R108（与 R91 重复，待合并）→ R105 → R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 0 先说事故：我自己在审计中改坏了在产二进制（已恢复，零停机）

拆 ISA 时执行了 `llvm-objcopy --dump-section .hip_fatbin=… /engine/strata-0.1.57-attn`，**没给输出文件** ⇒ 该命令会**原地改写输入并移除该 section**（W940 同款根因，项目记忆里明写着「disk ≠ build 就是 objcopy 原地重写」）。18:20:19 在产件从 43,452,008 B 变成 43,425,632 B、md5 `3b758f88…` → `2d2b7490…`；运行进程仍持旧 inode（`/proc/20/exe -> …attn (deleted)`，md5 仍 `3b758f88…`），服务正常，但**下次重启会加载缺设备代码的坏件**。

处置（全部零停机）：用逐字节相同的 `dot48`（`3b758f88…` / 43,452,008 B）按 `cp → .new → mv` 原子替换恢复；复核磁盘 = 运行进程 = SNAPSHOT 三方 md5 全等、health ok；坏件留证 `tmp/attn_objcopy_damaged.bin`；同一命令改写的 **6 个构建 `.o`** 已移到 `tmp/w1045/damaged_objects/`，让 ninja 下次重编。

防再犯（机械）：新增 `tools/binary_integrity.py:1`（`--live` 比对 disk/running/SNAPSHOT md5，`--self-test` **5/5**）；`albus/w1045/isa_audit.sh:1` 加双保险——拒绝对 `/data/bin/*` 操作、先复制到临时副本、并给 `llvm-objcopy` 显式输出文件；挂载 `/data/bin` 一律 `:ro`。**这件事本身就是第五问的答案**：当时没有任何一道门拦住对在产二进制的写操作。

## 1 第一问：R103 还有没有没移植的 / 移植了没落生产的 / 可继续挖的

**结论：R103 全量方案（`albus/gfx906_survey/PORT_PLAN.md:94`）只落了 B1 一条；方案里排第 2、自称「最值钱」的 B2 和排第 4 的 B3 一行都没动。**

`port-all @ 91a7c5a4` 相对共同祖先 `e181bda5` 改了 **10 个文件**（483+/93−），而在产的 `gfx906/attn-opt @ deb41e12` 相对 `gfx906/lcpp-k10` **只改 1 个文件**（`src/kernels/cuda/qsa_decode_attn.cu`，219+/23−）。逐条：

| 条目 | 落点 | 状态 | 硬证据 |
|---|---|---|---|
| A0 `v_dot4_i32_i8` 换指令 | `intrinsics.hpp` | **已判否**（`P421` 无收益），且该文件是死文件 | W1042 已纠错；硬件 dot4 本来就在产 |
| **A1 router DPP** | `src/kernels/cuda/native_router.cu`（port-all 144 行） | **未移植** | `git diff e181bda5..HEAD -- native_router.cu` 在 k10 为空 |
| A2 LDS +1 pad | `qsa_decode_attn.cu` OPT bit2 | **移植了没开** | 在产只开 bit1；`gfx906_attn_opt()` 仍在 `qsa_decode_attn.cu:1062` |
| A3 softmax DPP | 同上 bit0 | **移植了没开** | 同上 |
| **A5 Q8_GATHER8** | `src/kernels/cuda/kv_q8.cu`（port-all 15 行） | **未移植** | W1037 修过派发（`8b44f3d1`），但 k10 该文件未改 |
| A4 逐文件 max-ilp | 构建脚本 | **未做** | `PORT_PLAN.md:124` 标注「不在仓库 CMake」 |
| **B1 decode 分数 dp4a** | `qsa_decode_attn.cu` | **已落生产**（唯一） | W1044 装机，`STRATA_GFX906_ATTN_DP4A=1` |
| **B2 prefill 分数 dp4a** | `src/kernels/cuda/qsa_pattn.cu:146-181` | **未移植（任何分支）** | k10 与 port-all 对 `qsa_pattn.cu` / `qsa_prompt_attn.cu` 的 diff 均为空 |
| **B3 HC dp4a** | `src/kernels/cuda/fused_gr.cu:114-121` `dot8q()` | **未移植** | 源码仍是 8 次 `fmaf`；ISA 实测 0 条 `v_dot4`、81,240 条 `v_fmac_f32` |
| B4 GDN fp16 dot2 / C1 V half2 | `fused_gdn.cu` / V 侧 | **未做** | `PORT_PLAN.md:134` |
| W1039 三个诊断位 F16D/CTLREAD/F16Q | `qsa_decode_attn.cu` bit3/4/5 | **只在 port-all** | `port-all:1143-1145` 有，在产 `:1066-1068` 只到 bit2 |
| dot8 核心 | `gfx906/dot48` 5 文件 | **移植了没接入**（0 调用点，DCE） | `dot48` 与 `attn` 二进制 md5 逐字节相同 |

另外 `P435` 早已更正：**B1/B2 改的 `attn_chunk_kernel` 预填根本不走**，预填吃的是 `qsa_prompt_attn_batch`（fp32 `fmaf`，`src/kernels/cuda/qsa_prompt_attn.cu:353-356`）——所以 B2 不是「差一步」，是**落点还没开工**。

**可继续挖的排序**（按方案 §4.0 的可判性 × 分母）：① **B2**（prompt 分母大、attn 占 16%，`P104`）；② **B3**（HC 占 decode 窗 16.6%，`gr_q8_tail()` 已产出 q8_1 镜像，基础设施现成）；③ A1（bitwise 门，零风险）；④ A5（bitwise，但要重派发）；⑤ A2/A3 单独开关 A/B（现在与 DP4A 混在一个 bitmask 里，一次只能开一位）；⑥ A4。

## 2 第二问：dot4 到底用硬件还是软件

**两者同时存在，按操作数符号分流；硬件是绝对主力，dot8 全树 0 条。**

生效层 `include/strata/platform/hip_compat/strata_hip.h:237-251`：`strata_dp4a(int,…)` 在 `__gfx906__` 下走 `__builtin_amdgcn_sdot4(a,b,c,false)`（**硬件**）；`strata_dp4a(unsigned int,…)` 在 `:246-250` 是 **4 次逐字节乘加的软件回退**。W1042 曾经读错的 `include/strata/hip_compat/intrinsics.hpp:18` 不在任何 depfile 里（死文件）。

逐 TU 拆 `.hip_fatbin` 反汇编（**实测**，`albus/w1045/isa_audit.sh:1`；整机 fatbin 28 MB 只出 235 行是错误取样面，必须单 TU 拆）：

| TU | `v_dot4_i32_i8` | `v_dot8_i32_i4` | `v_mad_i32_i24` | `v_fmac_f32` |
|---|---|---|---|---|
| `qsa_decode_attn.cu.o` | **384** | 0 | 0 | 7,725 |
| `iq_kernels.cu.o` | **44,746** | 0 | 34 | 6,143 |
| `native_mmvq.cu.o` | **37,464** | 0 | 195 | 6,830 |
| `fused_gr.cu.o` | **0** | 0 | 87 | **81,240** |
| `kv_q8.cu.o` / `moe_mmq.cu.o` | 0 | 0 | 0 | 8 / 4 |

⇒ 硬件 dot4 合计 8 万余条，软件痕迹（`v_mad_i32_i24`）不足 0.5%；**真正的问题不是「硬件还是软件」，而是 `fused_gr` 一条 dot4 都没有**——它就是 B3 真空。dot8 核心虽在 `gfx906/dot48` 自检通过（8192 随机 + 9 边界 0 失配、自检 ISA `v_dot8=1`），但**在产二进制 0 条**，因为被链接器 DCE。

## 3 第三问：dot8 要不要用起来

**要试，机主判断对；但队列里早有 `R91`（接入六子任务）和它的前置 `R74`（W4A4 精度门），我上一轮又立了 `R108` 属于重复，**建议合并去重**（本轮只出结论，未改队列行）。**

上网核到的硬外证（skyne98 gfx906 实测、ROCm `AMDGPUAsmGFX906.html`、LLVM AMDGPUUsage）：
- `v_dot8_i32_i4` 在 gfx906 可用；`dot4c/dot8c` **不可用**；`gfx9-generic` 目标会排除这些指令 ⇒ 构建必须 `--offload-arch=gfx906`。
- 4 卡实测 **sdot8 ≈ 44 TOPS vs sdot4 ≈ 22 TOPS（2×）**；ILP4 下 86 vs 43 TOPS ⇒ 要保持多个独立累加器。
- 32 位累加器会溢出，`clamp=false` 回绕（W1042 自检已验）。
- 建议「**仅当量化/布局支持 4-bit 打包时才用**」。

两条接入路线：**(a) Q4_K 权重的 MMQ**（权重本就 4-bit，只需把激活从 Q8_1 降到 int4）＝ `R91` 路线，误差源单一；**(b) k8v4 的 V 侧 4-bit**（`PORT_PLAN.md:230` C2），但 softmax 概率是 float、要 `p→int4`，引入新误差源 ⇒ 不推荐先做。

**零停机三步预注册（跑之前写死，不占 GPU）**：
1. **微基准判上限**：复用 `tools/gfx906_dot48_selfcheck.cu` 加 ILP4 吞吐与 12 head × 32 段形状的 roofline。`GFX906_OPT_INVENTORY §8` 已记「ALU 换指令在 gather 型 kernel 上无效、dp4a 已满速」——若确认 memory-bound，dot8 收益上限为 0，直接判否，省一整轮停机。
2. **离线 W4A4 精度门（`R74`）**：不动内核，用 numpy 模拟 int4 激活量化，算相对 Q8_1 的 KL / top-1；过门才谈工程。
3. **才做内核接入（`R91` P1–P6）**：单变量 A/B + 自带锚臂数值门 + 回滚，与 `R108` 合并。

## 4 第四问：K10 的 mmq 移植的哪里

**它不是「移植新 mmq 算法」，是 llama.cpp 升 pin 时的 API 对齐；而且现在是混合树。**

`fa8e6761` 提交 message 逐字（`git show` 实测）：`mul_mat_q_case<type> → <type, GGML_PREC_Q8>`（llama.cpp **#30168**）25 处、`ggml_cuda_mmq_get_config(..,cc) → (..,cc,GGML_PREC_Q8)` 5 处、`new_pool_for_device` 加 ctx 1 处、`cmake/strata_ggml_tq_overlay.cmake` 改为探测 write-back 签名。共 6 文件 39+/33−，`src/prefill/moe_mmq.cu` 的 25/25 行就是这些签名改动（**不是算法**）。

`mmq*` 文件来自上游 commit **`4c1004c49221b07c3b8108977e3d1991fc9f45cc`（2026-10-19）**，GitHub API 核实为 **`cuda: cap MMQ Stream-K blocks at available work (#30553)`**，只改 `ggml/src/ggml-cuda/mmq.cuh` 一个文件（小矩阵下限制 Stream-K block 数）。而生产主体已升到 **b12180 = master `bcb01528`（2026-11-06）** ⇒ **主体领先、mmq 文件停在 10-19 的混合树**。

**有没有更好的移植：有，且可枚举**。GitHub API 列 `mmq.cuh` 在 4c1004c 之后还有 5 个提交：`1a24df16`（10-23，**#30837「Enforce DP4A MMQ tile height multiple of warp size」——wave64 的 gfx906 直接相关**）、`c49edf09`（10-25 #29948 fuse FFN gate/up+GLU）、`eb4e244b`（10-29 #31373 RDNA4，与我们无关）、`5ce06fc7`（11-05 #31296 NVFP4 fuse）、`69ee2ecc`（11-05 #31047 MoE 布局线性化）。

本树自身的优化口子（源码核实）：`src/prefill/moe_mmq.cu:386` 的 `pick_J()` 自己遍历 `J=8..128`，而上游已有 `ggml_cuda_mmq_get_J_best()`；上游 `GGML_CUDA_MMQ_PREC` 的 q4 激活分支只在 Blackwell MMA 可用，gfx906 走不了。**但换 mmq 要重编 + 数值门 + A/B，不能盲目跟**——先单独评 #30837 的 tile-height 约束在 wave64 上是否改变我们的 J 选择。

## 5 第五问：CI/CD 走了没有，覆盖全不全

**结论：没有全覆盖，而且缺口可逐条枚举。** 按 `strata-ci-cd` 技能的 13 节点拓扑，GitHub 那段只做静态检查（workflow 头自述 `deliberately not a build`），编译/装机/A/B 全在 166 手工。

| 检查 | 实测 | 判定 |
|---|---|---|
| 触发白名单 | `downstream-gate.yml`：分支 `main` / `gfx906/mi50` / `ci/**`；paths `src/**` `include/**` `CMakeLists.txt` `ci/**` + workflow 自身 | **`tools/**` 不在 paths** |
| 最近 20 次 Actions run | 全部 11-05 / 11-06，最新 sha `e181bda5`；`af797b90`(kvg) / `deb41e12`(attn) / `e0ce7c96`(dot48) **一次都没有** | **今天（11-07）CI 零触发** |
| 分支推送 | 三个分支都已推 `origin`，但都不在白名单 ⇒ 不触发 | 已推 ≠ 已验 |
| pre-push 钩子 | 只装在 `pr/strata-fork`（mi50 树）；**`pr/k10/.git/hooks/pre-push` 不存在** | 这些 push 连 `round_gate.py --ci` 都没跑 |
| `deploy.sh 0/8 gh_gate` | `ci/deploy.sh:41` 要求「该 sha 有绿 run」 | W1040 / W1044 都走**手工停/起**，没经过 |
| `deploy.sh 3.5/8 evidence gate` | `ci/deploy.sh:96` 存在 | 本机 `tools/deploy_gate.py` 手工补跑（六条 PASS），**不是装机流程强制** |
| 脚本/补丁版本控制 | `deploy/`、`albus/`、本机 `tools/` **都不是 git 仓库**；`window_w1044.sh` / `finish_install.sh` / `judge.py` / `kl_extract.py` / `longctx_needle.py` 的 `git ls-files` 计数全为 0 | 只有 `gfx906/dot48` 的 5 个文件进了 git；`tmp/w1044` 另 13 个脚本**未版本化** |
| 权威件 | `mirror_check.py --sync` 7 件逐字节推 166 PASS | 是**同步**，不是版本化 |

⇒ 五条缺口：① 装机分支无 CI run；② `gh_gate` 未走；③ 窗口/判据脚本未入版本控制；④ `pr/k10` 缺 pre-push 钩子；⑤ `tools/**` 改了也不触发 CI。**§0 的 objcopy 事故是第六个实证**：没有任何一道门拦住对在产二进制的写操作，靠人工事后发现。

建议按成本排序：把窗口/判据脚本收进 `ci/**`（或把 `tools/**` 加进 paths）、给 `pr/k10` 装 pre-push、`binary_integrity.py` 进收工 11 硬门、装机前显式跑 `gh_gate` 或登记豁免、`R108` 并回 `R91`。

**边界**：本轮只读审计 + 资产修复，未编译、未重编、未提交、未停机；上游 mmq 的 5 个提交只做了 API 级核实，没有评估合入代价；dot8 的 roofline 与 W4A4 门都还没跑（属建议，不是结论）。`audit_scope §A` 现为 **14 轮连续未审**（阈值 8，仍 FAIL）。
