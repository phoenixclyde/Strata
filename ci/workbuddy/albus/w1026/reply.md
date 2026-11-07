**一、生产容器（10 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`） |
| 2 | 运行中引擎 | `strata-0.1.57-001`，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T18:46:29Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.57-001`（现役）、`strata-0.1.57-002`（b12129 试版）、镜像 `0.2.10-101`；`ci/rollback.sh --exe … --apply` |
| 8 | 本轮改动 | 生产零改动、零重启；只改 `deploy/`（方案 + 账本）；disk = build = running 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 360cbd4c · tag `mi50-0.2.11-r33-9` · 落后上游 0 / 领先 72 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 0 提交（只改 `deploy/`）。
**四、进度** 295 条 / 已结 211 / **71.5%**；队列 **R99（llama.cpp 最新，四阶段）→ R95**（`P335`）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、最优方案：R99，四阶段，每阶段只动一个变量

直接换 b12169 不行，理由是**可归因性**：b12129 实测 −4.0/−4.6%，b12169 相对它多 40 个提交、其中只有 #31047 碰 MMQ，而 #31047 要重写我们的分派层。一次换全树，会把「spec 布局写错」与「上游变快/变慢」压成一次无法分解的测量 —— 而 spec 写错**不报错、只是结果错**（kernel 直接解引用 `tile_spec`，无空指针分支），这是本项目最贵的一类 bug。

方案已落 `deploy/W832_OPT_PLAN_V2.md:2055`（§6.6），队列进 §0.1（`:28`），账本行 `R99`（`PROGRESS.tsv:271`，count=4 / done=0）。

| 阶段 | 内容 | 硬判据 | 失败处置 |
|---|---|---|---|
| **S0** | 同机复测 b11062（三档 bench + 48-token 贪心指纹） | 与 W1022/W1023 记录差 ≤1% | 差 >1% 先查环境，不进 S1 |
| **S1** | 树 = `ref/llama_b12129` + patch `69ee2ecc`；写 `bounds → tile_spec`（device kernel，参照 `mmid.cu:120` 起的 seam 对齐），改 `src/prefill/moe_mmq.cu:505` 的 `mmq_args` 构造与 `:504` 的 `pick_J`（`ntj` 语义） | **门1**：968-token 英文 prompt 的 48-token 贪心输出与 b11062 **逐字节一致**；**门2**：2K/8K 至少一档 **≥ +2×CV** | 门1 不过 = spec 错，禁止进 S2；门2 ≤0 ⇒ **R99 关闭** |
| **S2** | 完整 `b12169` 树（镜像 + `-C -` 续传，或只补 39 提交 diff） | 与 S1 差 ≤1%，指纹仍逐字节一致 | 差 >1% ⇒ 二分定位其余提交 |
| **S3** | 六档 bench + decode + TTFT + 多轮；质量相对门 | 任一档超 2×CV 即回滚；KL ≤0.0139 / top-1 ≥99% | 回滚 001，R99 记 DONE_NEG |
| **S4** | 改 `third_party/ggml/VERSION.txt`（**fork 覆盖**，commit 写明上游声明 b11062）、Dockerfile 的 `LLAMA_CPP_SHA/BUILD/TREE` 与去掉 `iqp.cpp` 的 `test -f`、重建镜像与容器（memlock + 18 键 diff 0）、`ci/release_check.py` 10/10 | 五处 pin 一致 + `RELEASE_CHECK: PASS` | 不一致即发布失败 |

## 六、为什么这四步的收益值得投

2K 的 prefill 相位里，MMQ 相关是 gemm gate/up **816 ms** + gemm down **510 ms**，占 GPU **3191 ms** 的 **41.6%**。
若 MMQ 快 20%，整条 prefill 约 **−8.3%**（算术，不是实测）。而上游 PR 自报 MI50 **1.23×** 是 Q4_0 + mb64；
我们走 **Q4_K/Q5_K**，适用性只能实测 —— 所以 S1 的门2 就是这道题的答案，代价 2–3 h。

**成本**：S1 2–3 h、S2 ~1 h、S3 ~2 h（含一次 4–6 min 停机的质量门）、S4 ~1 h；编译 5–6 min/次。
**最坏情况**：S1 门2 ≤0，2–3 h 后关闭，生产零改动、账本留一条死因。

## 七、这条 R 的退出条件写死在方案里

不是"做不完就算了"，而是**三种明确的死法**：①门1 不过（spec 布局错，且不允许"看起来对"就上）；
②门2 ≤0（gfx906 不适用 #31047，整个 R 关闭）；③S3 质量门不过（数值变了，回滚并记 DONE_NEG）。
任何一条触发，R99 都要在账本里写清"死在哪个门、数字多少"，不许含糊成"效果不好"。

## 八、门与同步

`plan_lint` A–F PASS（`R99` 在方案与账本双侧可 grep）；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；
`REPORT_LINT: PASS (14 fields)`；`REPORT_DEPTH: PASS`；`ROUND_CLOSE: PASS`。六件权威件双侧逐字节。
本轮新增：§6.6「R99 四阶段」、§0.1 队列行前置 R99、`PROGRESS.tsv:271`（R99，OPEN，count 4）。
