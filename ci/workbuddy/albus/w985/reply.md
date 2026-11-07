## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `49bf0c812fe5e53db4a00b5be97e3a13`；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T18:39:29Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **生产配置零改动**；只改账本（PROGRESS +2 行、R88 改靶；PARAM_REGISTER +2 行、P138 改判）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `e0b975d8` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 12** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

配置改动 **0**；重启 **0 次**；停机 **0**。回滚命令同上。**账本改动**：`PROGRESS.tsv` 备份 `.bak_w985` 后追加 P252/P253 两行并改写 R88 正文；`PARAM_REGISTER.tsv` 备份后新增 P254/P255、改判 P138。

## 四、进度 + 队列

**178 条 / 已结 104 / 58.4%**（补账前 176/102）；主线 **150 / 104**；死块池 **0/28**。
队列：**R88 → R86 → R87 → R46 → R91 → R93 → R72 → R81 → R79/R80 → R63/R60/R64**。

---

## 五、问题一：该入调优方案却没收的 R（4 条）

| # | 问题 | 证据 |
|---|---|---|
| Q1-1 | **R88 的账本正文还写着"异步分阶段拷贝"**，而今天的证据把靶子改成"首块 CPU/GPU 串行" | 303 tok 时 5.4 ms/token vs 稳态 1.28；`--prefill` 借用量 7.62→3.11 GiB 无影响、`pool-tasks`/`pcie-frac` 双向无效应 |
| Q1-2 | **今天两条负面结论没入账**（我上轮说"台账补两行"但没做） | `pool-tasks=6`、`pcie-frac 0.10/0.35` 在 PROGRESS 里 0 命中 |
| Q1-3 | **39 个 R 编号从未被任何审计件引用**（R20/21/29/33/34/36/39/40/45/46/49/50/52/55/56/57/59/61/62/64–83 中未被审者） | 账本 79 个 R，审计件只提 49 个 |
| Q1-4 | **R89 / R91 / R93 是 OPEN 且从未被审计**（立自 W952/W951/W954） | 审计覆盖到 W951 为止 |

⇒ 已修 Q1-1、Q1-2；Q1-3/Q1-4 列入下一轮审计（见 §八）。

## 六、问题二：该开却没开的开关（6 条，按成本排序）

| 候选 | 是什么 | 为什么该试 | 成本 |
|---|---|---|---|
| **P227 `pcie_frac_auto`** | PCIe 份额在头几个 decode 窗口自适应 | 源码 `generate.cpp:4644`：`pcie_frac_auto = … && !pf_old && (decode_defaults_arch_ok() \|\| pcie_auto_fork_arch_ok())`——**显式 `--pcie-frac` 会置 `pf_old` 把它关掉**；而我们刚证明 0.20 无效应，**去掉这个 flag 是零损失的解锁** | 1 次 cfg_apply |
| **P33 `pin=N`** | 请求级钉住会话 | 不传即无影响；只在会话缓存 **evictions>0** 时才有收益，而 `/metrics` 实测 evictions 会递增到 5+ | 零成本 |
| **P239 `STRATA_PF_MMVQ=1`** | 短轮 MMQ 专用路径 | 作者扫描：靶心是 **100–250 token** 的短 prompt（512+ 反而变慢），我们日常最短 2K ⇒ **只有短问才测得出** | 1 次 cfg_apply + 需造短 prompt |
| **P48 `--pcie-mode dma`** | DMA 版 PCIe 模式 | 未跑过，`docs/BATCHED_DMA.md` 有设计 | 1 次 |
| **P47 `--mtp-draft-vocab`** | 草稿词表文件 | 族内唯一真候选，未跑 | 1 次 |
| **P244 `STRATA_GR_V3=1`** | hyper-connection read 双流拆分 | 作者要求先微基准（≥10% 且 KL 可过）才值得停服 | 先 bench |

## 七、问题三：负面/测试残留（4 条 + 3 条假阳性）

**真残留（建议清）**：

| 项 | 登记状态 | 问题 |
|---|---|---|
| `STRATA_RESIDENT_HEADROOM_GIB=0.5` | **P65 DEFERRED** | 自身 verdict 写着"**惰性（配着但不生效），下次动 config 时一并清理**" ⇒ 空转 env，占着口径 |
| `STRATA_DECODE_TIMING=1` | **未登记**（本轮补 P255） | 每 4 个窗口打一行 stderr 的观测开关，生产常驻；代价未测 |
| `--pcie-frac 0.20` | P25 ADOPTED，但 P210 **UNRESOLVED** | 今日实测 0.10/0.35 与 0.20 无差别；且它置 `pf_old` 会**关掉 Q2 的 auto 候选** |
| `--vision` | P99 ADOPTED（W715 新启用） | 全库找不到使用证据或收益记录；占 VRAM 与一条代码路径 ⇒ **待确认是否真用**，不擅自删 |

**假阳性（机械匹配会误杀，已逐条核对）**：`--spec 4`、`--spec-min-p 0.70`、`--prefill auto:16384` 命中的 P249/P154/P131 虽标 REJECTED，但正文都是"**维持现值**"（P249：判否 spec 阶梯、维持 4；P154：判否 0.50、保持 0.70）。

## 八、未审计轮次：31 个（W952–W985）

审计件覆盖到 **W951**（AUDIT24）。之后 31 个轮次从未被审，机械扫描结果：

| 特征 | 轮次 |
|---|---|
| 只有 0–1 个文件（可能空转） | W959、W964、W965、W967、W968、W969(1)、W971 |
| 有负面/回滚结论但**未提及台账** | W963、W972、W973、W975、W976、W980、W981、W982、W983 |
| 文件多、结论多（优先审） | W952(26 件)、W954(9)、W972(12)、W970(10)、W975(10) |

## 九、下一步（都在门内）

1. **清死参**：cfg_apply 支持 `--unset-env` 后删 `STRATA_RESIDENT_HEADROOM_GIB`（预期无性能变化，n=10）；
2. **P227 解锁实验**：去掉 `--pcie-frac 0.20` + `STRATA_PCIE_FRAC_DEFAULT=auto`，看 auto 是否优于固定 0.20；
3. **补审 Q1-3/Q1-4**：39 个未审 R + R89/R91/R93，按 AUDIT24 的模板出一份 `AUDIT25_W952_W985.md`。
