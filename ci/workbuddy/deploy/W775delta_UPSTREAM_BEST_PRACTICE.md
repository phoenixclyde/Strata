# 上游「最佳实践」到底长什么样 —— 逐层拆解 + 我们的对照

> 依据：0.2.2 树（引擎 0.1.47）的 `docs/` 原文 + 生产容器实读。
> 结论先行：上游的最佳实践不是一个参数清单，而是一套**三层规范**：可复现的构建 ->  标准化的测量 ->  明确声明「不声称什么」。我们前两层部分对齐、第三层基本没做。

## 1 第一层：构建（`docs/AMD_HIP.md`）

### 1.1 gfx906 官方配方（原文）

```sh
cmake -S . -B build-906 -G Ninja -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja -C build-906 strata
```

并列要求：
- 底座 `mixa3607/rocm-gfx906:7.14-complete`，**hipBLASLt 不使用**
- 运行参数 `--device=/dev/kfd --device=/dev/dri --group-add video --ipc=host --ulimit memlock=-1`，必要时 `HSA_OVERRIDE_GFX_VERSION=9.0.6`
- **「Use the repository-pinned llama.cpp dependency; do not silently substitute another revision」**（`AMD_HIP_PERFORMANCE.md`）

### 1.2 我们的对照

| 项 | 上游 | 我们 | 状态 |
|---|---|---|---|
| 编译器 | `/opt/rocm/llvm/bin/clang(++)` | 同 | 对齐 |
| 依赖 pin | 仓库 pin，不静默替换 | ggml `3cf03257`，全量清单 md5 与镜像一致 | 对齐 |
| 底座 | `mixa3607/rocm-gfx906:7.14-complete` | 同 | 对齐 |
| 运行时设备/权限 | 5 项 | `docker inspect` 逐项满足（含 `ulimit -l` unlimited） | 对齐 |
| `STRATA_PREFILL_MMQ` | gfx1100 路径要求 ON | **gfx906 上不可用**（需 `ENABLE_HIP`，与 `HIP_GFX906` 互斥） | 不适用 |
| `STRATA_HIPBLASLT_TUNING` | gfx1100 专用表 | 不适用（gfx906 无 hipBLASLt 路径） | 不适用 |

**=>  构建层：完全对齐。**

## 2 第二层：测量（`docs/BENCHMARK_PROTOCOL.md`，40 KB，`strata bench run` 实现）

这是上游最佳实践的核心，也是最严的部分。**Status: draft**（`strata-qwen38-thinking-v1-draft.1`）。

### 2.1 采样参数是硬规定，不许替换

| Setting | Required value |
|---|---|
| `chat_template_kwargs.enable_thinking` | `true` |
| `chat_template_kwargs.preserve_thinking` | `true` |
| `reasoning_effort` | `"xhigh"` |
| `temperature` | **`1.0`** |
| `top_p` / `top_k` | `0.95` / `20` |
| `min_p` | `0.0` |
| `presence_penalty` / `repetition_penalty` | `0.0` / `1.0` |

原文并写死：

> `Unsupported settings make a run nonconforming; **do not silently substitute greedy sampling or disable thinking**. Disable custom reasoning budgets, automatic effort changes, and additional stop strings.`

### 2.2 工作负载是冻结的 fixture，不是自己搓的文本

- fixture：`bench/prompts/standard-v1`，corpus SHA-256 `e75eff8b...f68407`
- runner 发请求前**逐字节校验** manifest，有一个字节不同就拒绝运行
- stage 结构：warm-up 1（不计分）->  performance **3 reps × {short, prompt-4k, prompt-16k} = 9** ->  sanity **12**（I1-I4 / R1-R4 / T1-T4，cap 2048）->  可选并发 3 轮 × 4
- 总共 **21 个计分请求 + 1 个 warm-up**，concurrency=1

### 2.3 统计规则（逐条原文）

- `prompt_tps = read_tokens / prompt_s` —— **"Cached tokens never enter the numerator"**
- `decode_tps = decode_tokens / decode_s` —— 含被接受的 reasoning/answer token，**排除被拒的草稿**
- 每个 case **分别**算 median / min / max / **n**，**"Do not pool prompt sizes, quantizations, configurations, or concurrency levels"**
- **"Never hide early EOS, failed requests, or slow samples"**
- **"A partial sample set keeps its actual `n`; do not imply that three repeats succeeded"**
- **"Three rounds are too few to advertise a stable p95"**
- **"Quality scores remain separate from throughput"**
- 排除项：errors / cancellations / **unexpected cache reuse** / missing measurements，且必须**列出**

### 2.4 配置必须分 track，不许混

> `configuration.track = "default"`（unmodified release's setup-generated settings）vs `"custom"`（tuning, experimental options, modified builds）。
> **"Never merge these tracks into one headline result. A claimed improvement requires a separate, same-machine baseline."**

### 2.5 我们的对照 —— 这是差距所在

| 项 | 上游要求 | 我们实际做的 | 判定 |
|---|---|---|---|
| 采样参数 | `temperature 1.0 / top_p 0.95 / top_k 20 / effort xhigh` | **`temperature=0`（greedy）+ `reasoning_budget_tokens=64`** | **违规**（上游明确「不 conforming」） |
| 提示词 | 冻结 fixture + manifest 校验 | 自己用重复段落 + nonce 构造（为强制冷读） | **不可比** |
| stage 结构 | warm-up + 9 perf + 12 sanity | 只有 perf（2-3 档 × 3-5 runs） | 缺 sanity/quality |
| 统计 | 每 case 分 median/min/max/n；不得合并档位 | 我们按档位分开了，也报了 n | 基本对齐 |
| 缓存 token | 不进 prompt_tps 分子 | 我们强制 `--prompt-cache 0` + nonce 做到 `reused=0` | 对齐（但手段非标准） |
| track 标记 | default / custom 分离 | 我们一直是 custom（改了 `pcie-frac`/`spec-min-p`/`kv`/`resident`），**但没标** | 缺 |
| 基线 | 声称改进需同机独立基线 | 我们做了 A/B（同机、同窗口） | 对齐 |

### 2.6 一个关键可执行发现

- **`strata bench run` 不在引擎二进制里**：生产容器实测 `strata bench --help` ->  `unknown argument: bench`。它是 0.2.1 起的**产品 CLI**（Python 层），我们只编了引擎。
- **但冻结 fixture 在镜像里**：`/src/bench/prompts/standard-v1/{MANIFEST.sha256,build.json,requests/*}`。
- =>  **我们无法用官方 runner，但可以照协议手工发同一套 fixture 请求**。这是让我们的数字第一次能和社区对比的唯一路径。

## 3 第三层：声明边界（`AMD_HIP_PERFORMANCE.md` 的范式）

这一层最容易被忽略，但上游做得最狠。

### 3.1 「正确性与质量限制」的原文写法

> - CTest **29/29** passed ...
> - `Real quantized MMQ relative L2 error was approximately 0.0026 ... **this is not bitwise numerical equivalence**`
> - **`End-to-end coding quality is not established by these numerical checks or capped throughput requests. Validate completed tasks with independent runtime tests`**
> - **`this contribution makes no broad answer-quality or agentic-reliability claim`**
> - `The changes do not claim better model reasoning, verified full-context behavior, end-to-end vision validation, Windows HIP, other AMD architectures, or mixed AMD/NVIDIA execution.`

### 3.2 「被否定的实验」必须带理由

> `Static 16K chunks, expanded FP16 expert tuning, and a 192-slot ring did not offer a consistent end-to-end win in the evaluated workload.`
> `**Microkernel speedups alone were not sufficient to select a configuration.**`
> `No increase in GPU power cap was used.`

### 3.3 我们的对照

| 项 | 上游 | 我们 |
|---|---|---|
| 数值误差量化 | 给出相对 L2 ≈ 0.0026 并声明"不是逐位等价" | 我们只有"输出 md5 相同"，且**已发现该判据在长重复 prompt 上不成立**（同 prompt 3 次 3 种输出） |
| 明确「不声称什么」 | 一整段 | **从未写过** |
| 被否定实验 + 理由 | 专门一节 | 我们有 `REJECTED` 记录，但缺"为什么不是微基准赢就算赢"这类方法论陈述 |

## 4 差距清单（按可弥补性排序）

| 序 | 差距 | 能否弥补 | 成本 |
|---|---|---|---|
| 1 | 采样参数不合协议（greedy + 自定义 budget） | **能**：照 fixture 的 `template_kwargs` 发（`enable_thinking=true, reasoning_effort=xhigh, temp 1.0, top_p 0.95, top_k 20`） | 一次窗口 |
| 2 | 提示词不可比（自搓 vs 冻结 fixture） | **能**：fixture 已在镜像里，直接加载 `requests/*.json` | 同上 |
| 3 | 缺 sanity/quality 阶段 | **能**：I1-I4/R1-R4/T1-T4 共 12 请求，cap 2048 | 同上，+10 min |
| 4 | track 未标记 | **能**：文档层面标注 `custom` | 0 |
| 5 | 没有「不声称什么」的边界段 | **能**：写作层面 | 0 |
| 6 | 无法用官方 `strata bench run` | **不能**（需 0.2.x 产品 CLI，我们只有引擎）；手工照协议是替代 | — |

## 5 一句话总结

上游最佳实践 = **「构建可复现 ->  测量有标准（冻结 fixture + 规定采样 + 分 track）->  声明有边界（量化误差 + 明说不知道什么）」**。

我们前两层：构建已完全对齐；测量的**统计纪律对齐、采样与 fixture 不合规**。
第三层：**基本空白**——而这恰恰是上游文档里写得最狠的一层（"this is not bitwise numerical equivalence"、"makes no broad answer-quality claim"）。

## 6 建议的下一步（若要真正对齐）

一次约 25 分钟的窗口，照协议跑一版**合规基线**：
1. 加载 `/src/bench/prompts/standard-v1/requests/*.json`
2. 用 fixture 的 `template_kwargs`（thinking on / xhigh / temp 1.0 / top_p 0.95 / top_k 20）
3. warm-up 1 ->  performance 3 reps × 3 长度 ->  sanity 12
4. 每 case 报 median/min/max/n，标明 `track=custom`（因为我们改了 `pcie-frac 0.20` / `spec-min-p 0.70` / `kv k8v4` / `--resident-experts`）

产出可以同时回答三件事：**我们的绝对水平在哪、和社区差多少、以及「我们改的那些参数到底值多少」在一个合规口径下还剩多少。**
