## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **零改动、零重启**（源码/文档核实 + 方案重排）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 16** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。回滚件同上。

## 四、进度 + 队列

**191 条 / 已结 115 / 60.2%**；主线 **163 / 115**；死块池 **0/28**。
队列：**R87 → R86 → R91 → R95 → R94 → R89 → R46 → R49**（R88 已证伪，降级）。

---

## 五、C 的真相：`dequant` 相位不是反量化，是"专家权重聚拢"

源码 `prefill.cpp:5543 / 5588 / 7005` 的 `pt.mark(kPfDequant, ...)` 包住的是 **把专家权重从缓存槽位聚拢/重排进 MMQ group buffer**（`gather_gguf` / group slot 填充），FP16 路径才是真反量化。所以 2K 时它 3.9× 的每 token 成本，是**每专家固定一次的重排开销摊不薄**。

**现成的"免重排"开关**：`STRATA_MMQ_DIRECT=1`（直接原地读槽位）。

| 证据 | 内容 |
|---|---|
| `docs/DETAILS.md §1511` | 170/1,217 token 的 read-in **−24% / −18%**，greedy token 完全一致 |
| 前提 | 构建需 `-DSTRATA_MMQ_TAB=ON`；**我们 build-r32 只有 `STRATA_MMQ_KQUANTS/TQ/TQP`，没有 TAB** |
| 关键限制 | 同一份文档：**"多数专家从 RAM 流式读入时 within 1.5%"** —— 我们 VRAM 只有 21.79 GiB，正是这种情形 |

⇒ **C 暂不重编**：要为一个"多数专家流式"的配置付一次全量构建，却拿不到那 18~24%。

## 六、方案 V3.3：把你要求"必须做完"的移植项提到最前

R95 的归因（GEMM + 权重重排）恰好落在三个已 OPEN 的移植项上，它们比新造的预取想法更该先做：

| 序 | 项 | 与 R95 的对应 | 自带判据 |
|---|---|---|---|
| **1** | **R87 q8_1 激活复用** | 减重复量化（dequant 侧） | 先量"每请求量化总时间"，**<1% 就判否**；bit-exact；外证 +2.2~2.6% |
| **2** | **R86 Q5_1 down 布局重排** | 减 88.6% 专家字节的重排/行去别名 | `kq_bench` canonical vs repacked：单内核 <20% 判否、≥40% 才动生产 |
| **3** | **R91 dot8 接 MMQ** | 正对 gate/up 的 Q4_K 小批 GEMM | P4 精度门（KL ≤0.005 / argmax ≥99%）先决生死；上限仅 2.05% |
| 4 | R95-B 小专家 small-M 分流 | 天花板高，改路由/边界 | 2K gate/up 相位 −10~15% |
| 5 | R94 / R89 / R46 / R49 / R50 | 并行 | — |
| — | ~~R88 预取~~ | 主机缝隙仅 15 ms，**已证伪** | — |

## 七、R86 第一步卡在哪（已查清）

`kq_bench` 只在 `build-r28` 有编译产物，而那个构建 `mmq::built()=false`（运行只回一句 `MMQ/Q4_K not in this build`）；`build-r32`（生产树）**没有**这个可执行。⇒ 要拿 W944 那份 Q5_1 基线在新版本上的复测，需要**按 r32 的编译行重编一次 `kq_bench`**（约 2 分钟，不动生产）。

## 八、下一步

1. **按 r32 重编 `kq_bench`**（逐字抄 `build.ninja` 的 flags，含 `-DNDEBUG`），复测 Q5_1 down [2560,640] 的 1.53 ms / 5.47 TMAC/s；
2. 同时做 **R87 的第一步测量**（每请求量化总时间），拿实数决定做/不做；
3. 两者都不动生产配置，无需停机。
