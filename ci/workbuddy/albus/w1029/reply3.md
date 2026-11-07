**一、生产容器（10 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）——本轮未重建 |
| 2 | 运行中引擎 | `strata-0.1.57-001`，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-06T11:59:46Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.57-001`（现役）、`strata-0.1.57-002/003`（b12129 / S1 试版）、镜像 `0.2.10-101`、旧容器 `strata166-407-old`；`ci/rollback.sh --exe … --apply` |
| 8 | 本轮改动 | 生产零改动、零重启；仓库 2 提交（`a9677182`、`6501c28f`，均改 `ci/`）；GitHub 侧 3 次 run（#45/#46 红 → **#47 绿**）；disk = build = running = `5e63174d…` |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 6501c28f · tag `mi50-0.2.11-r33-14` · 落后上游 0 / 领先 78 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 2 提交（都在 `ci/`）。
**四、进度** 307 条 / 已结 223 / **72.6%**；队列 **R99**（S1 待修）→ R95（`P335`）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、新邮件是 run #45 的失败通知，同时确认：Actions 已经开了

收件箱最新一封 `[phoenixclyde/Strata] Run failed: Downstream gate - gfx906/mi50 (8476b78)`（13:45:36Z）。
我这边同一时刻的探针也变了：`POST …/dispatches` 从 **422 → 204**，说明你点的那次生效了，
**Actions 从此是活的**——接下来三次红不再是"没跑"，而是**跑了但判据不对**。

## 六、三次红，每次只往前走一步，病根是同一个

| run | 卡住的日志（逐字） | 被当成失败的是什么 | 修法 |
|---|---|---|---|
| #45 `8476b78c` | `[FAIL] container image  error: no such object: strata166-407` | runner 上有 docker、**没有我们的容器** | `release_check.py --offline`（`ci/release_check.py:58`）：容器/镜像 json/二进制/版本一致/树 hash 五行降为 **SKIP**，不再算失败 |
| #46 `a9677182` | `[FAIL] llama.cpp pin (release) (absent)` | `--offline` 跳过了 `BUILD-IMAGE.json`，而 release pin 那行**正是读它** | offline 时改读 `ci/docker/Dockerfile-*` 里的 `LLAMA_CPP_SHA`（`ci/release_check.py:131`）——烤进镜像的那份声明，runner 上也有 |
| #47 `6501c28f` | — | 自测 fixture 里没有那个 Dockerfile（**fixture 缺了被检查的文件，就不算 repo**） | fixture 补写 `Dockerfile-selftest`（`ci/selftest_pin.py:41`）⇒ **success** |

三行日志对应三件被误当"源码事实"的东西：**宿主状态、镜像产物、fixture 的形状**。

## 七、绿了：run #47，14 秒，6/6 步全绿

```
run 47  completed  success  6501c28f  2026-11-06T13:50:30Z
job Static gate (no GPU) success  started 13:50:33  done 13:50:47
  1 Set up job · 2 checkout@v7 · 3 setup-python@v7 · 4 Syntax of the 166 tooling
  5 Config-face checks · 6 Round gate (evidence, report lint, …)   ← 全部 success
```

`python3 ci/gh_gate.py` → **`GH_GATE: PASS 6501c28fecf2 run #47`**（rc=0）。
这是 `ci/deploy.sh:41` 的第 0 步**第一次被一条真实的 GitHub 绿 run 放行**——前三次都是 exit 6/7 拦下来的。

## 八、现在的判据链

| 层 | 谁跑 | 作用 | 能不能被绕过 |
|---|---|---|---|
| 判据 | **GitHub Actions**（`downstream-gate`），由 `ci/gh_gate.py:96` 按 sha 查询 | 干净 runner + 推送的树 + 无宿主依赖 | 不能：部署只认这条 run |
| 自检 | 本地 `ci/round_gate.py --ci` | 推送前 25 s 自查 | 可以（但没意义） |
| 第二双眼睛 | 166 的 `git push gate` 接收端回执 | 换台机器再跑一遍同一棵树 | 不能，但已降为提示 |

`ci/deploy.sh` 现在：**没有绿 run 不装**。本轮落生产 0/0/0 是因为没有要装的二进制，不是因为门被关掉了——
门现在是开的，`gh_gate` 刚 PASS。

## 九、举一反三：干净 clone 才是 runner 的样子

三次红我都在本机跑过 `round_gate --ci` 全绿，然后 GitHub 红——因为本机有容器、有 `/data`、有那些文件。
最后能收敛，靠的是把"runner 的样子"写成一个可执行的步骤（`ci/selftest_pin.py:67` 的 `--offline` 也是同一件事）：

```
git clone --depth 1 <repo> /tmp/x && cd /tmp/x && python3 ci/round_gate.py --ci
```

这条命令现在能一次跑通 `ROUND_GATE: PASS`。**以后任何 `ci/` 改动，先跑它，再推。**
一个判据只要依赖"我这台机器上有什么"，它就不是判据——这是本项目第四次交这个学费（W1018 证据件、W1025 全文匹配、W1028 的 `GIT_DIR`、今天的路径/容器/fixture）。

## 十、R99 仍未动

`exp/lcpp-b12169` = `7fdd5d3c` 保留；S1 的 `tile_spec` 仍在 75-token prompt 上 hang（`exit -6`），三个候选未验证。
CI 门现在通了，下一轮可以正经把它往前推一步：先在 host 侧 dump 一次 `bounds`，核对「末项是否等于 `total_rows`」再动 device 端。

## 十一、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `MIRROR_CHECK` 全 PASS；
`GH_GATE: PASS`（run #47）；`GATE_RECEIPT` 对 `6501c28f` PASS；六件权威件双侧逐字节。
新增 `P372`（三次红与 run #47 绿）、`P373`（部署门首次由真实 GitHub run 放行）。
生产未动，现役性能仍是 prefill@2K **530.43 tok/s** / @8K **716.02 tok/s**（W1022 记录，本轮未复测）。
