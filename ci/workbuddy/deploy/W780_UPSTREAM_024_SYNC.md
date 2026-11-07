# W780 上游 0.2.4.2（引擎 0.1.49.2）同步 + 遗留项汇总裁决

> 2026-10-25 01:2x-02:2x · 机主令：「与上游同步，更新到最新版源码，同步更新 llama.cpp 到最新版，去项目看最佳实践，并编译制作最新版镜像，并去项目查看过去几版完整 releasenote，**结合昨天遗留项和调优情况，进一步形成调优方案**。拉新镜像基线，落生产容器，更新 config。」
> 基线口径与 W777/W778 完全一致（`_bench166.py`，S 2,807 / M 21,821 / L 99,381 tok，唯一 nonce、`reused=0`）。

---

## 0 结论先行

1. **上游最新 tag = `v0.2.4.2`**（`dfa3f4025c`），`main` HEAD `7dd5cf18e6` 只多几个 release-notes/README commit。**引擎 `0.1.49.2`**（我们原 0.1.48.1）。
2. **但 0.2.4 全系列对 Qwen 引擎没有发布新二进制**：release note 两处原文 ——「every Qwen engine package stays as it was」「every engine package is still the 0.1.48 file, **byte for byte**」。0.2.4 的新东西是 **DeepSeek V4.1-Flash**（独立引擎包 `strata-dsv41` 0.1.49.x）+ 产品层。
3. **源码确实变了，但对我们无效**：`build023` 与 `build024` 目录级 diff 共 **92 项**，引擎核心 `src/` 只有 **10 个文件**，**全部在 `kernels/cpu/`**（`iq_avx2.cpp/.inl`、`iq_avx512.cpp`、`tq_*`、`native_expert.cpp`、`expert_layout.cpp`）。其中 `iq_avx2_rows.inl` 的实质改动是给模板加 `bool EX = false`，源码注释逐字：
   > `// EX (the DeepSeek CPU lane's rows)` … `// Without EX the order of the main engine's rows (**unchanged**)`
   => **Qwen 路径的数值与代码路径不变**，那批 CPU 加速（release note 说 decode +25% / prompt +26%）只走 `EX=true`，是 DeepSeek 的。
4. **llama.cpp pin 没变**：`3cf03257f219`（0.2.2 / 0.2.3 / 0.2.4 三代逐字相同）。上游最佳实践仍禁止替换（`AMD_HIP_PERFORMANCE.md`）。最新 master 依旧 5 参 vs 4 参不兼容（W777 §5）。
5. **基线实测三档等价**：S 408.7 / M 485.6 / L 465.2 vs 0.2.3 的 410.2 / 486.6 / 465.5 => **-0.37% / -0.21% / -0.06%**，全部低于 prompt 分辨率（1.2%）。**已落生产**（0.2.4 保留），旧容器存为 `strata166-407.bak023`。
6. **本轮最大的副产品不是升版，是发现我们的测量脚本有个会骗人的缺陷**（§4）：同一档第二次调用会因 nonce 重复而命中缓存（实测 `reused=99376`），如果不看 `reused` 就会把 1,340 ms 当成"预填 74,165 tok/s"。已修。

---

## 1 版本与产物

| 项 | 值 |
|---|---|
| 上游最新 tag / main HEAD | `v0.2.4.2`（`dfa3f4025c`）/ `7dd5cf18e6` |
| 源码版本行 | `project(strata VERSION 0.1.49.2 LANGUAGES CXX)` |
| 引擎 `--version` | **`strata 0.1.49.2`** |
| llama.cpp pin | `3cf03257f219`（未变） |
| 镜像 | `strata-gfx906:0.2.4`，6.96 GB，`28c9888b54cf` |
| 引擎二进制 | 34,771,568 B（0.1.48.1 是 34,235,568，**大 536 KB** = 多出的模板实例），md5 `81424da1dd2729e0…` |
| `STRATA_Q6K_EXPERTS` | OFF（与 0.2.3 一致） |
| 构建 | `[160/160]`，`BUILD_RC=0`，官方 gfx906 配方 |

---

## 2 源码 diff：92 项里只有 10 个碰引擎

| 区域 | 差异 | 对我们 |
|---|---|---|
| `src/` | 10 个文件，**全在 `kernels/cpu/`** + 新增 `src/dsv41/` | `EX` 模板参数化，**主引擎路径不变**；`src/dsv41` 是 DeepSeek |
| `include/` | 5 个（iq_avx2/avx512/native_expert/tq_cpu 头 + `strata/dsv41/`） | 同一批 |
| `serve/` | `frontend.py`、`server.py` 变了；**`telemetry.py`、`web/app.js` 逐字节未变** | 我们的遥测移植件**原样复用**（f045648a / a31f4544） |
| `src/core/dflash2.cpp` | **与 0.2.3 逐字节相同** | `STRATA_USE_HIP` 补丁**仍必须打**（否则 gfx906 编不过） |
| `third_party/` | llama.cpp pin 未变；新增 `project-maya`（DeepSeek，OFF） | 无影响 |
| 其余 | `tools/`、`tests/`、`docs/`、`apps/`、README | 非引擎 |

**结论**：`ninja strata` 的目标图里，除了 `EX` 那个模板参数，没有一处落在 Qwen 的调用路径上。三档实测印证。

---

## 3 基线（同 config、同口径）

| 档 | 0.2.3（0.1.48.1）prompt | 0.2.4（0.1.49.2）prompt | Δ | decode 0.2.3 -> 0.2.4 |
|---|---|---|---|---|
| S | 410.2 | **408.7** | -0.37% | 62.4 -> 60.8 |
| M | 486.6 | **485.6** | -0.21% | 61.3 -> 59.1 |
| L | 465.5 | **465.2** | **-0.06%** | 41.5 -> 35.7（该档仅 32 token，不作数） |

**L 档第一次只跑 2 runs 得 461.2（-0.92%），补测第 3 个有效样本后中位数回到 465.2。** 这个来回记在这里：**2 runs 的中位数在 1% 量级上不够用，至少 3 个有效样本。**

判读：三档全在 0.4% 内，低于分辨率 => **等价**。保留 0.2.4（版本与上游同步，长期维护成本更低）。

---

## 4 本轮真正值钱的发现：测量脚本会骗人

补测 L 档时出现：

```
[L] run1 ptok=99381 reused=0      prompt_ms=213639  prompt_tps=465.2
[L] run2 ptok=99381 reused=99376  prompt_ms=1340    prompt_tps=74164.9   <-- 假的
```

原因：`_bench166.py` 的 nonce 是 `w776%s%02d`（档位+序号），**同一档第二次调用脚本时序号从 01 重来 => 与上一次的 prompt 完全相同 => 服务端整段复用**。脚本自己按 `reused == 0` 过滤了（`n=2 reused0=1`），但如果谁只看最后一行的 `prompt_tps`，就会当真。

**修法**：nonce 加时间戳。**纪律**：报数前先看 `reused` 列，`reused != 0` 的样本一律作废——这条在 W776 就写过，仍然在这里差点被自己的脚本骗到一次。

---

## 5 遗留项汇总裁决（机主要的那份"进一步调优方案"）

### 5.1 已经彻底关掉的（不要再试）

| 项 | 裁决 | 出处 |
|---|---|---|
| `--pool-workers 21` | 显式 21 与默认 20 差 0.1%，且挤掉 aux 专用核 | W776-C1b |
| `--pool-tasks 42/126` | 483.4 / 484.2 vs 484.3，零差异 | W776 |
| `--ple-io ram` | -45% | P91 |
| `--prefill auto:16384` | -0.22% | P22 |
| `--ple-inflight 512` | -0.04% / -0.33% | W778 |
| `--host-core last` / `--aux-cpus auto` | +0.21%（噪声）/ **-0.64%** | W778 |
| `--prompt-cache-every 2048` | 完全无效（checkpoint 只能落 chunk 边界） | W778 |
| `--prefill 4096` | -12.6% 且复用仍 0 | W778 |
| gfx1151 默认表 7 项 env | 全在 ±0.5% 内 | W778 / P80 |
| routeK 的 LDS / BM / MMQ_NWARPS 手法 | 要么 Strata 已有、要么是空宏、要么结构不可比 | W779 |

### 5.2 还开着的（按 ROI 排序）

| 序 | 项 | 预期 | 代价/风险 | 为什么排这里 |
|---|---|---|---|---|
| **1** | **`--kv-grow`** | +1487 槽（**+15.2%** 槽位）=> 命中率 +2~4 pt，预填 +2~4% | 中高：必须拆掉 `--resident-experts`（源码 `generate.cpp:5154` 的 `!o.resident_cpu_experts` 门），同时动 RAM 与 VRAM 两个面 | 这是显存侧唯一还剩的实质空间（3.35 GiB），且 W720 当年算错了 16 倍（214 MiB 是单层），值得重做 |
| **2** | **`--spec-min-p --calibrate`** | decode +2~5% | 中：要独占 GPU 跑校准，约 10 min 窗口 | 上游提供了本机校准工具，我们一直用历史值 0.70 从未校准 |
| **3** | **8K 以下的复用**（#3493 / 会话缓存） | 多轮首字从 15 s 降到 <5 s | **高：属上游机制问题**（checkpoint 与 8192 chunk 边界绑死），本机只能上报，不能硬改 | 这是日常对话体感最大的一项（Open WebUI 多在 2-8K） |
| **4** | 合规基线（上游冻结 fixture / temp 1.0 / track=custom） | — | 低：25 min 窗口 | 有了它，我们的数字第一次能和社区比 |
| 5 | `--mtp-q4` / `--adapt-async` | 未知 | 低 | 与 kv-grow 争同一块空间，排在它后面 |

### 5.3 本轮新增的一条"看似可移植、实为不可"

routeK 的 `DEVLOG-moe-opt.md` 有个 SHIPPED 启发式：MoE GEMM 的 **BM 按专家行数分档**（`<=32 -> 1, <=512 -> 4, else 8`）。
查了 Strata：`native_moe.cu` 只有 229 行、是 **combine** kernel；真正的专家 GEMM 在 `s2_expert_grouped.cu`（`moe_hit_grouped_s2`），**不是模板化的 block-M 结构**，没有 `BM` / `BLOCK_M` 这个可调维度。
=> **结构不可比，不是"缺一个优化"。** 此条关闭。

---

## 6 落生产（已执行）

| 步骤 | 结果 |
|---|---|
| 镜像 | `strata-gfx906:0.2.4`（`BUILD_RC=0`，6.96 GB） |
| 回滚位 | 旧容器改名 **`strata166-407.bak023`**（0.2.3 / 0.1.48.1 完整保留）；镜像层还有 0.2.3 / 0.2.2b / 0.2.2 / 0.1.42 / 0.1.41 |
| 起新 | 同名、同参数、同 binds |
| 就绪 | **42 s** |
| 版本 | `strata 0.1.49.2` |
| `/metrics` | `slots 9901` · `vram_free 642` · `workers 20` · `kv k8v4` · `ctx 262144` · `arena 37495` |
| 遥测 | `gpu_name Radeon Instinct MI50 32GB` · `pcie gen3 / width16 / 4/4` |
| config | 与 register **无差异**（`gen_config --live` 空 diff） |
| 固化 | `verify_config` **PASS=29 FAIL=0** |

---

## 7 一句话

**这次升版编了、测了、落了，但收益是零——因为 0.2.4 的引擎改动全在 DeepSeek 那条路上，Qwen 的路径一行没动；真正的收获是发现我们的测量脚本会因为 nonce 重复而虚报 74,000 tok/s。下一步该做的不是再升版，是把 `--kv-grow` 那 15% 的槽位拿回来。**
