# W912 · ki 的 gfx906 内核要不要移植（逐文件判决）+ 四节现场

> **【AUDIT24 P1 · 2026-11-04】§121「领先 37 / 落后 0」是 stale ref 的产物**：当时 `upstream/main` 未 fetch。
> `W917` 实测我们**落后上游 708 条**；`W948` 又指出"三家 fork 比我们旧"的判据也不成立。
> ⇒ 任何以"我们已是 0.2.9 最新"为前提的判断，都要按 `R90` 的基线升级重新评估。

> 2026-11-03 20:5x。零停服。源码：`~/routeK_up`（ki 的 vLLM gfx906 fork，非 git 目录，副本）。
> 外部核对：Docker Hub `unverbraucht/vllm-gfx906`（自述 "maintained line KIntegrated/vllm-gfx906-mobydick"）、
> `0c33/mi50-vllm-lab`、`nlzy/vllm-gfx906`（祖先）README。

---

## 0 判决（先给结论）

**整包不移植；逐文件看只有 1 个候选，而且只能取"机制"不能取"内核"。**

| ki 文件 | 行 / 内核 | 算术 | 我们的对应 | 判决 |
|---|---|---|---|---|
| `csrc/rocm/dense_gemv_gfx906.cu` | 1431 / 7 | `__ockl_fdot2`（fp16，**2 MAC/指令**） | `native_mmvq` + iq mmvq（**6 种量化格式**） | **不移植**：格式我们更全；decode 是 1.78 MAC/B 的带宽地板，加宽指令不减字节 |
| `csrc/rocm/moe_q_gemm_gfx906.cu` | 910 / 2 | `fdot2` + **AWQ/GPTQ W4A16**（int32+exllama shuffle+fp16 scales+打包零点）+ CAS 原子累加 | tiled MMQ（**dp4a，4 MAC/指令**）+ gather | **不移植**：格式要重打包 77 GB；算术密度只有我们一半 |
| `csrc/gfx906_fa/kernel/fattn-q8.cuh` | 1281 / 1 | **`sdot4`**（int8 Q8-KV 点积，`static_assert(nbatch_K % 4 == 0, "… for sdot4")`） | `qsa_prompt_attn.cu`：**dp4a=0**，`__half2float` 36 处 + fma 30 处 | **唯一候选**：机制可取（attention 用 int8 点积），内核不可取（算法不同） |
| `fattn-q8-paged.cuh` | 776 / 2 | 同上 | `qsa_decode_attn.cu`（dp4a=0） | 同上，decode 侧收益更小 |
| `gfx906_fa_gather.cu` | 917 / 4 | — | KV gather | 不移植：我们是 host+gather 的另一套 |
| `gfx906_fa_quant.cu` | 215 / 2 | — | Q8_1 量化 | 不移植 |
| `moe_align_m1_gfx906.cu` | 173 / 1 | — | 路由 align | 不移植（占比可忽略） |

合计 **5,703 行 / 19 个 `__global__`**（不含 `benchmarks/…/harness` 的 2,258 行测试内核）。

---

## 1 为什么"整包不移植"——三条量化理由

### 1.1 算术密度只有我们一半

`__ockl_fdot2` = `v_dot2_f32_f16`，每条指令 **2 个 MAC**；`v_dot4_i32_i8` 是 **4 个**。

| 路径 | 理论上限（60 CU × 64 lane × MAC/指令 × 1.725 GHz） |
|---|---|
| `fdot2`（ki 的 dense/MoE） | 60×64×2×1.725e9 = **13.25 TMAC/s** |
| `v_dot4`（我们的 MMQ） | 60×64×4×1.725e9 = **26.5 TMAC/s** |

同卡我们实测 dot4 = **21.52 TMAC/s**（`W909`，ILP4）。ki 自述 fdot2 "峰值 ~20 TFLOPS @930MHz" ≈ 10 TMAC/s，
在模型内 **9.6 TFLOPS = 4.8 TMAC/s**。⇒ 搬过来等于**把 4 MAC/指令换成 2 MAC/指令**。

### 1.2 但真正扎心的是这句：两边都没喂饱

| | 指令上限 | 模型内实测 | 达到上限 |
|---|---|---|---|
| ki（fdot2） | 13.25 TMAC/s | 4.8 | **36%**（它自述 ~48% of 它自己的峰） |
| 我们（dot4） | 26.5（实测 21.52） | 4.55 | **21%** |

⇒ 差距**不在指令集合**，在供给率。这条与 `W909`/`W911` 完全一致：我们是"更强的指令只用到 1/5"，
ki 是"更弱的指令用到 1/3"。**换指令不解决供给。**

### 1.3 格式与算法双重不匹配

- **格式**：ki 的 MoE 是 AWQ/GPTQ **W4A16**（int32 打包 + exllama shuffle + fp16 scales + 打包零点），
  我们是 **Q4_K/Q5_1**（144 B/256 值）。`W910` 已确认我们 48 层专家 = 43×(Q4_K,Q5_1) + 4×(Q4_K,Q8_0) + 1×(Q5_K,Q8_0)。
  要吃 ki 的 MoE GEMM，得把 71.7 GiB 专家重打包成 AWQ —— 那是换模型，不是换内核。
- **算法**：ki 是 **dense flash attention**；我们是 **QSA（稀疏）+ 自研 decode attention**。整块换等于换推理算法。

### 1.4 外部旁证：vLLM 那条路在 gfx906 上的 prefill 本就不快

`0c33/mi50-vllm-lab`（vLLM + gfx906，90 W）自述：**"a cold 63k-token prompt takes 6.5 min（160 tok/s）"**，
并明确 "prefill is compute-bound"。我们生产 6.4K prompt = **720 tok/s**。
prompt 长度差 10×，不能直接相除，但两条都不支持"把 vLLM/ki 的内核搬进 Strata 能加速 prefill"。
Docker Hub 那份（KIntegrated 维护线）报的是 decode：dense 27B-AWQ **25.6 t/s**、MoE 35B-A3B-AWQ **66.1 t/s** ——
**都比我们生产的 70.7 tok/s 低或持平**，而我们的模型更大（UD-Q4_K_XL，专家 71.7 GiB）。

---

## 2 唯一候选：attention 用 int8 点积（这一条我们确实没有）

**事实对比（源码计数）**：

| | Q·K 的算术 | dp4a 用量 |
|---|---|---|
| ki `fattn-q8.cuh` | int8 × int8 → int32，`sdot4` 每次 4 个 MAC | 有（并有 `static_assert` 保证 K 维度 4 对齐） |
| 我们 `qsa_prompt_attn.cu` | `__half2float`（36 处）→ fp32 `fma`（30 处） | **0** |
| 我们 `qsa_decode_attn.cu` | `__half2float`（10 处）→ fp32 | **0** |

也就是说：**我们的 KV 虽然按 `--kv k8v4` 存（K=Q8_0、V=4-bit），但算 attention 时先把 K 反量化成 fp32 再乘。**
ki 直接在 int8 域做点积，算术密度 4×。

**为什么现在才看出来**：`W907` 把 ki 的 FA 归到"2 不同算法（QSA 稀疏 vs dense FA）"就收口了，
没有单独看**它内部用的是 sdot4**。这次逐文件读才发现这一条。

**该不该做？先量，不要先写。** 三个前置事实：
1. attention 在 prefill 的占比：6.4K tokens 时 **14.9%**（`W903`），但它是 O(L²)，长上下文会涨；
2. 我们的 QSA 是稀疏的（选块），实际点积量比 dense 少 —— 要先量"真做了多少次 dot"；
3. int8 attention 改数值（Q8×Q8 → int32 累加 → 再乘 scale），**必须过 R59 的 KL/top-1 门**。

⇒ 立 **R64**：先量长上下文（32K/131K）prefill 里 attention 的**时间占比 + 每 token 的 dot 次数 + VALU 占比**，
只有当 attention ≥25% 且是算术受限时，才把"int8 点积"接进 `qsa_prompt_attn`。

---

## 3 四节现场

### 3.1 生产容器

| 项 | 值 |
|---|---|
| 容器 / 镜像 | `strata166-407` / `strata-gfx906:0.2.9-101`（ID `d4afd5f5`，建于 2026-10-31 21:04） |
| 运行中的引擎 | `/data/bin/strata-0.1.55t`，**`md5 e0c6f250…`**（40,771,760 B），`/proc/15/exe` |
| **磁盘上的同名文件** | **`md5 a97f4479…`（40,746,776 B，mtime 2026-11-02 19:01）—— 与运行中不是同一个文件**（`/proc/15/exe` 显示 deleted） |
| config | `/data/strata-huihui-ud-iq4_xs.json`，`md5 89cd61d7…` |
| 健康 | `/health ok`，`model=qwen3.8-flash-next-ud-q4_k_xl-abliterated`，`max_context=262144` |
| 重启 | `restarts=0`，启动于 2026-11-02T18:28:48Z（已连续 26 h） |

**arg（33 项）**：`--pack /data/packs/ud-q4_k_xl --native …UD-Q4_K_XL-00001-of-00004.gguf --expert-profile /src/data/expert-profile.bin
--expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4
--prefill auto --prompt-cache-every 8192 --expert-profile-save /data/profiles/q4kxl-learned.bin --conversation-cache-mib 4096
--vision --mtp-window 8192 --vram-reserve-mib 832`（含成对值，共 33 个数组项）

**env（config 10 项）**：`HSA_OVERRIDE_GFX_VERSION=9.0.6`、`STRATA_PREFILL_CPU_SHARE=auto`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、
`STRATA_RESIDENT_HEADROOM_GIB=0.5`、`STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt`、`STRATA_GFX906_TUNED=1`、
`STRATA_CKPT_MOVE_PARK=1`、`STRATA_DECODE_TIMING=1`、`STRATA_SPEC_DEPTH=1`、`STRATA_VERIFY_NODES=1`
**套装展开 7 项**（`STRATA_GFX906_TUNED=1`）：`ATTN_QUERY_SWIZZLE / GDN_PP / HC_Q8 / SELECT_SIMT / ROUTE_TAIL_SKIP / MMQ_KQ / HIP_PROMPT_F16`
**默认 2 项**（关掉整套也在）：`GDN_HEAD / GFX906_ATTN_REDUCE12` ⇒ 运行时 **10 + 7 = 17 项生效**。

### 3.2 主线

`gfx906/mi50 @ d963c791`（2026-11-02，`spec: /data/strata-spec …`），tag `mi50-0.2.9-r27`，工作树干净（0 处改动），
相对 `upstream/main` **领先 37 / 落后 0**。

### 3.3 本次落生产

**零。** 今天全部是只读取证与评估（`W909` 指令审计、`W910` 版本/量化口径、`W911` 三路线判决、本条 `W912`）：
未改二进制、未改 config、未重启、未动 GPU 参数。唯一写操作是往 `/tmp` 放探针（容器内）。

### 3.4 唯一权威方案（`W832_OPT_PLAN_V2.md` §6.5）量化进度

`tools/progress.py`：**147 条 / 已结 83 = 56.5%**；主线（不含 28 个死块）**119 条 / 83 = 69.7%**；死块池 `0/28`。

队列：`R59 → R61 → R60 → R58 → R63 → R49 → R50 → R30′ → M3`，本条新增 **R64**（排在 R63 之后）。

---

## 4 复现

```bash
# ki 的 gfx906 内核清单与算术路径
cd ~/routeK_up
for f in $(grep -rl __global__ --include=*.cu --include=*.cuh . | grep -i gfx906); do
  printf "%-56s %5s 行 %3s 内核\n" "$f" "$(wc -l <$f)" "$(grep -c __global__ $f)"; done | sort -k2 -rn
grep -rn "sdot4\|__ockl_fdot2" csrc/rocm/*.cu csrc/gfx906_fa/kernel/*.cuh | head -20

# 我们的 attention 是不是 fp32
cd ~/strata166/pr/strata-fork
for f in src/kernels/cuda/qsa_{prompt,decode}_attn.cu; do
  echo "$f dp4a=$(grep -c '__dp4a\|sdot4' $f) half2float=$(grep -c '__half2float' $f)"; done
```
