# W894 · 全量对账：版本与来源、分享页 30 条消息、ki 最新源码

**触发**：上一轮（W893）三处不合格 —— ①只查 GitHub 主线 CK 就断言「CK 是死路」，没查我们自己的 ROCm；
②只用「找到什么讲什么」，没有把分享页 30 条消息逐条覆盖；③没跟 `ki` 的最新提交（166 上的副本停在 2026-09-27）。
**本轮**：只读源码/文档 + 只读设备属性，**生产零改动、零重启**。

---

## 0 结论先行

1. **版本被我说错了一半**：生产容器是 **ROCm 10.1.0 自建版**（`ROCM_BUILD=7.14.0-gfx906+20260802001858`），
   镜像是 `COPY /opt/rocm /opt/rocm` 把整套 6.9 GB 拷进去的；**宿主机**另有 ROCm 6.4.4（apt，`repo.radeon.com/amdgpu/31.40.1`）。
   上一轮我只报了宿主 6.4.4，把「我们自己的 10.1」漏了。
2. **CK 在宿主上确实有 gfx906**：`composablekernel-dev 1.1.0.60404`，`/opt/rocm-6.4.4/include` 里 **17 处** gfx906，
   走的是 `device_*_dl.hpp`（DL = 点积路线，非 MFMA）。**但生产容器里没装 CK**（`/opt/rocm/include/ck` 不存在），
   所以「Strata 走 CK」不成立，而「CK 完全没有 gfx906」也不成立 —— 上一轮两头都说错了。
3. **hipBLASLt 的判死是对的，但理由要换**：容器里 `libhipblaslt.so.1.4` 存在，`find /opt/rocm -path '*hipblaslt*' -name '*gfx906*'` = **0**，
   即**没有 gfx906 内核**。而页面第 4 项的真实意图（按架构校准的 GEMM 表）我们**已经用 rocBLAS 实现**：
   `/data/gfx906-rocblas-5.7.0.txt`（88 行，`STRATA_ROCBLAS_TUNING` 在产 env 里）。所以不是「没戏」，是「换了库做成了」。
4. **页面 10 项里，8 项已落地或已实测，1 项真空白，1 项硬件不成立**：
   真空白是 **`STRATA_IO_THREADS`**（源码默认 Linux 16，页面用 32，PLE 直读线程池的队列深度，账本 0 命中）→ 立 **R53**。
   `--kv-resident 32768` 经语义判定为**冗余**（单 GPU + profile 时整个 K/V 已在 VRAM，KV 总量仅 214 MiB）→ 关闭 P63。
5. **ki 最新 30 个提交里有一条直接终结争论**：`1ccd44f — decide P32-5/#64 — no INT4 port; V-side int8 in the packed cell is the lever`。
   他们也不做 INT4/v_dot8，改在 V 侧 int8 上要收益。与 R47 DONE_NEG 同向。
6. **wave64 页面里本来就有一整节**（"wave32 本身：GCN5 只有 wave64，所有依赖 wave32 的收尾都要换"），
   是我上一轮漏读，不是页面没写；对应条目已在 W893 R52 建账。

---

## 1 版本与来源（本轮实读）

| 对象 | 版本 | 路径 / 来源 | gfx906 证据 |
|---|---|---|---|
| **生产容器 ROCm** | **10.1.0** | 镜像层 `COPY /opt/rocm /opt/rocm`（6.9 GB），构建机自编，env `ROCM_BUILD=7.14.0-gfx906+20260802001858` | `find /opt/rocm -name '*gfx906*'` = **221** 个代码对象 |
| 宿主 ROCm | 6.4.4（`rocm-core 6.4.4.60404-129~22.04`） | `deb https://repo.radeon.com/amdgpu/31.40.1/ubuntu noble main` | — |
| 宿主 CK | **1.1.0.60404**（`composablekernel-dev`） | 同上 apt 源；`/opt/rocm-6.4.4/lib/cmake/composable_kernel` `PACKAGE_VERSION "1.1.0"` | **17 处** gfx906（`device_gemm_dl.hpp`、`device_convnd_bwd_data_..._dl.hpp`、`ck.hpp`）＝**DL/点积路线** |
| 宿主 hipBLASLt | **0.12.1.60404** | apt | gfx906 文件 0 个 |
| 容器 hipBLASLt | `libhipblaslt.so.1.4` | 随自建 ROCm 10.1 | `find … -path '*hipblaslt*' -name '*gfx906*'` = **0** ⇒ **无 gfx906 内核** |
| 容器 CK | **未安装** | `/opt/rocm/include/ck` 不存在、`lib/cmake` 无 composable_kernel | Strata 不可能走 CK |
| 我们的 GEMM 校准 | `/data/gfx906-rocblas-5.7.0.txt` | 88 行；`STRATA_ROCBLAS_TUNING` 在产 env | 等价于页面第 4 项，只是库换成 rocBLAS |

> 结论修正：**「官方 CK 主线无 gfx906」成立（`ROCm/composable_kernel@d84d8e2` 0 处引用），「我们没有 gfx906 的 CK」不成立**（宿主 1.1.0 有 DL 系列）。
> 但 CK 的 DL 只覆盖 fp16/int8 GEMM/conv 的稠密路径，**不吃我们的 Q4_K/Q5_K 分块 + Q8_1 激活**，所以对 decode 无直接用处。

> **[AUDIT23 P1-1 · 口径补全]** 「10.1.0」是**版本串**，不等于官方 10.1.0 的组件集合。
> ROCm 10.1.0（2026-10-05 发布）官方矩阵是 **CK 1.2.0 / rocBLAS 5.5.0 / hipBLASLt 1.4.1 / HIP 7.14 / LLVM 23.0.0**；
> 我们容器实测 `librocblas.so.5.7` → **5.7.0.962d0059**（引擎日志逐字：`rocBLAS tuning enabled (84 rows, 75 with a solution, gfx906, rocBLAS 5.7.0.962d0059)`）。
> ⇒ 复现时必须按**这个** rocBLAS 版本对齐：`/data/gfx906-rocblas-5.7.0.txt` 只对 5.7.0 有效，装官方 10.1.0（5.5.0）会让该表失效。
> 同时这条日志正面证明：**调优表确实在生效**（84 行 / 75 行有解），不是哑表。

---

## 2 分享页 30 条消息 → 全覆盖矩阵

| 组 | 消息 | 条目 | 本机状态 | 证据 |
|---|---|---|---|---|
| A 硬件与替代方案 | 001–012 | MI50 vs 4090 48G 规格对比、NInfer-4090 130–150 t/s、vLLM/SGLang 4 卡、deepseek-recipe、4 容器 + nginx 路由 | **不适用**：本机单卡 MI50，无 4090；引擎单序列 | 规格数字与 ROCm 设备属性一致（wave64/1024 GB/s/26.5 TF） |
| B KV | 013–014、021–022 | `--kv` 四档（fp16/int8/q4_0/`k8v4`）、`k8v4` 64K 起常驻 VRAM、DeepSeek FP4 CSA2 890 B/token、bit-exact 4-bit | **在产 `k8v4`**；CSA2 是模型自带，与 Strata 无关 | P04（816 B/cell，KL 门过）；P32（KV 总量 214 MiB） |
| C 量化质量 | 015–018 | 1.75/2.00/2.25 bpw、GSQ-RCO、代码 +8.6/+3.2%、agent +5.3/+2.2% | **不适用**：我们是 UD-Q4_K_XL（UNSLOTH 动态），不是 IQ2 系 | PACK/模型名 |
| D 性能与并发 | 019–020 | 4090 40.2/615、官方表、4×24G 1M 上下文 847–1491 t/s、并发 1/2/4/8 无增益（4 并发 +8%） | 参考：我们 **prefill 740 / decode 45**；单序列，`--parallel` 不用 | 生产日志 |
| E RDNA3 十项 | 023–024 | 见 §3 | 逐条判定 | 见 §3 |
| F 诊断 | 025–028 | 45 t/s + 带宽十几% ⇒「dp4a 发射率墙 48% VALUBusy」；锁频 +5–15%；UPP +10–20% | **两条都实测否**：VALUBusy 26–41%（非 48% 硬墙）；sclk 恒 1725 MHz、114–220 W、未撞 cap | W892 §4（R48 DONE_NEG）、hipfire PMC |
| G Strata 架构 | 029–030 | 「无 gfx906 内核」「全部借 llama.cpp MMQ」「MMQ 是行并行」「pinned 版本早于 iacop」 | **三否**：自有内核 18,693 行；仅 prefill K-quant 借 `strata_kq`；MMQ 是 **tiled**（0.4.1） | W892 §8.1、R51 源码核查 |

---

## 3 页面十项逐条（有 / 无 / 生产值 / 判决）

| # | 页面主张 | 我们有没有 | 生产在用吗 | 判决 |
|---|---|---|---|---|
| 1 | wave32 integer-dot MMQ | **有等价物**：tiled MMQ + `v_dot4_i32_i8`（dp4a）；无 wave32（gfx906 只有 wave64） | 是（prefill 的 `strata_kq` + 自有 `iq_kernels`） | **已落地**；波口径未记账 → R52 |
| 2 | HIP MMQ prefill（`STRATA_PREFILL_MMQ`） | 有（二进制含该 env） | 是 | 已落地；gfx906 向量 load 缺 → R51 |
| 3 | 权重重打包成可算格式 | 有（`--pack` + `iq_pack.py`，IQ→native experts） | 是（`/data/packs/ud-q4_k_xl`） | 已落地 |
| 4 | hipBLASLt 调优表 | **无 gfx906 内核**（容器 0 个 gfx906 文件） | 不用 hipBLASLt，用 **rocBLAS + 88 行 gfx906 表** | **意图已用 rocBLAS 实现**；不是缺失 |
| 5 | prefill 批处理 + `RING=96` + `IO_THREADS=32` | 有（`STRATA_PREFILL_RING`、`STRATA_IO_THREADS`） | RING：**测过 =8 无变化**；IO_THREADS：**从未设**（默认 Linux 16，clamp 1–64） | RING 已判否；**IO_THREADS 真空白 → R53** |
| 6 | 可复用 pinned staging buffer | 有（`pinned.hpp`；`load_main` 打「one reused destination」） | 是 | 已落地 |
| 7 | `--resident-cpu-experts` | 有（引擎 flag 存在） | **未开**；等价组合 `--resident-experts` 已 A/B：**去掉胜 +10.5%** | **有意不开**（P89） |
| 8 | `--mmap-experts` + 固定 profile + `--expert-cache auto`，PLE 留 SSD | 有 | `--expert-cache auto` + `--expert-profile` 在产；mmap **有意不开** | 同 P89（mmap 是 `--resident-experts` 的一部分） |
| 9 | `--kv int8` + `--kv-resident 32768` | 有（`--kv-resident`） | 用 `k8v4`（816 B/cell < int8 1056）；未设 kv-resident | **冗余**：单 GPU + profile 时整个 K/V 已在 VRAM，总量 214 MiB；显式驻留只会占专家槽 → 关闭 P63 |
| 10 | MTP `--spec 4 --spec-min-p 0.5` | 有 | `--spec 4` **`--spec-min-p 0.70`** | **0.5 在我们机上更差**：P06 sweep 0.3=33.74 / **0.5=35.72 / 0.7=36.96**；P154 复核 −14.5% |

---

## 4 ki 最新（`3857591`，2026-10-26，比 166 副本新 30 个提交）

| 提交 | 结论 | 对我们的意义 |
|---|---|---|
| `1ccd44f` | **decide P32-5/#64 — no INT4 port；V-side int8 in the packed cell is the lever** | 与 R47 DONE_NEG 同向：**不做 int4/dot8**，收益在 V 侧 int8 |
| `2febcd5` / `a349f0c` | **DFlash2 × INT8 W8A16 = 2.83×；与 INT8 交错 3.14×**，bf16 门通过 | drafter 量化是 decode 真杠杆；我们 MTP 是 bf16 → 观察项 X5（需新组件 + 逐位门） |
| `8ea4a1c` | INT8-PACKED-1 收口（门 + 性能），并修 MTP embedding 接线 | 说明 W8A16 打包路径已成体系 |
| `f844192` / `3857591` | 上游 expert offload **在 CPU 上从不计算**；hot-set 是唯一轴 | 我们的 `--expert-cache` 就是 hot-set，结论一致 |
| `cad3bd1` | LLMM1 尾部行静默截断加保护 | 正确性类，抄的是「尾部 guard」做法 |
| `f519936` | 修掉一个**虚报 470 tok/s prefill** 的 harness | 测量卫生；与 `derived_check.py` 同一纪律 |

---

## 5 缺口与动作

- **R53（新，一次重启）**：`STRATA_IO_THREADS` 默认 16（Linux，`direct_file.cpp:61-68`，clamp 1–64）→ 试 32/64。
  PLE 读取走 `DirectFile`（`ple_reader.cpp:18,100`），线程数即阻塞 `pread` 的队列深度。判据：首次读 PLE 的 TTFT / prefill，
  `|Δ| ≥ 2×CV`；16→32→16 交错，掉头即回滚（env 删除即可）。
- **关闭 P63**：`--kv-resident 32768` 语义冗余（见 §3 #9），不再作候选。
- **R54（新，源码级，重）**：GDN **逐层 persistent megakernel**（`rdna3/src/kernels/cuda/megakernel_gdn.cu`，564 行，
  带 `mk_gdn_parity` 逐位校验）。目标是把每层 5 个小 kernel 的 launch/同步摊掉（W873：decode 非 GPU 约 21%）。
  门：先 `mk_gdn_parity` 式逐位对齐，再窗口 ms；不做服务 A/B 前不合并。**这是本轮唯一从源码新挖出的结构级杠杆**。
- **不开 X6**：`rdna_mmvq.cu`（`sudot4` + 8 行/块）——它与我们 `native_mmvq` 同类，而 R23 已按行/波调过；
  且 `sudot4` 在 gfx906 的可用性未验，先不动。
- **X5（观察，不进队列）**：ki 的 DFlash2 × INT8 drafter（2.83–3.14×）——我们 drafter 是 bf16 的 MTP runtime，
  要换等于换组件，先记观察。
- **维持**：R52（wave64 波口径）、R51（prefill MMQ 向量 load）、R49（per-file max-ilp）、R50（router GEMV 先复现）。

---

## 7 `nicejunjie/Strata-rdna3` 源码（**已公开**，本轮实测）

分享页说它 Private 是**过期信息**：`api.github.com/repos/nicejunjie/Strata-rdna3` 返回 `"private": false`、
`"visibility": "public"`，28 stars / 9 forks，最后推送 **2026-11-02T13:05Z**。已拉源码：
`albus/w896/forks/rdna3`，`021ecb8`，4,936 文件。

**逐文件哈希对比（我方 `d963c791` vs 它 `021ecb8`，`src/`+`include/`）**：改 **142** / 增 **18** / 删 **66**（我方多 48 个文件）。

| 它新增的内核 | 行数 | 源码事实 | 能否移植到 gfx906 |
|---|---|---|---|
| `src/kernels/cuda/rdna_mmvq.cu` | 265 | 头部逐字：**"One wave per output row"**、每 lane 取 8 个连续权重、**"two dp4a"**；实际指令是 **`__builtin_amdgcn_sudot4`**（signed×unsigned dot4）；`lane = tid & 31`、`row = blockIdx.x*8 + (tid>>5)` ⇒ 8 行/256 线程块，**wave32 布局**；归约用 DPP `row_xmask` + `permlanex16` | **需改**：`sudot4` 在 gfx906 的可用性未验；行映射要按 64 lane 重排（我们 `native_mmvq` 已是 128 线程/2 波、SmallK 2 行/波，R23 已调过）。**无证据比我们快** |
| `src/kernels/cuda/rdna_gr.cu` | 753 | RDNA3 的 GR 路径（含 WMMA 相关配对测试 `qsa_select_wmma_parity.cpp`） | **不能**：gfx906 无 WMMA |
| `src/kernels/cuda/megakernel_gdn.cu` | 564 | **逐层 persistent megakernel 原型**：把 `native_quantize_q8_1` + `native_mmvq_wave_exact` + `gdn_conv_l2` + `gdn_ab` + `gdn_step_norm` 融进一个 512 线程常驻块，用「虚拟块/虚拟线程」复用 `blockIdx/threadIdx`，`__syncthreads` 改为无条件；**`mk_gdn_parity` 逐位校验** | **可移植（新方向）**：不依赖 WMMA，只依赖 wave 内归约；能直接打 launch/同步开销（W873：decode 非 GPU 约 21%） |

**全树 `sdot8` 计数 = 0**；`dot8` 命中的 6 处全是 `fused_gr.cu` 里的**函数名** `dot8u/dot8/dot8q`（FP32/BF16 点积），
不是 `v_dot8_i32_i4`。⇒ 页面「iacopPBK 用 v_dot8 把指令数减半」在本仓同样**不成立**。

---

## 8 复现

```bash
# 版本
docker exec strata166-407 cat /opt/rocm/.info/version            # 10.1.0
docker exec strata166-407 bash -lc 'find /opt/rocm -name "*gfx906*" | wc -l'   # 221
dpkg -l | grep -E 'composablekernel|hipblaslt|rocm-core'
grep -rn 'gfx906' /opt/rocm-6.4.4/include/ck | wc -l             # 17（DL 系列）
docker exec strata166-407 bash -lc 'find /opt/rocm -path "*hipblaslt*" -name "*gfx906*" | wc -l'  # 0
# 十项里的两个空白
strings /data/bin/strata-0.1.55t | grep -E '^STRATA_(IO_THREADS|PREFILL_RING)'
sed -n '58,68p' ~/strata166/pr/strata-fork/src/platform/direct_file.cpp
# ki 最新
cd albus/w896/forks/ki-latest && git log --since=2026-09-27 --oneline | wc -l   # 30
```
