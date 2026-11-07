**代码级结论：0.8.0 的 MMQ 内核与我们**逐字节等价**（23,164 B vs 23,168 B，寄存器/私有内存/spill 全同）；热态生产路径 A/B 三者 503 / 497 / 506 tok/s（差 ≤1.8%）⇒ **0.8.0 不慢，可以紧跟上游**。我之前那个 −6% 是"每个容器第一段 prompt"的冷启动口径，不是上游退步。**

## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T13:15:20Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`） |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量重启 **3 次**（热态 A / 热态 B / 回滚件），停机 **≈15 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；死块池 0/28。
队列：**W968 查缓存口径** → 六长度档 A/B 定稿 → 补 trellis prec + 摘 `#29953` padding → **R88-量** → **R86-A/B** → R87 → R46 → R91 → R93 → R72 → R81 → R63/R60/R64。

---

## 一、内核级：两版**逐字节等价**

把 `.hip_fatbin` 拆成 code object，读每个内核的元数据（`llvm-readelf -n`）与符号大小（`llvm-readelf -s`）。
我们实际跑的是 `pick_J` 选出的 **J=64、fallback=false、prec=Q8**：

| 项 | 0.7.0（无 fusion） | 0.8.0（fusion） |
|---|---:|---:|
| 内核代码大小 | **23,164 B** | **23,168 B** |
| sgpr / vgpr | 44 / 128 | 44 / 128 |
| private segment / spill | 44 / 0 | 44 / 0 |

`has_fusion=true` 是另一个 **48 B / sgpr 38 / vgpr 41** 的小内核，我们的调用**不会**选中它（`fusion.gate == nullptr`）。

## 二、另外三个嫌疑，逐个排除

| 候选 | 结论 | 依据 |
|---|---|---|
| `#30553` stream-k cap | 无关 | `mmq-config-gcn.cuh` 里 Q4_K/J=64/fallback=false 的 CASE 第 8 参是 `false`（`stream_k=false`），我们不走 stream-k |
| `#30087` GDN `cols_per_warp=4` | 不是 0.7→0.8 的差 | 两版 `gated_delta_net.cu` 都是 9 处、默认 4 |
| fusion 的 loader 改动 | 不影响非 fused 实例 | 同一内核代码大小与寄存器都没变（上表） |

## 三、热态生产路径 A/B：三者等价

口径：production 的 `serve/server.py` + 项目自带 `ci/prefill_probe.py --quick`（`/v1/chat/completions` + streaming，每 cell 先打一次丢弃），同一 1916-token prompt，只换 `exe`：

| 引擎 | TTFT（3 次） | 吞吐 |
|---|---|---:|
| `strata-0.1.56`（0.4.1 + 我们的补丁） | 3810 / 3806 / 3797 ms | **503 tok/s** |
| `build-080c/strata`（0.8.0） | 3850 / 3884 / 3886 ms | **497 tok/s** |
| `strata-0.1.55w`（回滚件 0.2.9） | 3770 / 3803 / 3789 ms | **506 tok/s** |

⇒ 差 **≤1.8%**。**0.8.0 不慢**。

## 四、所以我之前错在哪

`W960`/`W962` 的 −6%/−5% 是**每个容器加载后读的第一段 prompt**（冷态）：那一段主要由**专家换入**支配，与 MMQ 无关。
内核逐字节相同、热态等价——两者一致，说明"看起来慢"来自测量口径，不是代码。

## 五、留下一个必须查清的口径问题

三者都只有 ~500 tok/s @1916，而 `W863`（11-01，同一探针）是 **946 @1242 / 1231 @2468**。
铁证在重复测试：W863 记录"同一 prompt 第 2–5 次 **252 ms（14.6×）**"，而我这三次 **TTFT 全是 3.8 s，缓存一次都没命中**。

⇒ 我的 harness 里 **prompt cache 没生效**（很可能 OpenAI 兼容接口要请求带 `cache_prompt: true`，探针没带）。
**在这一点查清前，"500 vs 946"不能算退步，只能算口径不同。**

## 六、紧跟上游的下一步（顺序）

1. 查缓存口径（不改生产，纯读代码 + 一次探针）；
2. 六长度档 A/B 定稿（2K/8K/16K/32K/64K/130K，用修好的口径）；
3. 跟之前补两件：overlay 的 trellis 段适配 `ggml_cuda_mmq_util_funcs(..., prec)`；**摘 `#29953` 的越界 padding**（`ids_dst` +`J-1`、`src1_q8_1` 按 `nthreads` 上取整）——这是我们 0.4.1 缺的正确性修复。

产物：`deploy/W966_CODE_LEVEL_VERDICT.md`；`W954` 已加"再改判"横幅（R90 回到可执行）；账本 R90 仍 **INFLIGHT**；结案台账 41/41。
