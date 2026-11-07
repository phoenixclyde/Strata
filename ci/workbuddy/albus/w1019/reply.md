**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（**镜像内 `/src` 仍是 v0.2.10 树**） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0）——本轮未重编 |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:45:25Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮**未动用**） |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running 里 disk=running=`eea5ea37…` 一致，**build 侧 `build-r28/strata` 已被一次失败链接删掉**（见第八节）；镜像未重建 |

**二、主线** gfx906/mi50 @ 22abb0c0 · tag `mi50-0.2.11-r33-2` · **落后上游 0 / 领先上游 64**（线性，0 merge commit）· 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；回滚件未用；代码面 0 提交（本轮全是 git 与构建面的操作，未改代码）。
**四、进度** 273 条 / 已结 193 / **70.7%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、rebase 做了——上一轮我做的是 merge，不是 rebase

`e21b1b01` 是 `--no-ff` 合并，历史里留了一个 merge commit。本轮改成 rebase：

```
git rebase upstream/main      # 64 个提交重放，0 冲突
behind=0  ahead=64  merges=0  # 线性
push --force-with-lease       # 85297483 → 22abb0c0
tag mi50-0.2.11-r33-2 ；备份 backup/pre-rebase-w1019 + tag pre-rebase-w1019
```

## 六、所有分支 rebase：只 rebase 活分支，存档不动

| 分支 | 之前 | 之后 | 说明 |
|---|---|---|---|
| `gfx906/mi50` | ahead 63 / behind 208 | **ahead 64 / behind 0** | 64 提交重放，线性 |
| `main` | ahead 3 / behind **916** | **ahead 3 / behind 0** | 已 force-push |
| `exp/R90-080`（独立 worktree） | ahead 41 / behind 208 | **ahead 0 / behind 0** | 末条 `R90: print the J` 早已在主线（`c39e85ea`），重放时被判已应用；41 条旧提交留 `backup/pre-rebase-expR90` |
| `pre-rebase/*`（7 条）、`backup/*`（2 条） | — | **不动** | 名字即用途：存档。rebase 存档等于毁掉存档 |

顺带一条判据：`exp/R90-080` 第一次 rebase 到**裸上游**后 pre-push 被拒——那个分支上没有 `ci/round_gate.py`（门只在主线）。**实验分支应 rebase 到主线**（主线 behind 0，等价上游但带门）。

## 七、镜像和容器确实没跟，机制第一次查清

- 镜像 `strata-gfx906:0.2.10-101` 里 **`/src` 是 v0.2.10 的树**（`serve/server.py` md5 `ecf3cfc5…`；上游这 208 提交里改了它 16 次）；
- 生产容器只挂 **`/data`** 与 **`/models`**，**不挂 repo** ⇒ 运行中的 HTTP 层与 `/src/data/*` 全部来自镜像；
- **引擎二进制不在镜像里**（`Dockerfile-0.2.10` 逐字："引擎二进制不放进镜像（/data 是 bind，引擎走 /data/bin 的版本文件 + ci 账本）"）⇒ 跟上游是**两条腿**：镜像重做 + 引擎重编后走 `ci/deploy.sh`；
- `BUILD-IMAGE.json` 是镜像的指纹指针（`source: rebase onto upstream v0.2.10 (ffa80d73)`、`commits_on_top: 37`、`engine 0.1.56`）；`data/expert-profile.bin` 三处同 md5 `ff1bc654…`，重建镜像不会动它。

## 八、全量重编试了一次：卡在 ggml 参考树，并且删掉了构建产物

154 个 TU、8 并行（**331 s** 跑完）：**150 通过、4 失败（2.6%）**，链接随之失败（`mul_mat_q_case<(ggml_type)7/21/23>`、`ggml_compute_forward_mul_mat_tiled` 未定义）。真实错因是第一条：

```
clang++: error: no such file or directory: '/llama.cpp/ggml/src/ggml-cpu/iqp.cpp'
```

`build-r28` 的 `STRATA_GGML_DIR=/llama.cpp`（`src/prefill/prefill.cpp:418` 里同类 env 的读法可作参照），而本机三个 ref（`b10700`/`b12099`/`b12110`）**都没有** `ggml-cpu/iqp.cpp` ⇒ **v0.2.11 需要比 b12110 更新的 ggml**。运行时镜像里也没有 `/llama.cpp`（`NO_LLAMA_CPP`），`docker images` 里没有构建用镜像。

**副作用（记账）**：ninja 的链接行先 `cmake -E rm -f strata`，链接失败 ⇒ **`build-r28/strata` 现在不存在**。生产不受影响（`/data/bin/strata-0.1.56-090`，md5 `eea5ea37…` 未变），但在补齐 ggml 前**不能 deploy**——`deploy.sh` 读 `$BUILD/strata`，文件缺失会直接报错，不会装错东西。

**五步代价（`P343`，未做；`ci/build.sh:47` 的单 TU 流程在这里不够用）**：① 取与 v0.2.11 配套的 llama.cpp（含 `ggml-cpu/iqp.cpp`）挂到 `/llama.cpp`；② 全量重编（上一轮 150/154 的流程，8 并行实测 **5.5 分钟**、**331 秒**）；③ `ci/deploy.sh`（gate → tag → identity → `cp .new` → `mv` → restart → verify）；④ 新镜像 `0.2.11-101` + 新 `BUILD-IMAGE.json`；⑤ 引擎与镜像各跑一遍 A/B（`cfg_apply` 与 `quant_quality` 相对门）才允许进生产。

## 九、举一反三：版本在三个地方分别写，必须一起动

`tag`（代码）、`BUILD-IMAGE.json`（镜像内的树）、`/data/bin`（引擎二进制 + ci 账本）——**三处各自独立**，所以「主线跟上游」不等于「生产跟上游」。这轮把第一处做到了（`mi50-0.2.11-r33-2`），第二、三处各有前置（ggml 源 / 全量重编），所以它们现在明确地"没跟"，而不是含糊地"应该跟了"。

## 十、门与同步

`plan_lint` A–F PASS（`tools/report_lint.py:25` 那条 `mi50-<版本>` 本轮由新 tag 满足，没有放宽正则）；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py:139`（证据须 `git ls-files` 认得，见 `bundle.py:79`）全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1019`、`P340`（rebase 取代 merge）、`P341`（所有活分支 rebase，存档不动）、`P342`（镜像不跟的机制）、`P343`（全量重编卡 ggml + 构建产物丢失），`§0.1` 主线行改写为「树 rebase 到 v0.2.11 / 二进制与镜像未跟」。
