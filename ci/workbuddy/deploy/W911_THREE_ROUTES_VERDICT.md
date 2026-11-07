# W911 · 评那三条路线：A 的前提不成立，B 的两处机理错，C 的结论对但理由错一条

> 2026-11-03 20:3x。零停服，只读核实。对象是机主转来的那张"三条路线可行性"图。
> 全文的原则：**先问改的是哪个量化格式、哪个相位（prefill/decode）、我们是否已有**，再谈 fork 归属。

---

## 0 先给判定

| 图里的说法 | 判定 | 一句话理由 |
|---|---|---|
| A：`third_party/llama.cpp` 是 submodule 还是 vendored，改 `.gitmodules` 指向 iacopPBK | **前提不成立** | 我们**没有** `third_party/llama.cpp`，`.gitmodules` 为空；`third_party/ggml` 是固定 commit `3cf03257`（2026-09-20）的 **ggml 子库** |
| A：升级到 iacop 的 gfx906 版，收益 45 → 70–110 tok/s | **格式错配 + 相位错配** | iacop 的 gfx906 改动集中在 **Q4_0/Q4_1/Q8_0/MXFP4**；我们权重大头是 **Q4_K(39.8%) + Q5_1(24.3%)**，他没动 K-quant MMQ。且 MMQ 只影响 **prefill**，而 tok/s 是 decode 口径 |
| B：把"行并行 dp4a"换成 tiled + LDS | **我们已经不是行并行** | 生产日志 `MMQ tile: type 21 -> J=64 (48000 B of shared)`；`mmq-instance-*.cu` 直接编进引擎；`mmq_tab` 覆盖 9 个类型 |
| B：`v_dot8_i32_i4` 让 int4 权重指令数减半 | **错**（`W909` 已实跑证伪） | `v_dot8` 是 **i4×i4**；W4A8 下拆成高低半后 8 个元素仍是 **2 条指令**，与 dot4 相同，还多两次拆包 |
| C①：vLLM 是服务框架，不能当 backend 嵌进 Strata | **对** | |
| C②：它不懂 GGUF/2-bit，加载就挂 | **过强** | vLLM **有** GGUF（out-of-tree `vllm-gguf-plugin`，Q4_K_M 可用），但**只支持单文件**，且官方自述 "highly experimental and under-optimized" |
| C③：gfx906 无 hipBLASLt、ROCm 支持弱，vLLM 跑不动 | **半对** | 无 gfx906 版 hipBLASLt 内核**是真的**；但 vLLM 在 gfx906 **能跑**，有活跃 fork（`ai-infos/vllm-gfx906-mobydick`），机主自己上一阶段走的就是 mobydick |

**排序（按证据）**：B 的方向（改成 R60/R58/R61）＞ A（只取两个内层手法）＞ C（不换）。
但更重要的结论是：**三条路线都在回答"怎么把别人的内核搬进来"，而我们的实测说瓶颈不在内核集合。**

---

## 1 路线 A：连前提都不成立

### 1.1 我们怎么引用 ggml（源码事实）

```
$ cat .gitmodules                      → 空（没有 submodule）
$ ls third_party/                      → ggml  ggml-tq  libstrix  project-maya
$ cat third_party/ggml/VERSION.txt     → 3cf03257f219afbe7334045ff7c6a06ac68c627d  Sun Sep 20 16:08:11 2026
```

`CMakeLists.txt:1918`：

```cmake
set(STRATA_GGML_DIR "" CACHE PATH "llama.cpp checkout to take ggml from (empty: fetch the pinned commit)")
...
add_subdirectory(${STRATA_GGML_DIR}/ggml ${CMAKE_BINARY_DIR}/ggml EXCLUDE_FROM_ALL)
```

⇒ 我们从 llama.cpp 里**只取 `ggml` 这个子库**（而且只用 `ggml-cuda` 的模板实例与 `vecdotq.cuh`），
`STRATA_GGML_DIR` 只是一个**可选覆盖**。所以"看是 submodule 还是 vendored，改 `.gitmodules` 指向 iacop"——
**这两条路我们都不在那张图上**。真要换，是换 `third_party/ggml` 的 pin，不是换 `.gitmodules`。

### 1.2 格式错配（这条最致命）

iacopPBK/llama.cpp-gfx906 的 README 逐条列出改动（2511 / 2512 / 2601 三个 release）：

```
2511  common.cuh        DPP-based warp reductions
2511  fattn-common.cuh  GCN-optimized thread counts and tile configurations
2511  fattn.cu          Q8-optimized tile kernel selection
2511  mmq.cu            GFX906 vectorized loads for Q4_0 / Q4_1
2512  mmq.cuh           software pipelining for Q8_0 MMQ loads
2512  mmq.cuh           Q8 MMQ need_check path → avoid LDS conflicts
2512  mmq.cuh           MXFP4 load pipeline (e8m0 conversion)
2512  vecdotq.cuh       fast Q8_0 load path using memcpy
2512  vecdotq.cuh       MXFP4 MMVQ software pipeline / lookup
2512  mmq.cu, mmid.cu   MoE sub-warp shuffle fix for wavefront64
2601  gfx906-mmvq-q4_0/q4_1/q8_0.cuh   warp-cooperative MMVQ
2601  mmvq.cu           half-warp dispatch for MoE small matrices
```

**全部集中在 Q4_0 / Q4_1 / Q8_0 / MXFP4，没有一条是 K-quant（Q4_K/Q5_K/Q6_K）的 MMQ。**
我们这套模型的实际格式（`W910` 实测，非文件名）：

| 位置 | 格式 | 占比 |
|---|---|---|
| 专家 gate/up（48 层） | **Q4_K** | 主体 |
| 专家 down（43 层 / 5 层） | **Q5_1** / Q8_0 | 主体 |
| 主 GGUF | Q4_K 39.8% / Q5_1 24.3% / Q8_0 8.6% / IQ4_NL 25.9%（PLE 单表） | |

⇒ iacop 那套优化能直接落在我们身上的，只有 **Q8_0 的 8.6%** 和一部分 attention/归约；
**占 64% 的 Q4_K+Q5_1 完全不在他的改动清单里。**

### 1.3 相位错配（"45 → 70–110 tok/s"）

- 我们生产实测（`W897`/`R53`）：**prefill 6440 tok / 8936 ms ≈ 720 tok/s**，**decode 中位 70.7 tok/s**。
- `W897` 的 A/B 已经量过：MMQ 开 vs FP16 —— **prefill 8.975 s vs 14.079 s（1.57×）**，而 **decode 两臂一致**。
  机理：decode 是 M=1，算术强度 1.78 MAC/B，喂满 dot4 需 ~12 TB/s，HBM 只有 ~1 TB/s ⇒ 带宽地板，MMQ 不参与。
- 所以"MMQ 类改动 → decode 45 提到 70–110 tok/s"在机理上不成立。那个 45 大概是**另一条路线（vLLM + 27B）的口径**，
  与 Strata 的 70.7 不是一个东西，不能横向相加。

### 1.4 A 里唯一值得偷的东西

iacop 真正独有的不是"内核"，是**内层手法**。查我们树（`src/` + `third_party/`，`*.cu/*.cuh`）：

| 手法 | iacop 用在哪 | 我们命中数 |
|---|---|---|
| `__builtin_amdgcn_readfirstlane`（SGPR hoisting） | MMQ 体内把循环不变量提到标量寄存器 | **0** |
| inline-asm `global_load_dword`（Y-tile prefetch） | MMQ 预取下一 tile | **0** |

（hipfire 的 README 也是这么概括 iacop 的贡献：*"warp-cooperative GEMV via half-wave split, Y-tile prefetch via
inline-asm global_load_dword, `__builtin_amdgcn_readfirstlane`-based SGPR hoisting, separate HBM-load →
register-cache → LDS-store pipelining"*。）

⇒ 这两个**可以单独评估，不必换 ggml**。已立 R63（先计数、后动码，见 §5）。

---

## 2 路线 B：方向对，但两个技术前提都是错的

### 2.1 "把行并行 dp4a 换成 tiled + LDS" —— 我们已经是 tiled

- `CMakeLists.txt:2192`：`target_sources(strata_mmq PRIVATE .../template-instances/mmq-instance-${_t}.cu)`
  ⇒ llama.cpp 的 **tiled MMQ 实例直接编进引擎**；
- 生产日志逐字：`MMQ tile: type 21 -> J=64 (48000 B of shared, smpbo 65536, cap 0)`
  —— 48 KB 共享内存、J=64 输出行 tile = 标准 tiled；
- 我们另有 `mmq_tab`（9 个 IQ/Q 类型）覆盖 IQ 系。

"行并行、无 LDS、无数据复用"是 **hipfire 改造前**的形态（它自己的报告写的："one wave64 per output row, no LDS,
no data reuse … llama.cpp (tiled MMQ): LDS staging, Q8_1 pre-quantized activations, int8 dot-products, 8× weight
reuse per tile"）。把 hipfire 的自述套到我们头上，是这张图的第二个事实错误。

### 2.2 `v_dot8_i32_i4` 不能让指令数减半

`W909` 在这张卡上实跑过：`sdot8` 对 nibble{1..8} 得 **20**（=1+2+…+7−8）⇒ 操作数是 **4-bit 有符号**（i4×i4）。
要用它，激活也得压到 4-bit；W4A8 下必须把 int8 激活拆成 `a = 16h + l`，**8 个元素仍是 2 条指令**，与 dot4 完全相同，
还多两次拆包。实测上限：dot4 **21.52 TMAC/s**、dot8 **49.66 TMAC/s** —— 指令率只差 1.15×，MAC 差 2.31×，
但那个 2.31× 只能靠 **W4A4** 拿到，且 IQ 码本类型根本不允许。**"指令数减半"这句话是错的。**

### 2.3 真正该做的（我们队列里已有）

同卡 dot4 实测峰 21.52 TMAC/s，我们生产折算 **4.55 = 21%**；hipfire 同卡 prefill MMQ 到 **48.5% VALU**。
⇒ 差距是**供给率**，不是指令集合。对应：
**R61**（rocprof 量 VALUBusy，判 ≥40% 还是 ≤25%）→ **R60**（stream-k，K 方向切分，提高在飞字节）→ **R58**（三段计数）。

---

## 3 路线 C：结论对，但三条理由里一条错、一条过强

| 图里的理由 | 事实 |
|---|---|
| ① "是完整服务框架，不是可链接内核库" | **对**。vLLM 的调度/PagedAttention/采样是一体的，拿不出"内核库"接口 |
| ② "不懂 GGUF/2-bit，加载就挂" | **过强**。vLLM 自 v0.27 起把 GGUF 挪到 **out-of-tree 插件** `vllm-gguf-plugin`，`Q4_K_M` 是它文档里的示例；但官方自述 "**highly experimental and under-optimized**"，且**只支持单文件 GGUF** |
| ③ "gfx906 无 hipBLASLt、ROCm 支持弱，vLLM 本就跑不动" | **半对**。缺 gfx906 hipBLASLt 内核是真的（我们容器里 hipBLASLt 有库无 gfx906 kernel）；但 vLLM 在 gfx906 **能跑**，社区有活跃 fork：`ai-infos/vllm-gfx906-mobydick`（活跃）、`mixa3607/vllm-gfx906`（预编译镜像）；`nlzy/vllm-gfx906` 已归档 |

对我们更硬的障碍不是"跑不动"，而是**模型形态**：我们是 4 个 GGUF 分片 + 71.7 GiB 独立专家 pack + 26.8 GiB PLE 表 +
`expert-profile` 路由画像。vLLM 只吃单文件 GGUF、且不走我们的 pack 布局 ⇒ 要迁就得**重打包 77 GB 并重训路由画像**。
这与"能不能跑"是两个量级的问题。

---

## 4 三条路线共同的方法缺陷（这才是要举一反三的地方）

那张图用 **fork 归属** 来估收益（"换成 iacop 的" / "换成 vLLM"），而我们这几天所有实测都指向另一组判据。
**看任何 fork / PR / 优化建议，先过这三个问题，任何一个答不上来就先别信收益数字：**

1. **改的是哪个量化格式？** —— iacop 改 Q4_0/Q8_0/MXFP4，我们 64% 是 Q4_K/Q5_1，直接命中率≈0。
2. **改的是哪个相位？** —— MMQ/MMVQ 只动 prefill；decode 是带宽地板（1.78 MAC/B），改指令救不了。
3. **我们是否已经有？** —— "tiled + LDS" 我们已经有了，`v_dot8` 已经有了但没有合法用法。
   把已有的东西列成"待做"，是这类分析的典型浪费。

补一条**收益口径**：任何"45 → 70–110 tok/s"必须写清 ①哪个模型 ②哪个相位 ③哪台卡 ④几 rep、CV 多少。
我们自己的规矩是 `|Δ| ≥ 2×CV` 才算数（当次 run 的 CV）。

---

## 5 落到队列：只加一条，且是"先计数"

| 条目 | 内容 | 闸门 |
|---|---|---|
| **R63（新，OPEN）** | 借 iacop 的两个**内层手法**：`__builtin_amdgcn_readfirstlane` 做 SGPR hoisting、inline-asm `global_load_dword` 做 Y-tile prefetch。**先 ISA 计数**（当前 `v_dot4` 130,808 条 / 每 dp4a 配套的 `v_lshlrev`+`v_and` 各多少 / `s_load` 与 `ds_read` 比例），确认"每 dp4a 的固定开销"里有多少是标量重算 | 计数不显示可消除项 ⇒ 直接关；动了求和序 ⇒ 先过 R59 |

**不改**的：路线 A 的"整包升级 ggml"不立项（格式错配 + 相位错配）；路线 B 的"绕过 ggml 重写"不立项
（我们已经是 tiled，重写等于把 llama.cpp 的调度再抄一遍）；路线 C 不立项（形态不兼容，收益为负）。
队列顺序不变：`R59 → R61 → R60 → R58 → R63 → R49 → R50 → R30′ → M3`。

---

## 6 复现

```bash
# A 的前提
cd ~/strata166/pr/strata-fork && cat .gitmodules; ls third_party/; cat third_party/ggml/VERSION.txt
grep -n "STRATA_GGML_DIR" CMakeLists.txt | head

# A 的格式错配（iacop 的 changelog 在上游 README，逐条对照我们 W910 的类型表）

# B 的"我们已经 tiled"
grep -n "template-instances/mmq-instance" CMakeLists.txt
docker exec strata166-407 grep -o "MMQ tile: type [0-9]*" /data/strata-huihui-ud-iq4_xs.log | sort -u

# B 的 dot8 语义（W909 实跑）
docker exec strata166-407 /tmp/dot_hw_run

# A 的两个内层手法我们有没有
grep -rn "readfirstlane\|global_load_dword" --include=*.cu --include=*.cuh . | wc -l   # → 0
```

---

## 7 补记（20:4x，机主指出"我们有别的更好的 fork"）—— 参照物选错了，结论反而更硬

机主提醒：真正该比的不是 iacop，是我们**自己就在用**的那个栈。核实结果：

**`mixa3607/ML-gfx906` 就是我们整套 ROCm 的来源。** 它 README 写
"Legacy builds (pre-TheRock) are no longer supported starting from the **`20260802001858`** release"，
而我们的 deb 是 `amdrocm-core7.14-gfx906 **7.14.0-gfx906+20260802001858**` —— **同一个构建戳**。
（顺带把 `W910` 的"两条轨道"坐实了：7.14 是这家的*gfx906 打包版本号*，10.1.0 是 TheRock/Core SDK 的版本。）

它还带一个 **gfx906 的 K-quant MMQ 配置补丁** `llama.cpp/build-context/patch/mxxm-gfx906-kcase.patch`
（`git cat-file -e HEAD:…` 已验证在 HEAD 里，来自 commit `eec35f4 "llamacpp: fix regression"`）：

```
// Q4_K/Q5_K/Q6_K: measured on MI50. I=64 halves the accumulator array and the X
// LDS tile, cutting VGPR/scratch and improving Q5_K/Q6_K throughput ~15-35%.
// Q4_K stays at I=128 (I=64 makes it ~53% slower). J=64 only.
CASE(GGML_TYPE_Q4_K, 256, 2, 128, 64, LAYOUT_Q8_1, MMQ_ITER_K, false, true/false);
CASE(GGML_TYPE_Q5_K, 256, 2,  64, 64, LAYOUT_Q8_1, MMQ_ITER_K, false, true/false);
CASE(GGML_TYPE_Q6_K, 256, 2,  64, 64, LAYOUT_Q6_K, MMQ_ITER_K, false, true/false);
```

**逐行比我们 pin 住的 `mmq-config-gcn.cuh`**（12 份原始副本一致，`streamk_true=0`；`work/r60-gc` 是 R60 改过的副本，别拿它当基线）：

| 类型 | 补丁（MI50 实测最佳） | 我们基线 | 差异 |
|---|---|---|---|
| **Q4_K** | 256 / occ2 / **I=128** / J=64 / stream_k=false | 已有 `(128,64,false,true)` 与 `(128,64,false,false)` 两行 | **完全一致** |
| **Q5_K** | 256 / occ2 / **I=64** / J=64（比 I=128 快 15–35%） | J=64 行是 `512 / I=128` | **1 行不同** |
| **Q6_K** | 256 / occ2 / I=64 / J=64 | 已有 `(64,64,false,true)` | 一致 |

⇒ **路线 A 的正确形态不是"换 fork"，而是"抄它这一行"**，而且只有 Q5_K 一行；本模型 Q5_K 只用在 **1 层 gate/up**（`W910`：`48 层 = 43×(Q4_K,Q5_1) + 4×(Q4_K,Q8_0) + 1×(Q5_K,Q8_0)`）⇒ 端到端期望收益 **上限远低于 1%**，可做一次一行 A/B，但不值得排进队列前列。

**更重要的是它给了我们一条负面数据**：`Q4_K 用 I=64 会慢 ~53%`（MI50 实测）。这条直接划掉了"改 I 提并发"的幻想空间，
`R58`/`R60` 都不该往 I 上试；R60 要动的是 **K 方向切分（stream-k）**，与 I（X 方向 tile 宽）不是同一个维度。

**同时也纠正我上一轮的表述**：我说"iacop 的改动只覆盖 Q4_0/Q4_1/Q8_0/MXFP4" 是对的，
但它不是唯一参照物；**真正盯 K-quant 的是 mixa3607**，而且它对 Q4_K 的结论与上游 pin 完全重合。
所以"路线 A 无效"的结论不变，但理由从"没人做过 K-quant"升级成"**做过，且我们已经是它的取值**"。
