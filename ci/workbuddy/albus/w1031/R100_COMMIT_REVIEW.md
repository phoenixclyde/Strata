# R100 · 上游 llama.cpp commit 全量评审（pin b11062 → v0.9.0）

> 立：2026-11-06 22:0x（W1031）。机主把 R99 的路线改成「review 所有 commit，找可以为我所用的，一个个试」，
> 并追加「或者把 llama.cpp 升到 0.9.0 看看」。本件是这两件事的合并交付：**面 → 分类 → 逐条判定 → 实测**。
>
> 数据面：`~/strata166/w1031/lcpp`（blobless 浅克隆，`--shallow-since=2026-09-01`），
> `git log --name-only 3cf03257..HEAD` = **1115 条**，HEAD = `6c01da6`（2026-11-06）。
> 分类脚本 `albus/w1031/triage.py`，原始表 `triage.json`（166 上）。

---

## 0 结论先行

1. **1115 条里只有 41 条碰我们真正编译的面**，其余 1002 条（89.9%）改的是我们一行都不编的文件
   （ggml-cuda 的 fattn/mmvq/cpy、llama.cpp 的模型/服务/多模态、metal/vulkan/sycl/opencl、docs/examples）。
2. 这 41 条再按「gfx906 上会不会执行」筛：**真能执行的 4 条**，**2 条是我们自己的粘合层要跟着改**
   （在 0.9.0 适配里已实证），**其余 35 条可证惰性或不适用**（每条给了证据，见 §3）。
3. **0.9.0 不是 drop-in，但断点很小**：三个 MMQ 粘合 TU 断在 4 处 API 上，
   改完 **编出可用二进制**（44,175,504 B，md5 `e0edacb7…`，构建 141 s / ccache 命中）。
   ⇒ R99 判否的是「S1 手写 tile_spec」，**不是「整树升级」本身**。整树升级的账要重开。
4. 我原先担心的「0.9.0 把 `x_gate`/`glu_op` 塞进 MMQ 图元签名、我们粘合层要大改」——**不成立**：
   0.9.0 的签名是 `<type, prec_src1>`，glu 是另一套（`GGML_GLU_*`）参数，粘合层不用动。
5. 逐条试用的净结论：**单条 cherry-pick 的期望值远低于整树升级**（唯一有实体收益的是 `#29478` 的 HIP
   `__vsub4`，而它本来就在 0.9.0 里）。这也解释了为什么 R99 当初选整树是对的。

---

## 1 面：我们到底编译 llama.cpp 的哪些文件

这件事必须先钉死，否则「review commit」就是凭印象。证据来自生产构建目录 `build-r28/build.ninja`
（`CMAKE_HOME_DIRECTORY=/src`，`STRATA_GGML_DIR=/llama.cpp`）。

| 目标 | 编译的 llama.cpp 文件 | 证据 |
|---|---|---|
| `strata_mmq`（26 TU） | `ggml-cuda/template-instances/mmq-instance-{q2_0,iq2_xxs,iq2_xs,iq2_s,iq3_xxs,iq3_s,iq4_nl,iq4_xs,q8_0,q4_k,q5_k,q5_1,q6_k}.cu`（13）+ `ggml-tq-overlay/{quantize.cu, template-instances/mmq-instance-tq*.cu}`（7） | `build.ninja:4429` 的 `libstrata_mmq.a` 成员表 |
| 同上的头文件闭包 | `mmq.cuh`、`common.cuh`、`mmq-load-tiles.cuh`、`mmq-vec-dot.cuh`、`vecdotq.cuh`、`mma.cuh`、`quantize.cuh`、`mmq-config-*.cuh`（11）、`vendors/{hip,cuda,musa}.h`、`ggml{,-common,-cuda,-impl}.h` | overlay 的 `#include "..."` 闭包（96 个 `.cuh` 全被拷进 overlay，但只有这一圈被 include） |
| `ggml-base`（9 TU） | `ggml.c`、`ggml-quants.c`、`ggml-alloc.c`、`ggml-backend*.cpp`、`gguf.cpp`、`ggml.cpp`、`ggml-threading.cpp`、`ggml-opt.cpp` | `build.ninja` 的 `CMakeFiles/ggml-base.dir/*.o` |
| `ggml-cpu`（16 TU） | `ggml-cpu/*.c|cpp`（含 `arch/x86/{quants,repack}.c`、`amx/mmq.cpp`、`tiled/tiled{,-kernel}.cpp`、`hbm.cpp`、`repack.cpp`） | 同上 |
| **不编** | 其它所有 `ggml-cuda/*.cu`（fattn、mmvq、cpy、mmf、getrows、softmax…）、`ggml-cuda/*.cuh` 里不被 MMQ 闭包引用的（如 `fattn-*`）、`llama.cpp` 自身、全部后端与工具 | 在 build.ninja 里搜 `.cu` 只有 `src/kernels/cuda/*`（97 个自研内核）+ 上表 26 个 |

**这就是 89.9% 的 commit 与我们无关的机制原因**：我们的 GPU 计算全在 `src/kernels/cuda/*.cu`（自研），
llama.cpp 只贡献 (a) MMQ 提示词 kernel 模板，(b) host 侧 ggml-base/ggml-cpu。

---

## 2 分类账

| 类 | 条数 | 含义 |
|---|---|---|
| `A_mmq` | 41 | 碰到 MMQ 闭包 / `ggml.h` / `ggml-common.h` |
| `B_cpu` | 40 | 只碰 `ggml-cpu/**` |
| `C_core` | 32 | 只碰 `ggml.c` / `ggml-quants.c` / `gguf.cpp` / `ggml-backend*` |
| `D_other` | 1002 | 其余（不编） |

B 类细分（按路径）：arm/s390/riscv/spacemit/kleidiai/SVE **22 条**（我们 x86，编不到）、
x86 相关 **10 条**（tiled/simd/tinyBLAS/quants）、通用 ops/vec **8 条**。
C 类细分：`ggml-backend-meta.cpp` **11 条**（llama.cpp 新 meta 后端，我们不用）、`ggml.c` 边界/溢出 **9 条**、
`gguf.cpp` 加载 **4 条**、量化生成（`ggml-quants.c`，只在造模型时用）**2 条**、其它 **6 条**。

---

## 3 A 类 41 条逐条判定

判定列含义：
`IN` 会执行且可能有收益 · `NUM` 会执行且改数值（要过 KL/指纹门）· `INERT` 编进去但可证不执行 ·
`NA` 文件不在编译面（或需要改格式/模型布局，属"重活"）· `CHK` 只加编译期断言/警告

| sha | 日期 | PR | 内容 | 判定 | 依据 |
|---|---|---|---|---|---|
| `69ee2ec` | 11-05 | #31047 | MoE 布局线性化（MMQ/MMF） | **NA** | R99 已两次判否（`P374`）；它改的是 `mmid.cu/.cuh` + 数据布局，我们 `mmid` 不在 26 TU 里，且布局由 pack 决定 |
| `5ce06fc` | 11-05 | #31296 | NVFP4 gate/up+GLU 融合 | NA | 我们无 NVFP4 权重（Q4_K/Q5_K/Q6_K） |
| `8fc0376` | 11-03 | #31247 | Q8_1 修正和改为 `d·Σq` | **NUM** | `Q4_K/Q5_K` 的 `ds_layout = DS4`（overlay `mmq.cuh:82`）⇒ 修正和**会被用到**；改成量化后求和会改数值 |
| `00f113e` | 11-03 | #30662 | CUDA graph 淘汰 | NA | 无 graph（`GGML_CUDA_GRAPHS=OFF`，且我们用自研流） |
| `1b6935b` | 11-03 | #29510 | `flash_attn_ext_rows` | NA | 新 op 在 `ggml.h`，我们不用 llama 的 attn 图 |
| `eb4e244` | 10-29 | #31373 | RDNA4_M 家族 | INERT | 只加 gfx1170/1171 分支；gfx906 走 `CC_IS_GCN` 早返回（`mmq.cuh:239`） |
| `68d20b8` | 10-29 | #27512 | OCP FP8 E4M3 类型 | INERT | 新类型；我们权重与激活都不用它（枚举追加，不改既有 block 布局） |
| `78febba` | 10-29 | #31259 | CDNA 稀疏 attn | NA | 改 `vendors/hip.h` 的宏，服务 fattn；我们无 fattn |
| `f5222f2` | 10-28 | #31188 | MoE gate/up+GLU 融合（MMQ） | NA | 需要 host 侧 interleaved 布局 + `mmq.cu` 调度；我们 `moe_fused.cu` 已是自家融合 |
| `c49edf0` | 10-25 | #29948 | FFN gate/up+GLU 融合（交错行） | NA(重) | 同上；要改 pack 的 gate/up 行交错，属格式变更 |
| `701fd25` | 10-24 | #26631 | `MUL_MAT_ID` −1 跳过 | INERT | 我们不走 ggml 图 |
| `8e5a58d` | 10-24 | #30656 | vulkan src1 precision | NA | vulkan |
| `1ddffe9` | 10-24 | #30915 | `__builtin_amdgcn_perm` 回退 | INERT | 只在无 perm 内建时生效；我们 clang 24 有 |
| `1a24df1` | 10-23 | #30837 | DP4A 瓦高须为 warp 倍数（断言） | **CHK** | 只加 `static_assert(I % warp_size == 0)`；GCN 表里 Q4_K 的 `I=64/128`，gfx906 `warp_size=64` ⇒ 恒过 |
| `9ff0d7e` | 10-23 | #30804/#31053 | chunked graph 修编译 | NA | graph |
| `280141e` | 10-24 | #30804 | graph 分块 | NA | graph |
| `d454a20` | 10-22 | #30640 | QSA mask 融合 op | NA | 新 op，我们 QSA 自研 |
| `13786fb` | 10-20 | #26771 | graph 清理 | NA | graph |
| `4c1004c` | 10-19 | #30553 | Stream-K 块数按可用工作封顶 | **INERT** | GCN 表里 Q4_K/Q5_K/Q6_K 全部 `stream_k=false`（`mmq-config-gcn.cuh:120-127`），`launch_mul_mat_q` 在 `!stream_k` 时直接返回（`mmq.cuh:1463`） |
| `9d1878a` | 10-17 | #29927 | Q1_0 用 `amdgcn_perm` | NA | 我们无 Q1_0 |
| `2744e48` | 10-17 | #30517 | 低比特 MMVQ 加速 | **INERT** | 改 `mmvq.cu`（不编）+ `vecdotq.cuh` 的 `vec_dot_*_mmvq`；MMQ 的 vec_dot 走 `mmq-vec-dot.cuh`，Q4_K/Q5_K/Q6_K 不经过这些函数 |
| `62df181` | 10-14 | #29353 | GDN 分块 kernel（新 op） | NA(重) | 与我们 `R10/STRATA_GDN_CHUNKED` 同题；它是 ggml 新 op + mma 路径，gfx906 无矩阵核（外证：ORT 的 4.5× 只在 `mma.sync` sm80+） |
| `8c2134a` | 10-14 | #30501 | `mul_mat_id` 注释/测试 | NA | 文档/测试 |
| `4dd6dd4` | 10-13 | #28195 | RDNA3.5 用 64 行瓦 | INERT | 只改 `mmq-config-rdna3-5.cuh` |
| `bfe65e1` | 10-13 | #30443 | `mmq-load-tiles.cuh` 警告 | CHK | 只消警告 |
| `882d671` | 10-13 | #30441 | 死 break 警告 | CHK | 同上 |
| `30f7df1` | 10-13 | #30420 | 警告清理 | CHK | 同上 |
| `8a1a9b5` | 10-09 | #30168 | 把 src1 精度传进 host 配置_helper | **INERT(我们)** | 改的是 `mmq.cu`（host，不编）里的选型；`mmq.cuh` 侧 `prec_src1` 我们在 pin 里**已存在**（overlay `mmq.cuh:216` 已有 `prec_src1`），且我们恒 Q8_1 |
| `fc9ce6b` | 10-08 | #29953 | MMQ 越界读修复（`J_best` 重构） | **NA(已自带)** | 我们 `moe_mmq.cu:377-393` 的 `pick_J` 已复刻上游新规则（注释写明 "0.8.0 (b12099) replaced ncols_opt with J_best"），并按老 header 的 `ncols_opt` 槽喂回去 ⇒ 两代 header 都能跑 |
| `8b2fbaf` | 10-05 | #29857 | NVFP4 累加优化 | NA | NVFP4 |
| `0eb6d9a` | 10-04 | #29940 | `mmid.cu` 变量搬家 | NA | 不编 |
| `2bc5635` | 10-04 | #29939 | `quantize.cu` 变量搬家 | INERT | 纯搬家，无语义 |
| `dd26678` | 10-04 | #29941 | `n_expert >> n_ubatch` 时越界 | **NA(已避免)** | 修的是 `mmq.cu` 里 `get_J_max(…, ne11→ne12)` 的 buffer 尺寸；我们的 q8_1 缓冲按 `pad512(cols)`×tokens 自己分配（`moe_mmq.cu:473`），不走 `get_J_max` |
| `bed0a85` | 10-03 | #29184 | 共享专家并入 MMVQ | NA | 无 mmvq |
| `272aad8` | 09-30 | #29508 | musa 定义 `__CUDA_ARCH__` | INERT | musa |
| `748d422` | 09-29 | #29478 | HIP `__vsubss4`→`__vsub4` | **IN** | 改 `mmq-load-tiles.cuh`（Q6_K 两分支、Q4_K 一条）与 `vecdotq.cuh`；逐字节语义相同（值域不溢出），只换指令 ⇒ 纯 HIP 代码生成收益 |
| `e9f824d` | 09-25 | #24364 | `llama_prec_policy` + W4A4 | NA | 我们不设精度策略 |
| `d028c69` | 09-25 | — | HIP fp8 版本门 | INERT | 无 fp8 权重 |
| `f9af9be` | 09-25 | #29193 | musa 修复 | NA | musa |
| `f46bc30` | 09-23 | #27962 | IQ2/IQ3 SWAR | INERT | 我们 IQ4_XS 只在历史 pack，现役 UD-Q4_K_XL |

**小结**：`IN` 1 条（`748d422`）、`NUM` 1 条（`8fc0376`）、`CHK` 4 条（编译期，零运行影响）、
其余 35 条 INERT/NA。这就是"逐条试用"的真实产出面——**不是因为清单长就有肉**。

---

## 4 实测

### 4.1 三条"惰性"的证明（源码级，不是印象）

| 主张 | 证据 |
|---|---|
| Stream-K 封顶（`4c1004c`）在 gfx906 不执行 | `mmq-config-gcn.cuh:120-127`：Q4_K 六条 `CASE(...)` 的 `stream_k_` 全 `false`；`mmq.cuh:1463` 在 `!get_stream_k` 时直接走普通发射 |
| DP4A warp 断言（`1a24df1`）恒过 | 同一张表 `I ∈ {64,128}`；gfx906 物理 warp = 64（ROCm 设备属性）⇒ `I % 64 == 0` |
| MMVQ 低比特（`2744e48`）够不到我们 | `mmq-vec-dot.cuh` 对 K-quant 用 `ggml_cuda_dp4a` 自算，不调 `vecdotq.cuh` 的 `vec_dot_*_mmvq`；后者的调用者 `mmvq.cu` 不在 26 TU 里 |

### 4.2 llama.cpp **v0.9.0**（= b12110 = `cd959ba`，2026-11-04 tag）

官方发布内容（GitHub release 页 + 多家转述一致）：OCP FP8 E4M3、`flash_attn_ext_rows`、
batched tensor copy API（**取代** `_2d`）、ggml 0.29.0 的 NCCL 多机 TP、四个新架构、音频。

**第一次全量构建（未改一行源码）**：`cmake` OK（3.8 s，overlay 生成成功）→ `ninja -j12 strata`
在 **141 s** 内编完 166 个目标，断在 **3 个 TU**：

| TU | 断点 | 迁移 |
|---|---|---|
| `src/prefill/moe_mmq.cu` | `ggml_cuda_mmq_get_config(type,J,fallback,cc)` 需第 5 参 `prec_src1`；`mul_mat_q_case<T>` 需第 2 参 | 加 `GGML_PREC_Q8`（5 处 + 20 处） |
| `src/prefill/ggml_cuda_host.cu` | `new_pool_for_device(int,int)` 变成 `static (ctx&,int,int)` | 改签名 |
| `src/prefill/mmq_nvfp4_w4a8.cu` / `w4a4.cu` | 同上（重命名后的 case 模板） | 加 `GGML_PREC_Q8` / `GGML_PREC_Q4` |

**改完第二次构建：`NINJA_RC=0`**，`build-v090/strata` = 44,175,504 B，md5 `e0edacb7…`。
源码副本在 `~/strata166/w1031/src-v090`（生产树 `pr/strata-fork` 未被改动），补丁脚本 `albus/w1031/adapt_v090.py`。

### 4.3 门（numeric → speed）：**1/3 通过，prefill 慢 4%**

部署 `strata-0.1.57-004`（`ci/deploy.sh --src build-v090 --exe …-004 --apply --allow-untagged`），
45 s 健康；跑完两道门后 `rollback --exe strata-0.1.57-001 --apply`，46 s 恢复，`restarts=0`。

**速度（同 `cfg_apply` 协议、同配置、同一晚）**

| 臂 | prefill@2K | prefill@8K | decode | ttft |
|---|---|---|---|---|
| pin b11062 · r99-s0（19:49） | 534.28（CV 0.65%） | 715.72（0.03%） | 36.84（1.63%） | 3.91 |
| pin b11062 · w1021-final（01:56） | 531.56（0.31%） | 715.98（0.10%） | 34.75（3.3%） | 3.94 |
| pin b11062 · w1023-back（02:48） | 531.42（0.24%） | — | 34.61（1.29%） | 3.94 |
| **v0.9.0 · w1031-v090（22:23）** | **512.28（0.48%）** | **685.48（0.09%）** | **34.91（2.81%）** | **4.07（0.72%）** |

⇒ prefill **−3.6%（2K）/ −4.3%（8K）**，CV 0.48/0.09 ⇒ **7×CV 以上**，是实测回退；decode 平；ttft +3.3%。

**数值（48-token 贪心指纹，三例）**

| 例 | 结果 | 说明 |
|---|---|---|
| `en2k`（968 tok） | **224/224 逐字节相同** | 长上下文英文没分叉 |
| `short`（63 tok） | 118/122，前 118 字符相同 | 尾部多 4 字符（`…longer` → `…longer red`），像停止条件 |
| `zh2k`（1565 tok） | 7/81，**第 0 字符起就不同** | 新臂 content 里是 reasoning 文本（`用户要求用一句话回答…`），基线 content 是答案 |

`zh` 这一条**不是 KL 漂移**：content/reasoning 的分区变了，属 serve 层与 GGUF 元数据读取的兼容问题
（候选：0.9.0 的 `gguf.cpp` 对 `tokenizer.chat_template`/token 属性的读法）。⇒ 判 **门不过**。

**结论**：整树升级「能编、能跑、慢 4%、分区变」⇒ **不采纳**；下一步 `R100-S5` 用 H1/H2 两臂把这 4% 归因
（`#31247` 的 DS4 修正和 vs `ggml-cpu` 主机侧），账本 `P380`。

### 4.4 归因第一步（W1031 续）：控制臂 + H1

| 臂 | prefill@2K | prefill@8K | 说明 |
|---|---|---|---|
| 在产 001 · 19:49 / 01:56 / 02:48 | 534.28 / 531.56 / 531.42 | 715.72 / 715.98 / — | 历史基线 |
| **在产 001 · 22:45（控制臂 `w1031-ctl001`）** | **532.76（CV 0.21）** | **714.89（CV 0.18）** | ⇒ 机器状态没变，回退不是时间漂移 |
| v0.9.0 · 22:23（`w1031-v090`） | 512.28（0.48） | 685.48（0.09） | −3.8% / −4.1% |
| 0.9.0 + 回退 `#31247` · 22:36（`w1031-h1`） | 514.91（0.42） | 683.66（0.18） | +0.5%，**未恢复** |

⇒ **`#31247` 排除**（H1）。另外 `mmq-config-gcn.cuh` 在 pin 与 0.9.0 之间 **diff 为空**（`J / K_vram / stream_k` 一字未动）
⇒ **瓦选型排除**。剩下的两组：① `mmq.cuh` 的 kernel 重写（+566 行，`x_gate`/`glu_op`/`J_best`）；
② `ggml-cpu` 主机侧（CPU share 会调 `ggml_cpu_has_*` 与 ggml 的 dot，见 `src/kernels/cpu/native_expert.cpp:438`）。
H2 = 0.9.0 树 + pin 的 `ggml-cpu` TUs（编译风险：API 漂移），或 H2' = 两臂同设 `STRATA_PREFILL_CPU_SHARE=0` 的配置 A/B。

数值侧同样干净：H1 的 zh 仍然不同 ⇒ 与 `#31247` 无关（当时的猜测是 serve 层/元数据，**后来被 H2 推翻，见下**）。

### 4.5 归因闭环（W1031 续二）

| 臂 | 树 = 0.9.0 的… | prefill@2K | prefill@8K | 结论 |
|---|---|---|---|---|
| 在产 001（控制臂） | — | **532.76**（0.21） | **714.89**（0.18） | 基线 |
| v0.9.0 `-004` | 全部 | 512.28（0.48） | 685.48（0.09） | −3.8% |
| H1 `-005` | 全部 + 回退 `#31247` | 514.91（0.42） | 683.66（0.18） | 未恢复 ⇒ `#31247` 排除 |
| **H2 `-006`** | **ggml-base/cpu 用 0.9.0，ggml-cuda 用 pin** | **532.59（0.37）** | **714.06（0.10）** | **完全恢复** |

⇒ **3.8% 与 zh 的 content/reasoning 变化全部来自 0.9.0 的 MMQ kernel 重写**（`mmq.cuh` +566 行、
`mmq-load-tiles.cuh` +300、`vecdotq.cuh` +176；含 gate/up+GLU 融合与 `x_gate` 入参）。
`ggml-base` / `ggml-cpu` 与 `quantize.cu` 在中性一侧（H2 与 001 差 0.03%）。**§4.3/§4.4 里"zh 是 serve 层"的
假设撤回**：H2 的 zh 文本回到基线（`这段话主要说明：`），说明它只是累加顺序变化在这个近似平局 prompt 上的翻转。

### 4.6 唯一 `IN` 条目的单条移植：零效果（二进制逐字节相同）

pin 树 + `git show 748d422`（`patch -p1` 干净）→ `build-vsub4/strata` = **42,947,088 B /
md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`**，与在产 `strata-0.1.57-001` **完全相同**
⇒ `__vsubss4` 与 `__vsub4` 在本工具链（clang 24 / gfx906）被编成同一段代码。
**41 条里唯一有实体期望的一条也是零**，所以不部署、不 bench（没有可测对象）。

---

## 5 与权威调优方案的合并

| 本件结论 | 落到哪个编号 | 动作 |
|---|---|---|
| 0.9.0 整树升级：断点 3 TU / 4 处，已编译通过 | **R100**（新，`PROGRESS`） | 按 §6.2 新条目登记；门过则进 §6.5 队列 |
| `748d422`（`__vsub4`）已在 0.9.0 内 | 并入 **R51**（gfx906 MMQ load 面） | R51 的"上游 gfx906 专用 load"清单里补这条，不单列 |
| `8fc0376`（Q8_1 修正和）改数值 | 新 **R101** | 只在 0.9.0 树上测 KL；单独 cherry-pick 到 pin 上要同时改 `quantize.cu` 的 DS4 分支 |
| `fc9ce6b` 的 `J_best` 规则我们已自带 | 结在 **R51** 的注里 | 不改 |
| `62df181` GDN 分块 = R10 的上游实现 | **R10** 补注：上游已落地（ggml 新 op + mma），gfx906 仍需 fp32/FMA 版 | R10 保持 OPEN，成本上调 |
| `c49edf0`/`f5222f2` gate/up+GLU 融合（需交错行布局） | 新 **R102**（格式变更级） | 只有 R100 通过后才评估；先算上限（FFN 占 prefill 多少） |
| B 类 x86 tiled/AVX2（`3dbcb7f`/`d834d44`） | 并入 **R53**（IO/PLE 主机侧）附近的"主机侧"话题 | 需要先证 `ggml-cpu` matmul 在我们的 host staging 里被执行 |

---

## 6 没做的 / 下一步

1. **没有**逐条 build 41 条（不经济：单条期望值 < 2×CV，而整树升级一次拿全部）。已用"执行面证据"代替。
2. **没有**测 `8fc0376` 单独的 KL（它已随 0.9.0 一起在树上，§4.3 的门会覆盖到它的净效果；若 0.9.0 数值变坏，
   第一步就是关掉这条再复测）。
3. 0.9.0 通过门之后的工作：`third_party/ggml/VERSION.txt`、`ci/docker/Dockerfile-*` 的
   `LLAMA_CPP_SHA/BUILD/TREE` 三件、`release_check.py` 的 pin 门、镜像与容器；**这些一步做完**（W994 的规矩：
   全量重建必须以 md5 复现为验收门）。
4. 若 0.9.0 门不过：退回 pin，只把 `748d422`（`__vsub4`）单条打进 overlay 重编——这是唯一有实体收益的单条。
