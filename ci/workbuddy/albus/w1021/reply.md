**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2c22318c`（`2c22318c7d79…`）/ **`strata-gfx906:0.2.11-101`**（image `b48d2aff…`） |
| 2 | 运行中引擎 | **`strata-0.1.57-001`**，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，`--version` = **strata 0.1.57** |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T17:58:24Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free`（与 0.2.10 逐项相同） |
| 7 | 回滚件 | `strata-0.1.56-090`（`eea5ea37…`）、`strata-0.1.56-091`（`972fb977…`）、旧容器 `strata166-407-old`；`ci/rollback.sh --exe …` |
| 8 | 本轮改动 | 引擎 `0.1.56-090 → 0.1.57-001`；镜像 `0.2.10-101 → 0.2.11-101`；容器重建 2 次；config 改 1 次（exe）；disk = build = running 均为 `5e63174d…` |

**二、主线** gfx906/mi50 @ 9104cc00 · tag `mi50-0.2.11-r33-4` · **落后上游 0 / 领先上游 67**（线性，0 merge commit）· 工作树脏 0 行。
**三、本次落生产** 引擎 1 次（`-001`）；镜像 1 次（`0.2.11-101`）；重启 4 次（含容器重建 2 次）；停机合计约 4 分钟；回滚件备好未用；代码面 4 提交（`30e42ca8`/`53720031` API 移植、`9104cc00` release_check、`e21b1b01`→rebase 链）。
**四、进度** 279 条 / 已结 199 / **71.3%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、做了（每条都是刚复取的证据，不是"我记得做过"）

| # | 动作 | 复核到的东西 |
|---|---|---|
| 1 | 主线 rebase 到上游 v0.2.11 | `ci/release_check.py` 的 tag 字段；`HEAD=9104cc00`、`behind=0 ahead=67 merges=0`、`origin==local`、`dirty=0` |
| 2 | 所有活分支 rebase | `main=4533def2`(behind 0)、`exp/R90-080=53720031`(曾=主线 tip)；`pre-rebase/*`(7)+`backup/*`(2) 未动 |
| 3 | 树能编（干净） | `rm -f strata` 后 **154/154、`LINK_OK`**、`strata --version` = **0.1.57**、md5 `5e63174d` |
| 4 | 镜像换树 | `0.2.11-101`（`b48d2aff…`）；`/src/src/prefill/moe_mmq.cu` 里 `GGML_PREC_Q8` 计数 **0**（移植在）；`BUILD-IMAGE.json` = v0.2.11/66/engine 0.1.57/llama 3cf0325 |
| 5 | 引擎换版本 | `/data/bin/strata-0.1.57-001`，`--version` 打印 0.1.57，config exe 指向它 |
| 6 | 容器换镜像 | `2c22318c`、image `0.2.11-101`、restarts=0、`/health` ok（60 s） |
| 7 | 四指针一致 | `ci/release_check.py` → **`RELEASE_CHECK: PASS`**（tag / 镜像 json / 二进制 / 编译期宏，0.1.57） |
| 8 | 性能 | prefill@2K **531.56**（+3.5% vs 513.65）、@8K **715.98**（+4.6% vs 684.62）、decode 34.75（band 10.96，噪声内）、TTFT 3.94 s（−3.8%） |
| 9 | 技能 | `~/.workbuddy/skills/strata-release/SKILL.md`（七步 + API 移植 + 四指针 + 失败模式） |

## 六、没做，以及为什么（这一节是回答"哪些没做"）

| # | 没做 | 为什么 | 正规做法 |
|---|---|---|---|
| 1 | **质量门**（KL / top-1） | `quant_quality.py` 要独占 GPU 且本机无 Q8_0 金标（`P330`）；我先出速度数 | 换上游可能改比特 ⇒ 跑相对门（KL≤0.0139 / top-1≥99%，对现役配置），停机 4–6 分钟 |
| 2 | 16K/128K、多轮、MTP 接受率 | 只跑 2K/8K 单轮 | 六长度档 + `prefill_multiturn` + spec 接受率，一起进发布记录 |
| 3 | 可重现的镜像构建 | 完整 Dockerfile 的 `pip`（tuna 源）在 01:32 不可达，改分层复用 0.2.10-101 | pip 走离线 wheel/双源；钉住 base image digest；镜像必须能从零重建 |
| 4 | 清理 | 11 个 exited 容器（最早 5 天）、`-091`（新引擎旧标签）仍在 `/data/bin` | 只保留 N-1（镜像+二进制+config），其余删；错版本加 `.superseded` |
| 5 | 废止"单 TU 拼装" | `ci/build.sh`（`build.sh:47` 的 grep）仍是单 TU 工具，上一轮却用它当"编过了" | 发布只用全量构建；`build.sh` 标注"仅调试" |

## 七、为什么我会犯这些（根因）

1. **合并 ≠ 能编**：只看两个 TU 就宣布可编，全量一编 4 处 ggml API 断裂（`src/prefill/moe_mmq.cu:564` 的 `mul_mat_q_case` 去 prec、`mmq_get_config` 同理、`src/prefill/ggml_cuda_host.cu:143` 的 `new_pool_for_device` 改签名）。
2. **link 成功 ≠ 干净**（`ci/build.sh:47` 的单 TU 视角看不出）：旧 `.o` 被复用，产出一版混合二进制（md5 `a93ac842`），差点当成品——所以现在重编前 `rm -f strata`。
3. **版本有四个指针**：tag / `BUILD-IMAGE.json` / binary / **编译期 `-DSTRATA_VERSION`**（`CMakeLists.txt:23` 把 `PROJECT_VERSION` 编成宏）。我只动前两个，于是部署了"新引擎旧标签"的 `-091`——你那句"引擎还是 0.1.56？"就是这一处。
4. **镜像是隐形的第三份树**：容器只挂 `/data`、`/models`，`/src` 全来自镜像；我最初按"挂载"思路排计划。
5. **自验没有第二遍**：所有"验收"都是我自己跑的。

## 八、正规做法（已写进技能，并且第 1 条已落成脚本）

1. **四指针校验进脚本**：`ci/release_check.py`（本轮新增，`P349`，`release_check.py:96` 是三方比对那段），一次读 tag / 镜像 + `BUILD-IMAGE.json` / 二进制 `--version`+md5 / 构建缓存里的 `-DSTRATA_VERSION`，不一致即 FAIL。
2. 变更与验收分离：build → 部署 → 质量门 + 六长度档 → 才切生产，失败自动回滚。
3. 版本单一来源：`-DSTRATA_VERSION` 由构建时 `git describe` 注入，不再依赖 cmake 缓存。
4. 发布产物只来自**全量构建**；单 TU 构建仅调试。
5. 镜像可从零重建 + 记录 base digest；`BUILD-IMAGE.json` 由脚本生成。
6. 回滚常态化：N-1 镜像 / 二进制 / config，一条 `ci/rollback.sh`。
7. 每版跑同一套 bench（2K/8K/16K + decode + 多轮），结果进 `ci/state/cfg/`。

## 九、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`release_check` **PASS**；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债，`bundle.py:79` 那条证据跟踪本轮未变）；六件权威件双侧逐字节。新增：`§6.5 回写·W1020`（API 移植 + 镜像分层 + 0.1.56 事故）与 `§6.5 回写·W1021`（本节 review）、`P344`–`P349`。
