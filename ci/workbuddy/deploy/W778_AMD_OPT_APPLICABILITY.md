# W778 AMD/Intel 优化的可用性判定（逐条实测）+ 一个意料之外的发现

> 2026-10-24 01:0x-02:2x · 机主三问：①那些 AMD 优化真没法在 gfx906 上试吗 ②HC_Q8 落生产了吗 ③继续优化
> 口径：每条结论要么是源码行号，要么是本机实跑（同 config、唯一 nonce、`reused=0`、M 档 3-5 runs）。

---

## 0 三个问题的直接回答

1. **不是"都没法试"——我上一轮的措辞是错的。** 真正不能试的只有 **3 项**（硬件 cc 分派 / 构建未链接 hipBLASLt / 不同后端）。**能试的 12 项我全试了**，7 项有代码路径可跑的**全部无收益**（±0.5% 内），5 项在**我们的模型上根本没有代码路径**（不是不能开，是开了也没东西跑）。
2. **HC_Q8 已落生产**：`config.env = {…, "STRATA_HC_Q8": "1"}`，容器 `strata166-407` 跑 `strata-gfx906:0.2.3` / `0.1.48.1`，`expert_slots 9901`，`verify_config PASS=29 FAIL=0`。证据在 §5。
3. **继续优化做了 12 组车**，其中挖出一个比所有开关都重要的东西：**7.3K 的对话完全不复用，19.5K 的第二轮能复用 16,384 token、从 40.4 s 降到 8.1 s**（§4）。

---

## 1 「能不能试」的正确定义：三种门控

`src/core/arch_defaults.cpp` 里那张表是**默认值表**，不是能力表——它只决定"gfx1151/gfx12 上默认开哪些 env"，每一项**在任何卡上都能用 env 强制开**。真正拦住我们的是另外三种：

| 门控类型 | 含义 | 本机有几项 |
|---|---|---|
| **软门控**（env 可强制开） | 表里默认只给 gfx1151/gfx12，但 env 设了就生效 | **12 项**，已全测 |
| **无代码路径** | 模型没有对应结构 / 不用对应特性，kernel 不会被调用 | 5 项（GDN 族 5 个、CVEC_FUSE） |
| **硬不兼容** | 编译期后端不同 / 硬件能力不同 / 构建没链接 | **3 项**，见 §3 |

---

## 2 软门控的 12 项：实测结果

### 2.1 有代码路径的 7 项（本轮新测，M 档 3 runs）

基线 = 0.2.3 + HC_Q8：**prompt 486.6 tok/s / decode 61.3 tok/s**

| env | 作用（源码注释原文） | prompt | Δ | decode | Δ | 判 |
|---|---|---|---|---|---|---|
| `STRATA_Q8_PACKED=1` | packed Q8_0 decode layout（gfx1151 +2.3%） | 486.7 | +0.02% | 61.6 | +0.49% | 无效 |
| `STRATA_Q6_PACKED=1` | packed Q6_K heads | 486.2 | -0.08% | 61.5 | +0.33% | 无效 |
| `STRATA_MMVF_ROWS=1` | bf16 multi-row GEMV, 4 rows/block | 486.2 | -0.08% | 61.4 | +0.16% | 无效 |
| `STRATA_LFUSE=1` | fewer launches around shared expert + KV append | 487.7 | +0.23% | 61.2 | -0.16% | 无效 |
| `STRATA_QFUSE=1` | activation q8_1 images written by producers | 486.2 | -0.08% | 61.5 | +0.33% | 无效 |
| `STRATA_PLE_BATCH=1` | verify window's PLE key/value projections at once | 486.7 | +0.02% | 61.5 | +0.33% | 无效 |
| `STRATA_TOPK_REG_MIN_BLOCKS=4096` | register top-k from 16K cells（gfx1151 路由） | 487.8 | +0.25% | 61.4 | +0.16% | 无效 |

**7/7 无收益**，全部落在 ±0.5% 内（M 档臂内波动本身就有 1%）。
原因可推断：这批是给 **RDNA3/4**（wave32、大 L2、新指令）写的调度与打包优化，gfx906 走的是 **wave64 + GCN** 分派，吃不到。

### 2.2 无代码路径的 5 项（不是"不能开"，是"开了没东西跑"）

| env | 为什么无路径 |
|---|---|
| `STRATA_GDN_HEAD / GDN_PP / GDN_CONVL2 / GDN_NOY / GDN_SPLIT` | **我们的模型没有 GDN 层**。实测 pack `index.txt` 里 `gdn` 出现 **0 次**，只有 `ssm` 252 / `conv` 38（Qwen3.8-Flash-Next 是 SSM + attention 混合，不是 GDN） |
| `STRATA_CVEC_FUSE` | 只在加载 control vector 时生效，我们不用 control vector |

### 2.3 已判过、本轮不重测的 4 项

`STRATA_EXPERT_V2`（P36 REJECTED）· `STRATA_TSUM`（P37 REJECTED）· `STRATA_SH_STREAM`（P40 REJECTED）· `STRATA_ATTN_LANECELL`（`W775delta_W6` 源码级判不发车）。

---

## 3 硬不兼容的 3 项（这次给到确切源码行）

### 3.1 RDNA3 / RDNA4 的 MMQ 路径 —— 改不了，也没有 env

`third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cuh:229`：

```cpp
static ggml_cuda_mmq_config ggml_cuda_mmq_get_config(type, J, fallback, cc) {
    if (GGML_CUDA_CC_IS_AMD(cc)) {
        if (GGML_CUDA_CC_IS_GCN(cc))  return ggml_cuda_mmq_get_config_gcn(type, J, fallback);   // <- 我们命中这里
        if (GGML_CUDA_CC_IS_CDNA(cc)) return ..._cdna(...);
        if (GGML_CUDA_CC_IS_RDNA4(cc))return ..._rdna4(...);
```

`common.cuh:71`：`#define GGML_CUDA_CC_VEGA20 (GGML_CUDA_CC_OFFSET_AMD + 0x906)  // MI50/Radeon VII, minimum for dp4a`

- `cc` 来自 `cudaDeviceProp`（硬件），**没有任何 env 能覆盖**。
- 唯一办法是改 ggml 源码硬塞 rdna4 配置 —— 那些 tile 是按 **wave32** 设计的，wave64 上会读错 tile 布局（不是慢，是算错）。
- **结论：不做。要做得上游改。**

### 3.2 hipBLASLt 调优表 —— 我们的构建里根本没链接

`CMakeLists.txt:729`：

```cmake
if(STRATA_ENABLE_HIP AND STRATA_HIPBLASLT_AVAILABLE)
    target_link_libraries(strata_prefill PRIVATE roc::hipblaslt)
```

而 `CMakeLists.txt:78` 原文：「STRATA_HIP_GFX906 and STRATA_ENABLE_HIP are **separate backends**; enable only one」。
gfx906 构建 `STRATA_ENABLE_HIP=OFF` => **roc::hipblaslt 没链接进二进制**。
上游自己也承认这条路在无表时是空转——`arch_defaults.cpp` 注释：`STRATA_HCD_EXACT ... needs the gfx1151 hipBLASLt tuning table, finds none on gfx12, says so on every start and does nothing`。

**结论：不做。**（`STRATA_HCD_EXACT` / `STRATA_PF_PAD` 由此一并作废。）

### 3.3 Mac Metal / Intel Arc SYCL —— 不同的引擎二进制

Metal 走 `metal/` 后端，Arc 走 `linux-x86_64-sycl` 独立包。这两条不是"参数关掉了"，是**另一个程序**。**结论：不做。**

---

## 4 意料之外：8K 以下的对话，一次都没复用

### 4.1 实测

用同一段前缀、只改结尾三个字，连发三轮（`/v1/chat/completions`，greedy）：

| prompt | 轮次 | `reused` | `prompt_ms` |
|---|---|---|---|
| **7,342 tok** | 1 / 2 / 3 | **0 / 0 / 0** | 15,250 / 14,887 / 14,919 |
| **19,467 tok** | 1 | 0 | **40,406** |
| 19,467 tok | 2 | **16,384** | **8,079** |
| 19,467 tok | 3 | 16,384 | 8,043 |

**19.5K 的第二轮快 5 倍；7.3K 的第二轮一点没快。**

### 4.2 机制

- `conversation_cache` 确实在工作：`parked` 从 0 涨到 2、`bytes` 涨到 655 MB —— **它在存快照，但从不 restore**。
- 复用实际来自 `--prompt-cache` 的 **checkpoint**，而 checkpoint **只能落在 chunk 边界**（chunk = 8192）。
- **7,342 token 连一个完整 chunk 都没跨过 => 没有任何 checkpoint => 零复用。**

### 4.3 两条弯路（都已试过，别重走）

| 尝试 | 结果 |
|---|---|
| `--prompt-cache-every 2048` | **完全无效**。7.3K 仍 `reused=0`、19.5K 仍 `reused=16384`。因为 checkpoint 必须落在 chunk 边界，2048 不是 |
| `--prefill 4096`（降 chunk 造边界） | **复用仍为 0，且预填变慢 12.6%**（17,172 vs 15,250 ms）。chunk 变小 => 更多 chunk 切换 |

### 4.4 影响面（这是真问题）

Open WebUI 日常对话大多 **2-8K token**，正好全部落在"无复用"区间：**每问一句就从头读一遍 7 千 token，多花 15 秒。**

这条不是"调个参数"能解决的——它需要引擎在 chunk 边界之外也能设 checkpoint（`--prompt-cache-tail` 只覆盖"接近 prompt 末尾的已有边界"，对我们这种"只有一个未满 chunk"的情况同样无效，且 P21 已判无效）。**属上游机制问题，建议报 issue，不要在本机硬改。**

---

## 5 HC_Q8 的落地证据

| 检查点 | 值 |
|---|---|
| `config.env` | `{"HSA_OVERRIDE_GFX_VERSION":"9.0.6","STRATA_PREFILL_CPU_SHARE":"0","STRATA_RESIDENT_HEADROOM_GIB":"0.5","STRATA_HC_Q8":"1"}` |
| 注意 | 它**不在** `docker inspect .Config.Env` 里 —— 是 **serve 注入引擎子进程**（与 register 里 P23/P65 同一条通道） |
| 容器 | `strata166-407` / `strata-gfx906:0.2.3` / `strata 0.1.48.1` |
| `/metrics` | `expert_slots 9901`（未开时 9732）· `vram_free 642` |
| 固化 | `verify_config.py` **PASS=29 FAIL=0**；`gen_config.py --live` **无差异** |
| 收益（复核） | prompt S +0.66% / M +0.60% / L +0.67%；decode +2~5%；槽 +169 |

---

## 6 本轮另外 4 组车（全否）

| 项 | 实测 | 判 |
|---|---|---|
| `--ple-inflight 512` | 486.4 / 61.1（基线 486.6 / 61.3） | -0.04% / -0.33%，无效。PLE 读已被异步 I/O 线程掩盖 |
| `--host-core last` | 487.6 / 61.4 | +0.21% / +0.16%，噪声内 |
| `--aux-cpus auto` | 483.5 / 61.4 | **-0.64%** / +0.16%，不采纳 |
| `--pool-tasks 42/126`（上一轮） | 483.4 / 484.2（默认 484.3） | 无效，CPU 侧是算力打满不是调度 |

---

## 7 剩余待做（都需要独占窗口，本轮没动）

| 项 | 预期 | 为什么留到现在 |
|---|---|---|
| `--kv-grow` | +1487 槽（+15.2%） | 要先拆 `--resident-experts`（源码 `generate.cpp:5154` 的 `!o.resident_cpu_experts` 门），动 RAM+VRAM 两个面，风险最高 |
| `--spec-min-p --calibrate` | decode +2~5% | 要独占 GPU 跑校准，与本轮的车冲突 |
| 合规基线（上游冻结 fixture） | — | 25 min 窗口，得在全部参数定下来之后跑才有意义 |

---

## 8 一句话

**"不能试"只有 3 项（硬件 cc、未链接的 hipBLASLt、别的后端）；能试的 12 项试完，7 项有路径的全是零；真正的收获不在参数上，而在发现 8K 以下的对话从来没复用上——那不是参数问题，是 checkpoint 只能落在 8192 边界上的结构限制。**
