## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T10:28:52Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；实验分支 `exp/R90-080` 提交 `999b9121`（未合） |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。
实验分支 `exp/R90-080`：6 文件 +59/−35，**未合**。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量停服、重启 **4 次**（每次 ≈4.5 分钟，脚本自动恢复），累计停机 **≈18 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R90-S4 第 2 轮**（同二进制重复跑对照 → 定位分叉段 → 端到端 A/B）→ R88-量 → R86-A/B → R87 → R88-实现 → R46 → R91 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′

---

## 结论：0.8.0 能跑，但**不逐位**（64 token 里前 7 个相同）

| 臂 | 二进制 | 输出 | prefill |
|---|---|---|---|
| A | `strata-0.1.56`（0.4.1 生产件） | 64 token，RC=0 | 2047 tok / 3384.5 ms = **604.8 tok/s** |
| B | `build-080c/strata`（0.8.0） | 64 token，RC=0 | 2047 tok / 3601.3 ms = **568.4 tok/s** |

前 7 个逐字相同（`248045 271 248045 487 198 262 328`），第 8 个 A=`33413` / B=`1666`。速度差 −6.0% **不是判据**（单次 + 合成 prompt，与生产 800 tok/s 口径不同）。

## 中途修掉一个会让 0.8.0 直接崩的 bug

第一次跑 B 臂：`J_best=412` → `GGML_ABORT`（`mmq.cuh:1594`）。根因是 0.8.0 把 `mmq_args` 末尾的 `int64_t ncols_opt` 换成了 **`int J_best`**，而我们是**位置式初始化**，最后两个 `p.max_rows` 里第二个就落进了 `J_best`。上游算这个值的 `ggml_cuda_mmq_get_J_best` 在 0.8.0 里是 `mmq.cu` 的 **static**（我们调不到），于是照它的规则补了 `pick_J()` 12 行。

这条正好印证 `W955` 判据②：**"编过"不等于"等价"，甚至不等于"能跑"**。

## 方法上还纠了一处

原打算比 logits，但 `--dump-logits` 在 native pack 上**恒 0 字节**——源码注释写明「to a native pack never reaches the per-token dump site」，日志却仍打印 `logits dumped`。改用引擎自己打印的 `output : <token ids>`，也就是本项目"比 argmax 序列"的原意。

## 但"前缀 7"现在还不能当结论

三种可能尚未区分：① 上游算法变了（`mmq.cuh` 585 行、fatbin +10.9%）；② 我们的适配有 bug（`GGML_PREC_Q8`/`pick_J`/还有字段错位）；③ **引擎 run 间本身不确定**（`W899 §7.11` 记过）。

第 3 条最要命：若同二进制两次跑也不一致，"前缀 7"就没有证据力。**下一轮第一件事是打这个对照**，而不是继续调 0.8.0：

1. A 跑两次、B 跑两次（各 64 token）→ 各自是否稳定；
2. 若稳定：用 `--max-new 1/8/9/10` 逐点追加，定位分叉在 prefill 还是 decode；
3. 若 prefill 就分叉：关 `STRATA_MMQ_KQ=1` 复跑，差异在我们就不是上游；
4. 端到端六长度档 A/B（真实文本，`|Δ| ≥ 2×CV`）。

## 判据建议改一条

"argmax 序列相同"适合同版本内做优化；**跨 4 个 minor 的基线升级**要求逐位相同 = 要求升级不改数值。建议升级类改用 **`KL ≤ 0.005 且 top-1 ≥ 99%`，或 64 token 前缀 ≥ 48（75%）**，同版本优化仍守逐位。

产物：`deploy/W957_R90_S4_NOT_BITEXACT.md`；分支 `exp/R90-080`（`999b9121`，未合）；账本 R90 仍 **INFLIGHT**；结案台账 37/37。
