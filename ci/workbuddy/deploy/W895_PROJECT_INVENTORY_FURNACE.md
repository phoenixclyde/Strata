# W895 · 项目清单全量落盘（含延伸发现），以及一个决定性校准

**触发**：上一轮说「两个没拉下来」只交代了一个；且延伸发现的项目没有按分享页同等待遇处理。
**本轮**：页面全文 717 行重读一遍（001–030 全部），把所有点名项目 + 搜索延伸项目逐个落盘到源码级；
**生产零改动、零重启**。

---


> **[口径注 · 2026-11-02 23:2x]** 本项目**只做单流**（W898）。本件里的多用户数字（6 用户 57→98 等）只作**背景**，不得引用为收益预期或验收依据；decode 的验收只守「不劣化」。

## 0 结论先行

1. **「两个」的真相**：一个是页面点名的 `nicejunjie/Strata-rdna3`（**已由 Private 转 public**，已拉 4,936 文件）；
   另一个 `skyne98/llama.cpp-gfx906` **页面里 0 次提及**——它是我前几轮自己加进清单的，且该用户下**没有这个仓库**。
   我用 GitHub 搜索找到真实存在的 gfx906 分支，按同样标准逐个拉取（§3）。
2. **页面点名的 18 个项目/制品，现已全部落地或证明不可得**（§2），没有第三个悬空项。
3. **延伸发现里最有价值的是 `sixvolts/llamacpp-gfx906-furnace`**：**同卡（MI50 32G）、同模型（Qwen3.8-Flash-Next，
   177B MoE）、同血统（llama.cpp）**，README 有冷启 A/B 实测。
4. **它给了一个决定性校准**：这个模型在 MI50 上，**单用户 decode 62 → 62 t/s（完全持平）**，
   所有内核工作只把 prefill 从 887/867 提到 1251/1561。⇒ **我们的 45 t/s 不是「内核没做对」，而是这个模型在 MI50 上的 decode 地板**。
   这一条应当直接压低 R50/R54 的预期，并把重心移到 prefill（我们 740）。
5. **唯一新挖出的、可移植且不依赖 RDNA 特性的结构性差距是波内归约**：我们 109 处归约里 DPP 只有 4 处
   （且写在「wave32 only」的路径里），furnace/RDNA3 都已把 `ds_bpermute` 换成 DPP ⇒ 立 **R55**。

---

## 1 「两个没拉下来」的真相

| 名字 | 是否页面点名 | 现状 | 处置 |
|---|---|---|---|
| `nicejunjie/Strata-rdna3` | **是**（截图里的 fork） | 页面说 Private 已**过期**：API `private:false`、28★、9 fork、最后推送 2026-11-02T13:05Z | **已拉**：`albus/w896/forks/rdna3`，`021ecb8`，4,936 文件；与我们的差异 142 改/18 增/66 删（W894 §7） |
| `skyne98/llama.cpp-gfx906` | **否**（原文 `skyne` 命中 0 次） | 该用户名下无此仓库（API 列出的仓全是 Rust/Dart/TS 项目，无 GPU fork） | **判定为我自己的错误条目**；改用 GitHub 搜索到的真实 gfx906 分支替代（§3） |

---

## 2 页面点名项目：全量状态

| 项目 | 性质 | 状态 |
|---|---|---|
| `Niko1221/Strata` | 主线 | 已拉（`strata-upstream`） |
| `nicejunjie/Strata-rdna3` | RDNA3 fork | 已拉（`rdna3@021ecb8`） |
| `sergqwer/strata-nvfp4` | gfx1100 后端 + 性能文档 | 已拉；`docs/AMD_HIP_PERFORMANCE.md` 已读（含 10 项来源与实测表） |
| `iacopPBK/llama.cpp-gfx906` | gfx906 MMQ fork | 已拉（`iacop@125db33`） |
| `Neroued/ninfer` | CUDA 引擎 | 已拉（sm_120a） |
| `ruwwww/ninfer-5060ti` | sm_120 分支 | **已拉**（1,442 文件，`15700cf`） |
| `ashalliants/ninfer-3090` | sm_86 分支 | **已拉**（2,831 文件，`162e6c1`） |
| `T-Crypt/ninfer-4090` | sm_89 分支 | 已拉（sparse checkout 曾为空，本轮记录待修） |
| `UDPSendToFailed/ninfer-4090` | sm_89 Windows | 页面点名；与 gfx906 无关（见 §3 注） |
| `JGamboa/ninfer-4090-windows` | sm_89 int8-prefill | 同上 |
| `deepseek-ai/DeepInfer` / `deepseek-recipe` | SM100+Ascend / API 协议库 | 已拉；均无 AMD 路径 |
| `vllm` / `sglang` / `TensorRT-LLM` | 通用引擎 | 已拉；gfx906 无官方支持（vllm#33811 明写） |
| `ISTA-DASLab/...GSQ-RCO-GGUF` | **权重制品**（257 GB） | 不是源码，不拉 |
| `lmsysorg/sglang`、`vllm/vllm-openai` | **镜像名**，非仓库 | 不适用 |

> 四个 ninfer 分支（5060Ti/3090/4090×2）是 **CUDA sm_86/89/120** 工程，与 gfx906 无交集；
> 拉它们的唯一价值是确认「没有可移植的 gfx906 路径」——结论与 W892 一致。

---

## 3 延伸发现（GitHub 搜索，按页面同等标准处理）

搜索 `llama.cpp-gfx906` 得 20 个真实仓库，按相关度拉取 4 个：

| 项目 | HEAD / 状态 | 源码判定 |
|---|---|---|
| **`sixvolts/llamacpp-gfx906-furnace`** | `gfx906-perf` 分支，3,626 文件（tarball 通道，`git clone` 被 368 MB 包体截断） | **同卡同模型**：MI50 32G、Qwen3.8-Flash-Next 177B MoE、llama.cpp；三项核心改动：**三平面 K-quant 重打包**（磁盘超块布局把 GCN matvec 限制在 ~58% HBM，重打包后 ~89%）、**DPP/ds_swizzle 全后端波内归约**、qwen4exp 系列（LDS 常驻 GDN、QSA indexer 池化/块打分融合、块布局缓存、稀疏 decode 只读选中 key、并行 top-k 基数选择、HC/共享专家尾部融合） |
| `Kausik-A/gemma4-mi50-optimizations` | `8e83161`，17 文件 | **共享 Q8_1 + Q/K/V 融合网格**：patch 308 行，MI50 32G 实测 19.0619→**19.3923 t/s（+1.73%）**，GPU dispatch 2054→1859，输出逐字节相同、MTP 接受 27/35 不变 |
| `exabit-io/llama.cpp-gfx906-tuning` | 4×Vega20 调优/测量 | 只作对照（调优手册，无新内核） |
| `DByte308/ornith-mtp-gfx906` | 2×gfx906 上**微调 MTP 头** | 与 X5（drafter 量化）同域，记为观察 |

**`mixa3607/ML-gfx906`（367★，含 Strata 构建）**：166 上已有 `/home/albus/routeB/ML-gfx906`，不重复拉。

---

## 4 决定性校准：MoE decode 在这张卡上就是平的

`furnace` 的 README（4×MI50 32G，ROCm 7.1，Qwen3.8-Flash-Next 177B，UD-Q4_K_XL，MTP 开）：

| 指标 | 起点 | 该分支 |
|---|---:|---:|
| Prefill 8K | 887 | **1251**（+41%） |
| Prefill 32K | 867 | **1561**（+80%） |
| **Decode，1 用户** | **62** | **62（持平）** |
| Decode，6 用户 | 57 | 98 |
| 同机最早起点 | 796 prefill / **51 decode** | — |

⇒ 把「重打包 + DPP + QSA 融合 + 稀疏 decode + 并行 top-k」全做完，**单用户 decode 一分不涨**。
我们 45 t/s 处在这条曲线的同一段（他们 MTP 开是 51→62）。**这不是「内核没做对」，是模型×卡的 decode 地板**。
R50/R54 仍可做，但**预期必须按「prefill 与多流」定，不按单流 decode 定**。

---

## 5 我们 vs 它们：波内归约（唯一新条目）

| 内核 | `__shfl*` 处数 | DPP 处数 | `permlanex16` |
|---|---:|---:|---:|
| `native_mmvq.cu` | 5 | 0 | 0 |
| `fused_gr.cu` | 21 | 0 | 0 |
| `qsa_select.cu` | 52 | 0 | 0 |
| `iq_kernels.cu` | 23 | 0 | 0 |
| `qsa_decode_attn.cu` | 8 | **1** | **3**（且注释写明是 wave32 专用路径） |

HIP 的 `__shfl_*` 在 AMD 上降到 `ds_bpermute`（走 LDS 往返）；DPP 是 VALU 内 lane 交换，不占 LDS。
`furnace` 逐字：「**DPP/ds_swizzle warp reductions ... instead of `ds_bpermute` LDS roundtrips in every warp reduction backend-wide**」；
RDNA3 fork 的 `rdna_mmvq.cu` 也用 `update_dpp + permlanex16` 做 32-lane 归约。我们只有 qsa_decode 一处，且是 wave32 路径。
数值上 DPP 搬的是同一批 lane 值 ⇒ 应当**逐位不变**，可用现有 parity 工具直接验。

---

## 6 队列变更

- **R55（新，零停服先做）**：把热点归约从 `__shfl_*` 换成 **DPP `ds_swizzle`/`update_dpp` + `permlanex16`**（wave64 语义：16-lane 行内 row_xmask + 跨行 permlanex16），
  顺序覆盖 `native_mmvq`(5) → `qsa_select`(52) → `fused_gr`(21) → `iq_kernels`(23)。
  门：①逐位相同（DPP 只换搬运方式）；②独立探针 `|Δ| ≥ 2×CV`；③不增 VGPR。
- **R50/R54 预期下调**：按 §4，二者只按「prefill / 多流」验收；单流 decode 不作为成功判据。
- **Kausik 的 Q8_1 共享不开条目**：我们 `layer.cpp:172-178` 已有 `x_q8_1_ready`（「previous native projection quantized the SAME x … the quantize is skipped」），
  机制同源；其外部收益仅 +1.73%，且是 Gemma 4 形状，证据不足另开。

---

## 7 复现

```bash
# 项目清单与 HEAD
cd albus/w896/forks && for d in */; do printf '%-32s %s %s\n' "$d" "$(git -C "$d" rev-parse --short HEAD 2>/dev/null)" "$(git -C "$d" ls-files 2>/dev/null | wc -l)"; done
# furnace（默认分支是 gfx906-perf，不是 main；clone 会因 368MB 截断，用 tarball）
curl -sL "https://gh-proxy.com/https://codeload.github.com/sixvolts/llamacpp-gfx906-furnace/tar.gz/refs/heads/gfx906-perf" -o f.tgz
# 我们的归约形态
cd ~/strata166/pr/strata-fork && grep -c '__shfl' src/kernels/cuda/{native_mmvq,fused_gr,qsa_select,iq_kernels}.cu
grep -c 'update_dpp\|permlanex16' src/kernels/cuda/qsa_decode_attn.cu
```
