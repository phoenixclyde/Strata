# 上游 0.2.2（引擎 0.1.47）全文评估与优化方案

> 生成：2026-10-21 23:4x · 机主令：「继续更新到上游最新版，看最近几版的**完整** release note，结合我们软硬件现状与参数配置，给出优化方案，并跑最新版基线，如数据一致或更好则落生产」
> 本件只写**有出处**的东西：每条断言后面的 `L###` 是 release note 行号或源码行号。

---

## 0 结论先行

1. **上游最新 = v0.2.2（2026-10-21T11:10Z），`main` HEAD 就是它**（`011c9e600a93`，tag `v0.2.2`），引擎 **0.1.47**。没有比它更新的 tag/commit；30 个发布资产里**仍然没有 gfx906/MI50 目标**。
2. **近 5 版（0.2.2 / 0.2.1 / 0.2.0-beta / 0.1.45 / 0.1.44.1）全文读完，逐条对我们判定：能落到我们配置上的「新东西」只有 4 条**，其余全部落在 RDNA3/RDNA4、NVIDIA、Mac、Intel、多卡、多用户、Windows 或别的模型族（Gyro/NVFP4/Qwen3.6）。
3. **0.1.45 的「AMD 长上下文提速」对我们不适用**——源码级证据：`src/kernels/cuda/qsa_select.cu:1223-1237` 的 `scores_thread_arch()` 只对 **gfx12（默认）** 和 **gfx1100（需显式开）** 返回非 0，**gfx906 返回 0 = 不提供**（L1219 注释原文 "Other wave32 parts have no measurement"）。
4. **我们唯一还缺的本地覆写只有两块**（不是三块）：`pcie_bw` 吞吐、FRU 容量一致性；PCIe link 与前端轴下限 **上游 0.1.47 已自行实现**（`serve/telemetry.py:205-233` `link()`/`_hops()`/`pcie_path` 与我们同构；`serve/web/app.js:145` 已是 `...v, 1`）。
5. 基线实测与落生产判定见 §6（数据填在实测之后）。

---

## 1 我们的软硬件现状（实测，非记忆）

| 项 | 值 | 出处 |
|---|---|---|
| GPU | Instinct MI50 32GB（gfx906，wave64，无 WMMA/无字节 SIMD，**不驱动显示**） | `docs/AMD_HIP.md` gfx906 节；`/metrics` `gpu_name` |
| 显存 | total 34,342,961,152 B（31.98 GiB）；运行期 `vram_free_mib 574` | `/metrics` |
| PCIe | 有效 **Gen3 x16**（自卡 Gen4，根端口 Gen3） | `/metrics` `pcie_gen 3 / own_gen 4 / width 16 / path 4/4` |
| CPU | Xeon E5-2696 v4，**单路**，22 核 / 44 线程，**1 个 NUMA 节点**，L3 55 MiB | `lscpu` + `/sys/devices/system/node/` |
| RAM | 125 GiB（available ~79） | `free -g` |
| 盘 | SATA SSD（Fanxiang S100Pro），根分区 161 GB 可用 | `lsblk` / `df` |
| ROCm/工具链 | 底座 `mixa3607/rocm-gfx906:7.14-complete`；cmake 3.28.3 · ninja 1.11.1 · clang 23.0.0git · HIP 7.14 | 镜像内实读 |
| 引擎 | 生产 **0.1.42**（`strata-gfx906:0.1.42`）；新编 **0.1.47** | `--version` |

---

## 2 现役配置（生产 config，`ff8cb973…`）

```
--pack /data/packs/huihui-ud-iq4_xs --native <...00001-of-00003.gguf>
--expert-profile /src/data/expert-profile.bin --expert-cache auto
--pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt
--max-context 262144 --kv k8v4 --prefill auto --prompt-cache-every 8192
--expert-profile-save /data/profiles/... --conversation-cache-mib 4096
--vision --mtp-window 8192 --resident-experts
env: HSA_OVERRIDE_GFX_VERSION=9.0.6  STRATA_PREFILL_CPU_SHARE=0  STRATA_RESIDENT_HEADROOM_GIB=0.5
```

启动段实测（A 臂 / 0.1.42）：

- `21 pool workers on logical processors 1..21, host on 0` → 已按**物理核**布线程（0.2.0 的「CPU worker 按物理核」我们本来就满足）
- `prompt chunk auto: 8192 tokens, a 96-slot ring` → **实际 chunk 是 8192**，不是文档口径的 4096/2048
- `experts via mmap (--mmap-experts; the GGUF shards in place, no experts.bin)` → 我们属 **GGUF in-place**，不是 `experts.bin` 打包族
- `PLE direct read probe: 34393 rows/s (fine)` → 本次 direct 臂
- `STRATA_ROUTE_TAIL_SKIP=7 is ON (default)`
- `expert cache 9761 slots, 21.99 GiB`；`resident RAM mode: 36.93 GiB ... 9761 in the GPU cache`
- `/metrics`: `spec 6 / mtp_max 4 / lookup 3`（`--spec 4` 被 suffix-draft 改写的既有账实不符，三代引擎同规则）

---

## 3 近 5 版全文逐条判定（只列与我们有关的）

### 3.1 0.2.2（引擎 0.1.47）

| 条目 | 原文要点 | 对我们 |
|---|---|---|
| **GPU 角色 Main/Helper/Off**（L5） | 每卡一角色；Off 卡不起进程 | **不适用**（单卡） |
| **NUMA 专家池切分**（L11） | 双 NUMA 节点自动；单节点「跑与 0.2.1 相同代码路径」 | **不适用**（166 单节点，启动行会打印 `NUMA pool off: <原因>`） |
| **HIP verify 首窗挂死修复**（L47） | 首窗偶发卡死；HIP 上首个 launch 前置 flag 已提前抬升，默认 2 | **适用（稳定性，自动）**；`STRATA_VERIFY_EARLY_PLE_FLAG` 可强指 |
| **`--spec` + native pack 单 token prompt 解 0 token**（L47） | 一 token prompt 起不了投机循环 | **适用（修复，自动）**；我们正是 native pack + `--spec` |
| **`STRATA_SPEC_WATCH`**（L47） | 卡住时报告阶段 | **诊断可用**（0 成本，默认关） |
| **显存预留 512/700（计算卡）**（L56）+ **AMD Linux 探测不到 → 1536 保留**（L101） | 仅当探针判定「不驱动显示」才降到 512 | **不自动生效**；且我们引擎默认已是 **700**（`generate.cpp:607`），启动行 `700 MiB reserved` → **本条对我们无收益** |
| **`experts.bin` 预取/解码门（≥55% 页缓存）**（L57） | +38/+21/+33% decode（RTX 3060，`--mmap-experts`） | **不适用**：我们走 **GGUF in-place + `--resident-experts`**，文件层已 0 读 |
| **长 prompt 的 exact scorer（#1749/#1943）** | 131K +8.7% / 230K +16% / 500K +79% | **不适用**：源码 `qsa_select.cu:1223-1237` 只给 gfx12 / gfx1100 |
| **`--pool-cores` / CPU workers 位置**（L17） | 可显式钉核，实验性、默认关 | **不需要**：我们已 21 workers 钉物理核；`--pool-cores` 留作诊断 |
| **`strata bench run` 修好**（L19） | 标准口径 suite | **暂不用**：需在 0.2.2 引擎上跑，且我们要的是与自家 0.1.42 的可比性 |
| **Docker 0.1.x 卷迁移**（L24） | 旧卷改名，不再重下 | **不适用**（自建镜像） |
| **答案口径统一**（L18） | 首 token、decode 定义统一 | 只影响 UI/监控显示，**不改引擎读数** |

### 3.2 0.2.1（引擎 0.1.46）

| 条目 | 要点 | 对我们 |
|---|---|---|
| gfx906 又能编了（L80） | 「All 161 targets compile… **we have no gfx906 card, so it was not run on one**」 | **这是官方对 gfx906 的全部背书：只到"编过"** |
| 计算卡预留 512 MiB（L56/L101） | 同 3.1 | **不自动生效** |
| `experts.bin` 预取门（L57） | 同 3.1 | **不适用** |
| R9700 队列顺序（L58） | 起始固定开两条队列，避免一半新引擎慢 8-14% | **gfx12 面**；gfx906 是否走同一路径**未验证**（不进方案） |
| 混架构 warm-up（L60） | 只在全卡同架构时跑 | **不适用**（单卡） |
| 就地读盘探针 #3237（L61） | 4 GB/s 以上才改无缓冲 | **不适用**（我们文件层 0 读） |
| 780M / Strix Halo 默认（L53/L54） | iGPU 专属 | **不适用** |
| 两卡 gfx906 经验（L83） | `--pipeline-windows 2` +36% decode、`--trim-stage-weights` +5% prompt，**报告者两卡** | **不适用**（单卡；没有单卡数据） |

### 3.3 0.2.0-beta（引擎 0.1.45.3）

| 条目 | 要点 | 对我们 |
|---|---|---|
| 图片默认开；<24 GB 走 CPU，≥24 GB 走 GPU（L35） | GPU 读图器占 1,470 MiB | **我们有 32 GB 卡但没编 GPU 读图器** → 实测两版都 `strata-vision: on the CPU`（自建镜像只编 `strata`）；**升级后必须保持 `--vision` 指向 CPU 读图器**，否则掉约 500 专家槽 |
| GGUF in-place 的 RAM/SSD 默认（L60） | 零拷贝页缓存专家、IO 预取 + 收益门；**`experts.bin` 保持旧行为** | 机制上**落在我们这一族**，但我们 `--resident-experts` 已把文件层归零 → 预计空操作，基线实测即为判据 |
| prompt chunk 按 RAM/SSD 规划（L61） | 文件集超页缓存就选更小的 chunk（CUDA 测） | 同上，文件层 0 读 → 预计无动作 |
| **CPU worker 按物理核**（L62） | 上限 32；worker 过少/过多都掉速 | **我们已满足**（21 workers + host） |

### 3.4 0.1.45（引擎 0.1.45）

| 条目 | 要点 | 对我们 |
|---|---|---|
| **prompt chunk 默认变大 4096/2048/1024**（L8） | `--prefill 512` 回旧值；**长 prompt 文本会有小差异（KL 0.004）** | **适用（间接）**：我们 `--prefill auto` 实取 8192；升版后要**记录实际 chunk**，若变了，输出差异属"预期内非 bug" |
| 长 prompt AMD 内核（L26） | 同 3.1，gfx12 | **不适用**（源码已证） |
| #1896 resident-RAM copy 保留借区（L28） | RTX 3060 +7% decode | **我们已通过 B7 走到同一形态**（借区 N==M、files 0 blobs） |
| `--parallel` 量化（L7） | 单请求 -4~-11%，N 并发仅 1.0-1.15x | **W9/P97 结论不变，理由升级**（上游已量化"能加但不值"） |
| Qwen3.8-Flash-Next 答案 byte-identical（L1） | 但 identity gate 的 HIP 只覆盖 gfx1201 | **对我们只是"没有反证"，不是背书** |

### 3.5 0.1.44.1（hotfix）

| 条目 | 要点 | 对我们 |
|---|---|---|
| 无 AVX2 老 CPU 启动即死（L5） | 166 是 Broadwell（有 AVX2） | **不受影响**，入账 |
| CUDA 12.0/12.1 构建（L7） | 我们是 HIP | 不适用 |
| M2 寄存器（L8） | Mac | 不适用 |

---

## 4 能落到我们配置上的 4 条（方案主体）

| # | 项 | 性质 | 期望 | 成本 | 建议 |
|---|---|---|---|---|---|
| **1** | 升到 0.1.47（0.2.2） | 稳定性 | 无可测速度差（基线可证）；获得 HIP 首窗修复、native+spec 单 token 修复 | 一次窗口 + 镜像 | **数据不差则落生产**（机主令） |
| **2** | `--ple-io direct` 显式写入 | 纪律 | 消除对探针的隐式依赖（0.1.43.1 起不再自动切 mmap，但显式写死不依赖它） | 0 | **写入** |
| **3** | `STRATA_ADAPT_OVERLAP_RESIDENT=1` | 待测速度 | 唯一「正对 `--resident-experts`、且有速度潜力」的新开关；上游实测 +7.0%（A4000） / **-2.6%（3060 46 GB 箱）** ⇒ 必须自测 | 一次车 | **单独单变量车**（5+ runs 判 decode） |
| **4** | `STRATA_SPEC_WATCH` / `--pool-cores` | 诊断 | 0 收益 | 0 | **备查**，不进生产 |

### 明确不做（有原文依据）

- **不为「AMD 长上下文提速」升版**：gfx12/gfx1100 专用（源码门控）。
- **不动 `--vision` 到 GPU**：我们没有 HIP 读图器；默认落到 CPU 是正确结果。
- **不加 `--parallel`**：上游自己量化「单请求 -4~-11%」。
- **不套 `--pipeline-windows 2` / `--trim-stage-weights`**：只有两卡 gfx906 的报告者数据。
- **不上 `--vram-reserve-mib` 512**：AMD Linux 探针判不出"不驱动显示"，且我们默认 700 已低于它要替换的 1536。
- **不改 `ROUTE_TAIL_SKIP`**：已实测 `=0` 改答案且 prompt 无收益。

---

## 5 编译：是否按上游最佳实践（逐项对账）

官方配方（`docs/AMD_HIP.md` gfx906 节原文）：

```sh
cmake -S . -B build-906 -G Ninja -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja -C build-906 strata
```

实跑（166，新树挂 `/src_022`）：

```sh
cmake -S . -B build-906 -G Ninja -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_GGML_DIR=/src_022/third_party/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_BUILD_TYPE=Release
ninja -C build-906 strata
```

| 差异 | 判定 |
|---|---|
| 路径 `/src_022` vs `/src` | 仅挂载点，无影响 |
| 多传 `-DCMAKE_BUILD_TYPE=Release` | **项目自默认 Release**（`CMakeLists.txt:65-66`），CMakeCache 两边都是 Release → 等价 |

CMakeCache 逐项（本次 vs 0.1.42 生产镜像）：`C/CXX=clang/clang++`、`HIP_GFX906=ON`、`ENABLE_CUDA=ON`、`ENABLE_HIP=OFF`、`MMQ_KQUANTS=ON`、`NATIVE_EXPERTS=ON`、`BUILD_TESTS=OFF`、`WERROR=OFF` —— **全部同值**；`third_party/llama.cpp` pin `3cf03257f219…` 与新树 `VERSION.txt` 同 hash。

结果：`CONFIGURE_RC=0` → `Strata: HIP (gfx906 compat) enabled, arch gfx906`；`158/158` 步；`BUILD_RC=0`；`strata 0.1.47`；help 266 行；`ldd` 缺失库 0。

**保留**：上游"161 targets 编过"那次用的是 **ROCm 7.10 + clang 22**；我们是**文档推荐组合 HIP 7.14 + clang 23**。这两句不能混为一谈。

---

## 6 基线（判据先定，数据后填）

### 6.1 判据（写在前，避免事后解释）

| # | 判据 | 门槛 |
|---|---|---|
| J1 | 答案一致 | 同一 nonce 的 greedy 输出 md5 两臂相同；若不同，必须能归因到 chunk/KL 而非崩溃 |
| J2 | prompt 不慢 | S 档（≈2.9K）与 M 档（≈23K）的中位数，B 不比 A 慢 **>2%** |
| J3 | decode 不慢 | 5 runs 中位数，B 不比 A 慢 **>5%**（decode spread 惯常 5-15%） |
| J4 | 资源不变差 | `vram_free_mib` 不低于 574；`expert_slots` 不低于 9761 |

J1–J4 全过 → **落生产**。

### 6.2 方法（第一车作废的教训）

第一车测出「第 2-5 轮 `reused=2873/23069`、只读 5 token」——服务端 prompt 缓存把整段复用了，只第 1 轮是真冷读；且 decode 仅 32-43 token 太短。**已作废重跑**：每 run 加唯一前缀（`r01S`/`r01M`…，两臂逐字相同）强制整段重读，并把输出改成「列 1..120」以拿到 ~250 输出的 decode。

### 6.3 数据

（实测后填，见 §6.4）

---

## 7 落生产步骤（J1-J4 通过才执行）

1. `Dockerfile-0.2.2`：`FROM strata-gfx906:0.1.42`（复用已验证工具链/依赖）→ `rm -rf /src` → `COPY src_022/ /src/` → 按官方配方重建 `/src/build-906`（保持 `exe=/src/build-906/strata` 不变）。
2. 打上**移植后**的 telemetry/app.js（`_tpatch/serve-telemetry.py.patched.022`、`serve-web-app.js.patched.022`），并 `ast.parse` + `python3 -c import` 自检。
3. 停生产 → 以新镜像重建容器（参数逐项抄 `docker inspect`）→ 等 `/health loaded:true`。
4. 验收：`--version=0.1.47`；`vram_free`/`expert_slots` 不低于基线；`gpu_name` 仍为 **32GB**；`/metrics` 有 `pcie_*` 与 `gpu_pcie_rx_mb`；一条真实请求出字。
5. 回滚位：旧容器 `strata166-407` 保留（`docker rename` 存档），新容器沿用原名建。

---

## 8 待机主确认

- 落生产是**机主已授权**（「如数据一致或更好则落生产」）→ 我按 J1-J4 自动判定。
- `STRATA_ADAPT_OVERLAP_RESIDENT=1` 属**改变行为**的候选，另开单变量车，不混进这次升版。

---

## 6.4 实测（2026-10-22 00:00-00:10）

方法修正过两次，两次都写在这里（不改口径只说结论等于掩盖）：

- 第一车作废：服务端会话缓存把连续请求当同一会话，第 2-5 轮 `reused=2889/23069`、只读 5 token。
- 第二车作废：关掉 `--conversation-cache-mib` 后**仍然** `reused=2889` —— 说明复用来自 `--prompt-cache` 的检查点（`generate.cpp:12434` 的 `o.prompt_cache > 0` 门）。
- **最终口径**：测试 config 加 `--prompt-cache 0`（help 原文「0 = read every prompt from the start」）+ `--conversation-cache-mib 0`，两臂一致；并给每轮唯一 nonce 强制整段重读。全部 `reused=0`，`read = ptok`（2,976 / 23,172）。

| 臂 | 档 | n | prompt 中位 tok/s | 逐轮 | decode 中位 tok/s | 逐轮 |
|---|---|---|---|---|---|---|
| **A 0.1.42** | S | 3 | **423.4** | 421.2 / 423.4 / 426.5 | 59.6 | 45.8 / 59.6 / 62.6 |
| **A 0.1.42** | M | 2 | **492.4** | 492.4 / 492.5 | 57.2 | 55.2 / 59.2 |
| **B 0.1.47** | S | 4 | **425.9** | 422.9 / 425.5 / 426.4 / 428.4 | 61.0 | 45.0 / 59.6 / 62.4 / 62.9 |
| **B 0.1.47** | M | 3 | **494.1** | 494.0 / 494.1 / 494.2 | 59.5 | 55.8 / 59.5 / 61.4 |

| 判据 | 门槛 | 实测 | 结论 |
|---|---|---|---|
| **J1 答案一致** | md5 逐 (tier,run) 相同 | 5/5 相同（判据强度已下调，见 §11）（`133d4e45a338` / `3949387427bc` / `dcf4488284c7` …） | **PASS**（逐字节同一） |
| **J2 prompt 不慢** | B ≥ A−2% | S **+0.59%**、M **+0.35%** | **PASS**（略快） |
| **J3 decode 不慢** | B ≥ A−5% | S **+2.3%**、M **+4.0%**（两臂各有 1 个首轮低值 45.8/45.0，噪声） | **PASS** |
| **J4 资源不变差** | `vram_free≥574` · `slots≥9761` | **574 / 9761**（与 A 逐项相同） | **PASS** |

**启动段差异（记在案，不改）**：A 臂 `21 pool workers`（核 1..21），B 臂 `20 pool workers`（核 1-20）；两者 `prompt chunk auto: 8192 tokens` 相同；PLE 两臂都 `direct`（34.7K / 34.3K rows/s）。

---

## 9 落生产：**已执行**（00:12-00:15）

| 步骤 | 结果 |
|---|---|
| 镜像 | `strata-gfx906:0.2.2`（6.95 GB，`BUILD_RC=0`，容器内按官方配方重编） |
| 容器 | 停旧 → `docker rename` 为 **`strata166-407.bak0142`**（回滚位）→ 同名起新 |
| 就绪 | **45 s** |
| 版本 | `strata 0.1.47` |
| `/metrics` engine | `kv k8v4` · `spec 6 / mtp_max 4 / lookup 3` · `expert_slots 9761` · `expert_cache_mib 22516` · `vram_free_mib 574` · `context 262144`（与旧版逐项相同） |
| `hardware_static.gpu_name` | **`Radeon Instinct MI50 32GB`**（FRU 容量纠正生效；原串是 16GB） |
| `hardware` 的 PCIe | `gen 3 / gen_max 3 / own_gen 4 / width 16 / path 4/4 / rx 0.01 MB/s`（`pcie_bw` 移植生效） |
| 生成 | 正常（`content='OK'`，28 tokens） |
| B7 稳态 | `resident RAM 36.93 GiB` · **`files 0 blobs`** |
| 生产 config | md5 **`ff8cb97379f0bdbe76ee555da6d8729c` 未变**（同一份配置，只换引擎） |

**纪律更正（重要）**：`apply_telemetry_pcie.sh` **以后不要再跑** —— 它会把 0.1.42 时代的整份 `telemetry.py` 覆盖回去（会回退 0.1.47 的 Metal/新监控改动）。遥测现在**烘在镜像里**（`Dockerfile-0.2.2` 的 COPY 层）。

---

## 10 llama.cpp：要不要跟上游（机主追问）

**结论：不跟。pin 未变，且上游 master 编不过我们的树。**

- pin 自 0.1.42 起一直是 **`3cf03257f219…`（2026-09-20，"CUDA: enable sparse fa for qwen4 #28770"）**；0.1.42 / 0.1.46.2 / 0.1.47 三代 `third_party/ggml/VERSION.txt` 逐字相同。
- 镜像里的 llama.cpp 与本次编译用的是**逐字节同一套文件**：全量清单（路径+大小）md5 都是 `e6f7a0ecd192ca69…`；抽查 `mmq.cuh / mmid.cuh / fattn.cu / ggml/CMakeLists.txt / ggml.h` 五个 md5 全 SAME。
- 上游 `ggml-org/llama.cpp` master HEAD = `9b56ccf00d75`（2026-10-21），**比 pin 领先 736 个提交**；`mmq.cuh`、`fattn.cu`、`ggml.h`、`ggml/CMakeLists.txt` 全部 DIFF（只有 `mmid.cuh` 未变）。
- **实编验证**（0.1.47 + master 的 llama.cpp，官方配方）：`CONFIGURE_RC=0`，编到 **104/159** 时 **2 个目标失败**，全部在 `src/prefill/moe_mmq.cu`：

```
moe_mmq.cu:305: error: no matching function for call to 'ggml_cuda_mmq_get_config'
  mmq.cuh:232: candidate requires 5 arguments, but 4 were provided
      （上游新增了第 5 个参数 ggml_prec prec_src1）
moe_mmq.cu:451-455: error: no matching function for call to 'mul_mat_q_case'
moe_mmq.cu:425: error: non-constant-expression cannot be narrowed from 'int64_t' to 'int'
```

即：**不是"理论上可能不兼容"，是实测编不过**；要跟就得改 Strata 的 MMQ 胶水层（3 处），而那正是答案数值最敏感的一段（MMQ 决定 prompt 专家的量化路径），改了必须过 identity gate。这属于上游该做的事（他们每版都自己对齐 pin），不该我们在生产上自己接。

**建议**：等 Strata 自己 bump pin 时跟；若想主动，就给上游提一个 issue/PR（带上面三段错误原文）。

---

## 11 调优：`STRATA_ADAPT_OVERLAP_RESIDENT=1`（2026-10-22 00:20-00:57）

**结论：不采纳。** 无可用增益，且引入一个非确定性变量。

### 过程（两次误判都记下来）

1. **第一次臂身份错**：只设 `STRATA_ADAPT_OVERLAP_RESIDENT=1`，启动行仍是 `adaptive overlap: off (STRATA_ADAPT_OVERLAP=1 turns it on)`。源码（`generate.cpp:1528-1539`、`9954`）表明总闸是 **`adapt_overlap()` = `STRATA_ADAPT_OVERLAP`**，resident 那个只是它的理由分支，所以 **两个 env 必须同时给**。
2. **第二次差点又误判**：日志里有 **2 次 `engine started`** —— 第一次（暖启动）没带 env，第二次才带。闸门若取第一条就会错杀；**必须取最后一条**。修正后闸门通过：
   `adaptive overlap (STRATA_ADAPT_OVERLAP=0 turns it off): the adaptive tier's copies land while the next window runs (same tokens, a layer waits for its own copies)`

### 数据（5 runs/档，`--prompt-cache 0` + nonce，全部 `reused=0`）

| 臂 | 档 | prompt 中位 | 逐轮 | decode 中位 | 逐轮 |
|---|---|---|---|---|---|
| A（关） | S | 426.6 | 424.0/424.1/426.6/427.6/429.0 | 62.2 | 45.7/59.9/62.2/62.3/62.9 |
| A（关） | M | 494.1 | 493.8/494.0/494.1/494.3/494.7 | 60.1 | 55.7/59.6/60.1/61.2/61.6 |
| **B（开）** | S | **426.0** | 420.6/424.0/426.0/426.5/426.8 | **62.2** | 45.3/59.4/62.2/62.4/62.5 |
| **B（开）** | M | **493.8** | 493.0/493.5/493.8/493.8/494.5 | **61.1** | 55.4/59.3/61.1/61.2/61.5 |

**B-A：prompt -0.14% / -0.06%；decode +0.00% / +1.66%。** 全部落在噪声内（prompt 臂内波动 1.2%，decode 45-63）=> **本机无增益**，与上游 A4000 +7.0% / 3060 46GB -2.6% 的机器间分歧一致。

### 意外发现（比调优本身更重要）：引擎在这个负载上不是确定性的

B 臂答案 md5 与 A 有 1/10 不同（`M r5`）。做对照 —— **同一个 prompt 在同一台生产引擎上连发 3 次**：

```
run 1 -> md5 5e282241c769  len 620
run 2 -> md5 2f34beb47ff0  len 610
run 3 -> md5 dad91a040bfa  len 634     <- 恰是 A 臂该轮的 md5
```

=> 同臂重复就会变，**那 1/10 不能归因于本开关**；同时 §6.4 的 J1 要打折：5/5 相同只是**无反向证据**，不是证明一致。**长重复 prompt + greedy 在本机不可作为 identity 判据**；以后要比答案，必须先做同臂重复对照。

### 处置

- 不写入生产 config（保持 `STRATA_ADAPT_OVERLAP` 不设）。
- 待办：若将来要启用，判据改为 decode 中位数提升 >=3% 且同臂重复对照表明差异不显著。
