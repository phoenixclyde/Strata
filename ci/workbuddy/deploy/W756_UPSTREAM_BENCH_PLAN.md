# W756 上游社区 bench：规范、缺口与我们的报告方案
> 本文件的内存容量统一用 **GiB**（与 bench README 的 Units 声明一致）；**带宽**用十进制 **GB/s**。

日期 2026-10-10 02:2x ｜ 触发：机主「上游有没有 bench 的标准，我们可以基于我们的硬件报一个测试数据给他」

## 1 结论：**有正式规范，而且我们正好补一个上游自认的缺口**

上游的规范在 **`docs/COMMUNITY_BENCHMARKS.md`**（本机 `deploy/tmp/src411/Strata-0.1.41/` 实读，全文 178 行）。它包含四件事：

1. **What to record** -- 硬件（GPU/VRAM/CPU/RAM/存储/**PCIe 链路**/功耗上限）、软件（OS/驱动/ROCm/引擎版本/commit/构建选项）、
   模型（仓库+revision/量化/GGUF 文件名/**自定义 pack 与 profile 要可复现**）、设置（启动命令/上下文/KV 类型/缓存/prefill/MTP/采样）、
   负载（脚本/实际 token 数/输出上限/重复次数/**缓存状态**）。
2. **How to measure** -- **每格至少 3 次**，公布**全部**与**中位数+范围**；区分「新处理 vs 复用」并**报引擎日志里的 reused/read 数**；
   四类量分开：**prompt 吞吐 / decode 吞吐 / TTFT / 总时延**；明确说**不要用"生成 token 总数 除以 总请求时间"当 decode**
   （那会把预填算进去）；失败/取消的请求要单列。
3. **Optional correctness checks** -- 长上下文召回用官方 **`tools/needle_bench.py`**（5858 B，已实读）：
   `python tools/needle_bench.py --url http://127.0.0.1:8090 --lengths 32k,128k --depths 10,50,90 --out needles.json`。
4. **Submit a report** -- fork -> 建 `bench/results/YYYY-MM-DD-community-<短硬件标签>/` -> 放 `README.md`（按模板）+ 每 run 的 JSON/CSV + 小脚本
   -> **PR 到 `Niko1221/Strata:main`**；并且**results-only 的 PR 要与引擎改动分开**。

### 1.1 已有的社区报告（`docs/COMMUNITY_BENCHMARKS.md` §Community reports 逐条）

| 日期 | 硬件 | 模型/上下文 |
|---|---|---|
| 2026-09-30 | RTX 5090, Core Ultra 9 285K, 64 GiB | Flash-Next **IQ2_XS**, 131072 |
| 2026-10-03 | **2x MI50 16 GiB (gfx906)**, Xeon E5-2666 v3, 32 GiB | **Coder IQ1_M**, 131072, **layer split** |
| 2026-10-04 | 2x Intel Arc Pro B60, Ryzen 5 5600 | SYCL 端口 |
| 2026-10-07 | 2x Quadro RTX 4000 8 GiB, Xeon E5-2620 v3 | IQ2_XS, 131072 |
| 2026-10-08 | 2x TITAN RTX 24 GiB, **Xeon E5-2696 v4 无 AVX-512**, 125 GiB | IQ3_S, 262144 |

### 1.2 缺口（这是我们的机会）

**`docs/AMD_HIP.md:504-506` 逐字**：

> **Not done:** setup.py detection and an automatic build, Windows, images (`--vision`), MI60 and Radeon VII (the same
> gfx906 ISA; not run), **a single-card run**, the tensor-split experiment

-> **上游自己写着 gfx906 的"单卡 run"没做**。而已有的那份 gfx906 报告是 **2 卡 + `layer_split 27`**。

**我们的机器正好是那个形态**：**单张 MI50 32 GiB**（比那两份 16 GiB 卡更大，能单卡装下全部专家）。

## 2 我们与已有 gfx906 报告的差异（互补，不是重复）

| 维度 | 已有（JeanP00l, 2026-10-03） | 我们 |
|---|---|---|
| GPU | **2x MI50 16 GiB**，layer_split 27 | **1x MI50 32 GiB 单卡**（上游标注未做） |
| GPU 功耗上限 | **85 W/卡 人工设** | 未设（默认） |
| CPU | Xeon E5-2666 v3（10C/20T，无 AVX-512） | **Xeon E5-2696 v4**（22C/44T，无 AVX-512） |
| RAM | 32 GiB DDR4 | **128.7 GiB** |
| 模型 | Coder **IQ1_M**（~1 bit） | **unsloth UD-IQ4_XS**（~4 bit，`huihui` abliterated 权重） |
| 上下文 | 131072 | **262144**（模型原生窗口） |
| 引擎 | 0.1.38 + PR #638/#639/#640/#637 | **0.1.41**（release 版） |
| KV | `--kv int8 --kv-resident 32768` | `--kv k8v4`（4-bit KV，更激进） |
| PCIe | 3.0 x16（探针 13.8 GB/s；**带宽用十进制 GB/s**） | **Gen3 x16 有效链路**（根口瓶颈，实测同量级） |

-> 单卡 vs 双卡、4-bit vs 1-bit、262K vs 131K、4-bit KV vs int8 KV -- **四项都不同**，且**单卡正是上游的已知缺口**。

## 3 报告设计（按上游模板逐节填）

### 3.1 Hardware and software（已实测，可直接填）

- **GPU**：1x AMD Instinct MI50 32 GiB（Vega 20, gfx906, wave64；`1002:66a1`；VBIOS `113-D1631711-100`）；
  VRAM **34,342,961,152 B**（实读）；**功耗上限未人工设置**（默认）；PCIe 根口上限 **8 GT/s x16**，
  全链有效 **Gen 3 x16**（`lspci -vv` 全链逐跳实读；本卡自身跳 16 GT/s）；**无 peer/无 NVLink**（单卡）。
- **CPU/RAM**：Xeon **E5-2696 v4**（22C/44T，AVX2，**无 AVX-512**）；RAM **128.7 GiB**；SATA SSD。
- **OS/runtime**：Ubuntu，kernel **7.0.0-34-generic**，内核 amdgpu 驱动；
  ROCm **7.14** 来自社区镜像 **`mixa3607/rocm-gfx906:7.14-complete`**（AMD 现行 ROCm 不再带 gfx906 库）。
- **引擎**：**0.1.41**，release 镜像 `strata-gfx906:0.1.41`；
  引擎二进制 md5 **`160611838796d4b172ec3a642ccd988d`**（24,982,264 B）。
- **其它负载**：本机的其它 GPU 服务（RTX 2070 侧、ASPEED BMC）**不参与**本次推理；容器只挂这张 MI50。

### 3.2 Model and configuration

- **权重**：`huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF` 的 **`unsloth-UD-IQ4_XS`**（Qwen3.8-Flash-Next，262144 原生上下文）。
  专家类型 **零 K-quant**：48 层中 44 层 `IQ3_S gate/up + IQ4_NL down`、4 层 `IQ4_XS + Q8_0`（`native_experts.txt` 实读）。
- **自定义 pack**：`/data/packs/huihui-ud-iq4_xs`（由仓库 `tools/iq_pack.py` 生成），
  `index.txt` **1079 张量**、`dense.bin` 1,384 MiB；非专家张量分布（W754 实读）：
  **Q8_0 303 个 / BF16 483 个（1407 MiB）/ F32 292 个 / F16InF32 1 个**。
- **配置**：context **262144**、`--kv k8v4`、expert cache `auto`（**9761 槽**，W767-W770 实测；W716 记的 9757 是 P43 采纳前）、`--prefill auto`、
  MTP `--spec`（自适应窗口，`mtp_max` 4）、`--pcie-frac 0.20`、`--spec-min-p 0.70`、
  `--prompt-cache-every 8192`、`--conversation-cache-mib 4096`；**vision 开着（`P99 --vision` ADOPTED）但本轮未实测**（未发图）、无 calibration、无 speed projection。
- **服务补丁**：serve 层有两个**本地覆写**（`telemetry.py` 补 AMD PCIe 读数 / `web/app.js` 修 sparkline 轴），
  **不改引擎、不改输出**；`engine 补丁面 = 0`（`docker diff` 只显示这两个 serve 文件）。
- **采样**：贪心（`temperature 0`）。

### 3.3 Method（照规范）

- **速度**：3 个长度（**4096 / 32768 / 128000** prompt token），**每格 3 次**，输出上限 **256**，
  唯一请求、`temperature 0`；**逐 run 记录** 引擎的 `prompt_ms / decode_ms / reused / drafts`，
  并**同时给 hit rate**（我们的纪律：口径须带协变量）。
- **needle**：官方 `tools/needle_bench.py`，长度 **32k / 128k / 262k**，深度 10/50/90，
  在容器内跑（`/src` 是仓库根）。
- **口径声明**：decode 取**引擎自报 `decode_ms` 与 `output_tokens`**，**不用总时延反推**；
  预填区分**冷（reused=0）**与**温（reused>0）**并分别列。

### 3.4 Correctness and limitations（照实写）

- 本机是**单卡、单用户、单并发**；**并发吞吐未测**。
- 引擎在 gfx906 上是**兼容构建**（`-DSTRATA_HIP_GFX906=ON`，**不定义 `STRATA_USE_HIP`**）；
  上游 `AMD_HIP.md` 的另一处自认（`mixa3607` 镜像 + 无 AVX-512 主机）与我们一致。
- 权重是**社区 abliterated 变体**，与上游报告用的官方 GSQ-RCO / unsloth 版本**不同**，本报告只代表这个 pack。
- 单卡与双卡的**直接对比不是 paired**（不同机器、不同模型、不同量化）。

## 4 提交流程（照规范 §Submit a report）

1. fork `Niko1221/Strata`，建分支；
2. 新建目录 **`bench/results/2026-10-10-community-mi50-32gb/`**；
3. 放 `README.md`（按 §Report template）+ `matrix.json`（逐 run）+ 小脚本 + `needles.json`；
   **不含模型文件与 pack**；
4. **PR 到 `main`**，只含结果、不含引擎改动。

**我们的现成通道**：166 上 `pr/strata-fork`（remote `git@github.com:phoenixclyde/Strata.git`，
上游 `Niko1221/Strata` 已加为 `upstream`）+ `_mkpr.sh`；开 PR 用 `_w736_post.py` 的凭据配方。

## 5 待跑（等 W1/W3 发车收车后）

| 项 | 内容 | 成本 |
|---|---|---|
| **速度** | 3 长度 x 3 runs = 9 次（128k 的预填每次约 4.5 min => 约 20-25 min） | 中 |
| **needle** | 3 长度 x 3 深度 = 9 次（262k 的 haystack 预填更久） | 中 |
| **装配** | 填模板 + 写 `matrix.json` + 建目录 | 低 |

**注意**：速度与 needle 都**直接打生产 8090**（HTTP），**不需要停生产、不需要臂** --
因为要报的就是"我们实际在跑的配置"。这与 W1/W3 的 A/B 性质不同（那要停生产）。
