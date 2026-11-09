# W1057 回执：R74 W4A4 精度门过门（KL 0.0023 / top-1 100%）——R91 dot8 工程放行 + 测量陷阱复盘

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）· restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件（探针 `strata-0.1.57-a4probe` md5 `e4c4669a59f19b7ca66be1832db27424` **生产未装**，只在窗口臂里跑过） |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（trap 还原后复测）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A` `STRATA_HC_DOWN_DP4A` `STRATA_HC_DOWN_DP4A_MAX_T` `STRATA_GFX906_ATTN_LDS_PAD`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T09:39:51Z`（末次 trap 还原的冷启动） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 884 MiB（生产态）；expert cache 8301 槽 / 24,807 MiB；borrows：metrics 未暴露该键（W1055 读数 2609 槽 / 7.62 GiB；本轮生产未动） |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`（`a85743d7…`）；窗口备份 `tmp/w1057/cfg_a4_pre.bak`（= `8d234fa3…`，trap 还原源）；rollback = `cp` 回备份 json 并冷重启（≈45 s，本轮 trap 已执行 2 次均绿） |
| 8 | 本轮改动 | 换件 0 / config 改 0（窗口臂改过、**trap 已还原并复测 md5 一致**）/ 装机 0 / 回滚 0；**重启 10 次 / 停机 ≈ 480 s**（4 臂窗口 ×2 轮：每轮 4 臂 + 1 还原，各 stop→health ≈ 47 s）；disk=build=running 三方未动 |
| 9 | ROCm（容器内） | `.info/version` **10.1.0** · HIP runtime **7.16.26323-0000000** · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | **b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`** + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc`（镜像未换 ⇒ pin 未变） |

**二、主线** — `gfx906/mi50` @ e181bda5 本轮未动，**领先 0 / 落后 0**，脏 0 行；生产树 `pr/k10` 头 **`bd47cf05d`**（W1056 提交）→ 本轮新增 W1057 provenance 提交（见 §4）。新证据件：`albus/w1057/`（`a4sim_patch.py`、`build_a4probe.sh`/`build_a4probe.log`、`window_a4.sh`/`window_run.log`/`window_run1.log`、`compare_a4.py`）。

**三、本次落生产** — 换件 0 / 装机 0 / **重启 10 次 / 停机 ≈ 480 s** / 回滚 0。重启全部来自 R74 的 4 臂数值窗口（2 轮 × 5 次 stop/start），窗口臂用探针二进制 + 临时 env，**trap 还原 = cp cfg + 冷重启**（W1051 教训固化），复测 config md5 `8d234fa3…` 与引擎 md5 `05330748…` 均回到生产态。

**四、进度** — **532 条 / 已结 445 / 83.6%**（+2 条 `P583`/`P584`，`R74` 过门转 DONE）。队列（代码+前置优先）：**R91（P1 起步；P4 复核项=max KL 0.0067）→ R101 → R85/R46 > R64 > R60 → R89 → R95 → R86 →（治理）R80 → R79 → R81**（`W832 §0.1`）。

## 1. R74 过门：int4 激活量化的代价在均值口径下只有 KL 0.0023（P583）

R91 的前置门（`W832 §6.2 R74`）判据：KL ≤ 0.005、top-1 ≥ 99%、分辨率 0.0032。测量用 QDQ 仿真探针（`albus/w1057/a4sim_patch.py`）：`quantize_mmq_q8_1` 入口加 env 门控 `STRATA_A4_SIM=1`——激活按 **scale=amax/7、codes clamp [-8,7]** 量化成 int4 语义后存进 Q8_1 的 int8 容器（sum=d·Σq 同步改），**MMQ 计算路径零改动**，GEMM 输出携带的就是 W4A4 激活量化误差；`a4=0` 路径逐式保留原数学（实测逐位惰性）。探针二进制 `strata-0.1.57-a4probe`（`ggml-tq-overlay/quantize.cu` 补丁 + 03509d1b 源基，ninja 增量 BLD=0 FAILED=0，构建后 overlay md5 还原复核）。

4 臂窗口（同批 6 prompt × 248,320 维全词表 first-logits，`compare_a4.py` 对拍）：

| 对 | 语义 | KL mean | KL max | top-1 | max\|Δlogit\| |
|---|---|---|---|---|---|
| A1a vs A1b | 跨进程地板（hc4b ×2 进程） | **0.000000** | 0.000000 | 6/6 | 0.00 |
| A1a vs A2 | 补丁惰性（a4probe 无 env vs hc4b） | **0.000000** | 0.000000 | 6/6 | 0.00 |
| **A1a vs B** | **int4 仿真（STRATA_A4_SIM=1）** | **0.002295** | **0.006704**（req3） | **6/6 = 100%** | 3.73 |

- **判决（均值口径）：PASS**——KL mean 0.002295 ≤ 0.005、top-1 100% ≥ 99% ⇒ **dot8 工程（R91）放行**。真实分布预算（R116 族）与端到端 logits 一致：int4 激活误差是小量。
- **max 口径记档**：req3 KL 0.006704 超线 1.34×（1/6 点）——不判死但**写进 R91 P4 的复核项**（真 dot8 落地后用同法复测 max 口径；两口径都过才装机）。
- 分辨率注：本套内核确定性（同二进制跨进程逐位相同，地板 0.000000），比 W913 记的 0.0032 跨进程噪声底更紧 ⇒ 本次差异全部可分辨，0.002295 不是噪声。

## 2. 测量陷阱复盘：run-1 的「全臂逐位相同」是假阴性（P584）

run-1 用生产配置（`STRATA_PREFILL_CPU_SHARE=auto`）跑同样 4 臂，**24 个 dump 逐对逐位相同**（md5 矩阵实证）——包括 B 臂。机制：小 prompt 的 GEMM 走 host 侧 CPU-share 路径，**CUDA 激活量化器整个被旁路**，`STRATA_A4_SIM` 从未生效。若不查 md5 直接信 compare 输出，门会以「KL=0 全过」放行一个从未跑过的候选——**假阴性比假阳性更危险**（P500 族教训的新变体）。

- 修法就是技能偏差集里的 `STRATA_PREFILL_CPU_SHARE=0`（`strata-quant-quality-gate §5` 早已写明「它测的是 GPU MMQ 内核的 prefill 数值，不含主机侧 CPU share」）——run-1 没照抄。**教训：技能的偏差集是判据的一部分，不是可选备注**（该技能验证表已补 W1057 实证行）。
- 举一反三：本树所有数值 A/B（R91 P4、R60 的 R59 门、R101 的 KL 门）凡涉 GEMM 数值，必须强制 GPU 路径 + dump md5 矩阵自证臂间已分化；「臂间逐位相同」必须先排除路径旁路，再当结论用。
- 残余登记：req0（64 tok 首请求）在 B 臂无效应（md5 同 A）而同长度 req5 有效应 ⇒ 启动后首请求走特殊路径（疑似 warmup/profile 保存），列为已知空洞；门判据用 5/6 有效点。

## 3. 下一步（新队列第一）

1. **R91 dot8 六阶段**：P1 量化器（float→int4 每 32 值 scale + Σa 进 block 头）起；**P2 前补 dot8 同访问面微基准**（W1056 教训：指令密度≠时间收益）；P4 KL 门带 max 口径复核（本门的 0.0067 记档）。
2. **R101**：#31247 cherry-pick + `quantize.cu` DS4 分支同步。

## 4. CI/CD 与门

provenance 提交（`ci/w1047-coverage`，本轮证据件 + 账本 + 方案镜像）+ Downstream gate + GPU gate 双绿（**本轮按 W1056 新坑流程：push 后先同步 runner 镜像再等 GPU gate**），run id 登记 `CI_RUNS.tsv`。收尾 `round_close.py` HARD 门全绿后交件。
