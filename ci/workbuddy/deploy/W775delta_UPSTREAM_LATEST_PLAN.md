# W775delta · 上游最新代码入库 + 逐版说法 + 优化方案（2026-10-21）

> **前情更正**：我先前下的 `v0.2.0-beta`（10-19）**不是最新**。核证结果：**最新 release = `v0.2.1`（2026-10-20T08:19Z）**，其后还有 `.1/.2/.3` 三个 hotfix tag；`main` HEAD 相对 `v0.2.0-beta` **ahead 162 commit**。
> **现在的基线（已入库）**：`deploy/tmp/src_latest/`（4,518 文件）= `main` HEAD `cbfd5b92`，`project(strata VERSION 0.1.46.2)`。旧的 `src142`（0.1.42）保留作对照，`src020`（0.2.0-beta）作废不再用。
> **口径**：实测（本机/生产实读）· 源码（对着 `src_latest` 读的）· 上游逐字（release note 原文）· 推测（显式标注）。

---

## 一、逐版说法（0.1.43 至 0.2.1，只记"与我们有关"的）

| 版本 | 时间 | 与我们相关的说法（逐字要点） | 对我们的意义 |
|---|---|---|---|
| **0.1.43** | 10-11 | AMD 提速（ROUTE_TAIL_SKIP 默认、measured PCIe share、fused prompt kernels、16K chunk）**逐字限定 gfx1200/gfx1201**；`RDNA3 (gfx11) and older keep their 0.1.42 behaviour` | 提速**不覆盖 gfx906** |
| **0.1.43.1** | 10-12 | hotfix：适配 overlap 回归 opt-in（#2010）；**#2040 SATA SSD 上 mmap 让 prompt 慢约 7x**；**#1984 长 prompt 停在 `layer 1 of the prompt chunk` 并重启引擎**，根因就是"direct 慢就自动切 mmap" | **正中我们的伤口**（166 是 SATA SSD；`--ple-io` 曾被自动切） |
| **0.1.44** | 10-13 | Unsloth 4-8bit + NVFP4；setup 新 RAM 规则（16 GiB 余量则全 RAM）；`STRATA_ROUTE_TAIL_SKIP=0` where every expert is in RAM；`STRATA_PIN_BY_NEED`；**Foresight exchange 保留它搬动的专家（#2134）**；Windows AMD 名称/显存走注册表（#1587） | #2134 可能污染过我们 `P70` 的观测；#1587 是我们 #1735 的 Windows 同类 |
| **0.1.44.1** | 10-14 | hotfix：无 AVX2 的老 CPU 启动即死（NVFP4 查找表用了 AVX/FMA）；CUDA 12.0/12.1 构建；M2 答案错 | 166 是 Xeon E5-2696 v4（**无 AVX-512，但有 AVX2**）=> 不在受害面，但要留意 |
| **0.1.45** | 10-17 | Qwen3.6 支持；**Qwen3.8-Flash-Next 答案与 0.1.44.1 byte-identical**（identity gate：CUDA sm60/sm86、**HIP gfx1201**、A750、M4）；**#1896 resident-RAM copy 保留 prompt 路径的借区**；AMD 长上下文 top-k（131K +8.7%/230K +16%/500K +79%，R9700 测）；`--parallel` 代价量化 | 答案不变是好消息；**gfx906 不在 identity gate 内** |
| **0.2.0-beta** | 10-19 | 形态重构（app + Terminal + 独立 engine，engine 0.1.45.3）；**图片默认开**（<24 GB 走 CPU，>=24 GB 走 GPU，GPU reader 占 1,470 MiB）；安装包矩阵**无 gfx906** | 我们的 32 GB 卡会被判走 GPU 读图器 |
| **0.2.1** | 10-20 | **"gfx906 (MI50, Radeon Pro VII) builds again (#3172, #3271)"**：W4A4 目标拿到 `GGML_USE_HIP`，trellis/moe_f16_kq 进 HIP 列表，**161 个 target 全部编过、`strata` 链接**，但**没有卡、没跑过**；Docker 镜像上线（`rocm-gfx120x/110x/1151`，**无 gfx906**）；`strata bench run` 标准基准；engine 0.1.46；`.1/.2/.3` 是 Terminal/Windows hotfix | **首次有"gfx906 编译通过"的官方声明**，但仅编译级 |
| **main HEAD** | 10-20 | `0.1.46.2`（0.2.1.3 的 Terminal 更新为主） | 我们入库的就是这一棵 |

**一句读法**：**从 0.1.43 到 0.2.1，AMD 侧的"提速"全部落在 RDNA3/RDNA4；唯一明确点名 gfx906 的，是"构建修好了"和"我们没在卡上跑"。**

---

## 二、源码级核实（对着 `src_latest` = 0.1.46.2）

### 2.1 规模与旗标面（0.1.42 对比）

| 项 | 值 |
|---|---|
| `src/` + `include/` 的 C/C++ | **新增 84 / 删除 0 / 改动 137 / 未变 195** |
| 改动最猛 | `generate.cpp` **+243,249 B** · `iq_kernels.cu` +102 KB · `expert_source.cpp` +70 KB · `qsa_select.cu` +68 KB · `prefill.cpp` +64 KB · `verify.cpp` +63 KB |
| CLI 旗标 | **171 -> 175，只多 4 个，零删除** |

新增 4 个（`generate.cpp` help 逐字）：

| 旗标 | 用途 | 对我们 |
|---|---|---|
| `--prefill-pipe R` | 层切分的 prompt chunk 按流水线定尺 | **单卡不适用** |
| `--prompt-cache-spread` | checkpoint 从对话末尾往回铺（密近疏远），而非"最近使用" | **可能有用**（我们 `--prompt-cache-every 8192` + `--conversation-cache-mib 4096`） |
| `--conversation-cache-park-gain N` | 会话推进 N token 以上才 park，避免写一个下一轮就丢的快照 | **可能有用**（多轮场景） |
| `--prefill-head-alias` | 读 prompt 时卸载输出头，读完再装回（8 GB 卡省显存） | **可能有用**（我们 `vram_free 574`） |

### 2.2 PLE 自动切 mmap：**新版对我们有利**

`generate.cpp:3973-3975`（0.1.46.2）逐字：

```
if (pio.mode == PleIo::Direct && std::getenv("STRATA_PLE_PROBE") == nullptr) {
    constexpr double kSlowRowsPerS = 15000.0;   // ~60 MB/s of 4 KiB pages; a healthy NVMe is >100k
```

`generate.cpp:3879-3886`（0.1.45.3 同义，0.1.46.2 保留）：

```
// #1984 #1971 #2040: on no platform is the switch made on its own. ... Linux SATA SSD: the 15K rows/s bar is NVMe-calibrated,
// a SATA SSD tops out at 10-14K with direct's 16 reads in flight and mapped reads were 7x slower.
// The switch is only made when asked for (STRATA_PLE_AUTO_MMAP=1, the 0.1.42 behaviour); otherwise the slow probe warns and direct is kept.
bool auto_mmap = !o.ple_io_explicit;
if (const char* am = std::getenv("STRATA_PLE_AUTO_MMAP"); am == nullptr || std::atoi(am) == 0) auto_mmap = false;
```

=> **`STRATA_PLE_AUTO_MMAP` 缺省为关**。我们量到的 14,560 / 13,268 rows/s 在 0.1.46.2 上**不会再被自动切成 mmap**，只打一行 warning 并保留 `direct`。这是"升级自带"的行为改善。

### 2.3 图片读图器：**升级会默认抢 1.47 GB 显存（必须显式改回 CPU）**

`tools/test_setup_menu.py:194-204` 逐字（这是 setup 的选择函数，也被 config 生成复用）：

```
#2406: "images: yes" gets the CPU encoder on an NVIDIA card under 24 GB ...
self.assertEqual(f("yes", {"vram_gb": 12.0}), "cpu")
self.assertEqual(f("yes", {"vram_gb": 15.9}), "cpu")
self.assertEqual(f("yes", {"vram_gb": 24.0}), "gpu")
self.assertEqual(f("yes", {"vram_gb": 32.0}), "gpu")
self.assertEqual(f("yes", {}), "gpu")            # unknown VRAM: the old default
```

生产现状（实测）：0.1.42 的启动日志是 `strata-vision: on the CPU, 22 threads, no warm-up`（CPU 读图器），而 `vram_free_mib = 574`。
=> 我们的 32 GB 卡在 0.1.46.2 上，**裸 `--vision` 会被判成 GPU 读图器（约占 1,470 MiB）**，直接挤掉约 500 个专家槽。**升级必须改成 `--vision cpu`。**

### 2.4 ROUTE_TAIL_SKIP：**注释与守卫不一致（#1732 同型）**

`generate.cpp:1926-1933` 逐字：

```
// 0.1.43: the HIP defaults of the decode speed push (route tail skip, measured PCIe share) were measured on gfx1201 (Radeon AI PRO
// R9700) and apply on gfx1200 / gfx1201 only; every other AMD part (gfx11, gfx906, ...) keeps its earlier behaviour.  CUDA: always true.
[[maybe_unused]] static bool decode_defaults_arch_ok() {
#if defined(STRATA_USE_HIP)
    ...
    return strata::kernels::gfx_arch_is_gfx12_wmma(p.gcnArchName);
#else
```

而 `CMakeLists.txt:158/164` 给 gfx906 构建定义的是 **`STRATA_HIP_GFX906=1`**，**不是 `STRATA_USE_HIP`**（这正是 gfx906 兼容层的既有事实，也是我们 #1732 修过的同一处坑）。
=> **gfx906 构建走 `#else` 分支、返回 true**，与注释"gfx906 keeps its earlier behaviour"**不一致**。
**影响面待实测**：还要取决于 `all_experts_resident` / `nearly_all_cached` 在 `--resident-experts` 下的取值（`generate.cpp:9781-9784`）。**这条不能假设，必须实测。**

### 2.5 gfx906 构建的可能性

`CMakeLists.txt:75` `option(STRATA_HIP_GFX906 ... OFF)` 仍在；0.2.1 note 声称 161 targets 编译通过、`strata` 链接，**但未在卡上运行**。我们有自己的 gfx906 镜像流水线（`strata-gfx906:0.1.42`），可复用。

---

## 三、优化方案（四阶段，含判据与回滚）

### 阶段 0（0 停机，已完成）
- 源码入库 `src_latest`（0.1.46.2）· 逐版说法表 · 上述四条源码核实。
- **顺带补上我自己的错误**：以后"最新版"必须核 `releases/latest` + `main` HEAD 两个面，不能只看上次的列表。

### 阶段 1（离线，0 停机）：build-only 试编 gfx906
- 在 166 上用与 `strata-gfx906:0.1.42` 相同的配方试编 0.1.46.2（`-DSTRATA_HIP_GFX906=ON`）。
- **判据**：`strata --version`、`--help` 能出；不要求能跑。
- **为什么先做**：0.2.1 只说"编译过"，我们这台机器的 ROCm / 编译器组合是另一套；**若连编都过不了，后面全部作废**。
- **风险**：构建吃 CPU 与内存（22 核、125 GiB 限额），会拖慢生产解码 => 放在**低峰**或临时停生产做。

### 阶段 2（停机窗口约 20-30 min）：同 config 双版本 A/B
一次窗口做三件事，**每臂只动一个变量**：

| 臂 | 引擎 | 关键设置 |
|---|---|---|
| A（基线） | **0.1.42** | 现役 config 原样（`--ple-io` 不传 = 现在实际是 direct 或 mmap，**按启动行记录**） |
| B | 0.1.42 | `--ple-io mmap`（显式钉死） |
| C | **0.1.46.2** | 现役 config + **`--vision cpu`** + `--ple-io direct`（显式） |

- **测**：短（约 3-5K）与长（约 64K / 93K）prompt tok/s、decode tok/s、5+ runs、ABBA 排冷热。
- **判据（三条同时成立才算过）**：
  1. **答案一致**：固定 prompt 的输出 token id 在 A 与 C 之间应当一致（0.1.45 逐字保证 Qwen3.8 族 byte-identical；不一致即停）；
  2. **显存不退化**：`vram_free_mib` 不低于现役 574（`--vision cpu` 下应当不降）；
  3. **长 prompt 不慢于 A**（这是升级的底线；快多少是加分）。
- **必记**：每臂的启动段 `PLE direct read probe` 行（臂身份核验）、`route tail skip` 行（2.4 的待测项）、`resident RAM mode` 行。
- **回滚**：临时实例独立端口；异常即 `docker start strata166-407`；恢复后核 `config md5 == ff8cb973...` + `/health` + 6 容器。

### 阶段 3（仅在阶段 2 通过后）：落生产
按铁律走：`register` 增/改 -> `gen_config.py --write` -> 推 166 -> `restart` -> `verify_config FAIL=0` -> `todo_reconcile --strict GAP=0`。
**必须同时做**：
- 新增 register 项：`--vision cpu`（理由：0.1.46 起裸 `--vision` 在 >=24 GB 卡走 GPU，占 1,470 MiB）；
- `--ple-io` 显式写 `direct`（理由：0.1.42 实验已证明窄 bar 会误切，显式钉死不依赖探针）；
- **重放 `apply_telemetry_pcie.sh`**（我们的 FRU/PCIe 本地覆写是唯一承载，见 `W775delta_UPSTREAM_0145_020.md` §4）。

### 阶段 4（并行，与阶段 1-3 无依赖）：上游跟进
- **PR #1877**（Monitor FRU）：rebase 到 `main`、标题加 `[GUI]`、填模板、`/reopen`（成本最低的一条）。
- **PR #1855**（bench）：等阶段 2/3 有新版数字后，用 `strata bench run` 标准口径重提，标题 `[Benchmark]`。
- **新 issue（可选，价值高）**：把 §2.4 的守卫不一致作为**独立 issue** 提（`#1732` 同型，且 0.2.1 恰好刚修过 gfx906 构建）；带 `[Engine]` 前缀与最小复现（`decode_defaults_arch_ok()` 在 gfx906 上的返回值）。

---

## 四、风险清单

| 风险 | 等级 | 处置 |
|---|---|---|
| 0.1.46.2 的 gfx906 只有"编译通过"，**无任何卡上验证** | **高** | 阶段 2 必须跑答案一致性 + 显存 + 长短 prompt 三项判据 |
| 裸 `--vision` 在 32 GB 卡上改走 GPU（+1,470 MiB） | **高** | 显式 `--vision cpu`，并写进 register |
| ROUTE_TAIL_SKIP 守卫与注释不一致（#1732 同型） | 中 | 阶段 2 记录 `route tail skip` 行；若 ON 则对照 `=0` 单臂确认是否改答案 |
| `generate.cpp` 从 0.1.42 起涨了 243 KB，`verify.cpp`/`prefill.cpp` 各涨 60 KB 级 | 中 | 只用"答案一致 + 速度不退化"两条硬判据，不做逐行审 |
| 上游把 tracker 清过场（1,300+ 项），我们的 PR 已关 | 低 | 走 4 步 reopen 配方 |
| 构建期抢 CPU 拖慢生产 | 低 | 低峰做或临时停生产 |

---

## 五、我建议的执行次序

1. **现在**：阶段 1 的试编脚本（在 166 上跑，先确认"能编"）；
2. **接着**：阶段 2 的一次窗口（A/B/C 三臂 + 三条判据）；
3. **通过后**：阶段 3 落生产（含 `--vision cpu` + `--ple-io direct` + 重放 telemetry patch）；
4. **随时可并行**：阶段 4 的 PR #1877 reopen。

---

## 六、落盘物

- 源码：`deploy/tmp/src_latest/`（0.1.46.2，4,518 文件）· 对照 `deploy/tmp/src142/`（0.1.42）· `src020/`（0.2.0-beta，**已作废**）
- 版本说明全本：`deploy/tmp/_rel_v0_2_1.md`(27KB) · `_rel_v0_2_0-beta.md` · `_rel_v0_1_45.md` · `_rel_v0_1_44*.md` · `_rel_v0_1_43*.md`
- 探针/差异脚本：`deploy/tmp/_diff142_latest.py` · `_src020_probe.py`

---

## 7 追加（2026-10-21 22:4x 三臂实测后，修正本方案的判断）

实测见 `deploy/W775delta_BASELINE_0146.md`。三条硬结论：

1. **版本间无可测差异**：3K prompt 362.5-387.5 tok/s、26K 477.8-482.7 tok/s，R(0.1.42)/N(0.1.46.2)/F 三臂同带 => **"升级能变快"被否**；升级价值只在修复/稳定性。
2. **融合（`ROUTE_TAIL_SKIP=0` + 显式 `--ple-io direct`）对 prompt 无收益**（+0.4% / -0.1%，噪声内），但**确实改答案**（26K 档输出 49 vs 66/29 tokens）。
3. **两处纠错/新发现**：
   - 本方案 §2.4 曾推"0.1.46.2 会自动关掉 ROUTE_TAIL_SKIP"---- **实测推翻**：两版都打 `STRATA_ROUTE_TAIL_SKIP=7 is ON (default)`（`all_experts_resident` 在我们配置下为 false）。
   - **新发现 `STRATA_ADAPT_OVERLAP_RESIDENT=1`**：0.1.46.2 启动行逐字 `adaptive overlap: off: not in the resident RAM mode unless STRATA_ADAPT_OVERLAP_RESIDENT=1`。这是**唯一有速度潜力、且正好针对 `--resident-experts`** 的新开关，应作为下一个单变量候选。
   - GPU 读图器抢 1.47 GB 的风险在我们自建镜像上**不成立**（无 `strata-vision-hip`，两版都 `strata-vision: on the CPU`）。

**因此 §5 的执行次序改为**：`STRATA_ADAPT_OVERLAP_RESIDENT=1` 单变量车 -> 再决定是否落 `--ple-io direct` 显式（纪律项）-> 升版只在需要稳定性修复时做（按 §3 的台账与回归）。
