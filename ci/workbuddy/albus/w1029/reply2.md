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
| 8 | 本轮改动 | 生产零改动、零重启；仓库 2 提交（`bc56628a` CI 真因+GitHub 门、`8476b78c` 四步文档）+ 1 空提交 `e4f0867d`；disk = build = running = `5e63174d…` 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 8476b78c · tag `mi50-0.2.11-r33-12` · 落后上游 0 / 领先 76 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 2 提交（+1 空提交验 run）。
**四、进度** 305 条 / 已结 221 / **72.5%**；队列 **R99**（S1 待修）→ R95（`P335`）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、你截图那一页我核过了，它只是「策略」，不是「fork 启用」

截图是 **Settings → Actions → General**，`Allow all actions and reusable workflows` 已选中——
这解释了为什么 `/actions/permissions` 一直报 `{enabled: true, allowed_actions: all}`。
但 `workflow_dispatch` 仍返回 **422 `Actions has been disabled for this repository`**：

> 这两句话可以同时为真。`/actions/permissions` 说的是**策略允许什么**，
> 422 说的是**这个 fork 的 workflows 有没有被启用**。它们是两个开关。

外部证据同形：apache/seatunnel 的维护者对**同一个 422**给过逐字答复——Settings 设 Allow all 是第 1 步，
然后必须去 **Actions 标签页**点横幅 `I understand my workflows, go ahead and enable them`，再**推一个新提交**，
GitHub **不回填**开关关闭期间推上去的 sha。

## 六、第 3 条我自己先验了：还是关的

我按「启用后要新推送」的做法推了一个空提交 **`e4f0867d`**（`git commit --allow-empty`）到 origin，
等 **180 s**：`GET /actions/runs` 里最新仍是 **#44 @ `372106ed` @ 2026-11-05T18:15:37Z**，`gh_gate.py` 返回 **6**。
⇒ 说明第 2 步（Actions 页的那次点击）还没生效。这一步 API 做不到，页面才有按钮。

**请你点这一处**：打开 `https://github.com/phoenixclyde/Strata/actions`
→ 顶部横幅 *"Workflows aren't being run on this forked repository"* → 绿色按钮
**"I understand my workflows, go ahead and enable them"**。
（顺手确认 Settings 那页的 `Save` 真按过——只选中不 Save 等于没改。）

点完告诉我一句，我这边一条命令验到底：`python3 ci/gh_gate.py --wait 300`。
要立刻看到结果，我可以再推一个空提交；不推也可以，我直接用 dispatch 起一次（那时会返回 204）。

## 七、你要的「GitHub 要修」有一半已经修完了：CI 从来不是因为禁用才红

`#42–#44` 的红与 Actions 开关**无关**，我把 job 日志原样拉下来了（`GET /actions/jobs/<id>/logs`，
要绕开带 `Authorization` 的 302）：

```
ROUND_GATE: FAIL (1)
  - selftest_pin.py: [BAD] baseline: both declarations agree   rc=2
```

`rc=2` = python 打不开文件。根因是 `ci/selftest_pin.py:13` 里写死的
`RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"`——我的工作仓路径，runner 上没有。
已改成 `__file__` 相对，缺失时在 `ci/selftest_pin.py:59` 直接 `SystemExit`。
**判据**：depth-1 干净 clone（无工作仓路径、无 tag，正是 runner 的样子）跑 `ci/round_gate.py --ci`
→ `ROUND_GATE: PASS`、`SELFTEST: 4/4`。也就是说：**开关一开，第一条 run 就是绿的**，不用再猜。

## 八、门已交回 GitHub，本地只做自检

- `ci/gh_gate.py`（`ci/gh_gate.py:96`）：要求该 sha 有 `completed = success` 的 `downstream-gate` run；
  exit 6 = 没 run / 进行中，7 = 失败并打 URL，8 = API 或无 token。
- `ci/deploy.sh:41`：第 0 步就是它 ⇒ **没有绿 run 不装**。所以本轮落生产是 0 / 0 / 0，是门不让，不是忘了。
- `.github/workflows/downstream-gate.yml:50`：checkout 加 `fetch-depth: 0` + `fetch-tags: true`
  （depth-1 没 tag，读 tag 的检查会无关地红，这是 CI 最常见的假红）。

## 九、顺带抓到第三次「只存在于我笔记本上」

`git ls-files deploy | wc -l` = **0**，可工作流开头写着 *See deploy/CI_CD_BLUEPRINT.md* ——
那份文件只有我笔记本上有。和 W1018（证据件没进仓）、W1025（报告两个副本）完全同族。
已把四步写进**受跟踪**的 `ci/README.md:90`，并把工作流那句引用改成 `ci/README.md`（`.github/workflows/downstream-gate.yml:8`）。

## 十、R99 本轮不动

`exp/lcpp-b12169` = `7fdd5d3c` 保留；S1 的 `tile_spec` 仍在 75-token prompt 上 hang（`exit -6`），
三个候选（bounds 末项 / `ntj` 与 grid z / 空 tile 覆盖）**均未验证**。CI 门没通之前不碰内核，否则出了偏差无法归因。

## 十一、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `MIRROR_CHECK` 全 PASS；
`GATE_RECEIPT` 对 `8476b78c` PASS（166 接收端）；`gh_gate.py` 对 `8476b78c` 返回 **6**（仍无 run）。
六件权威件双侧逐字节。新增 `P370`（fork 两处开关 + 不回填，`e4f0867d` 实测）、`P371`（`deploy/` 未跟踪）。
生产未动，现役性能仍是 prefill@2K **530.43 tok/s** / @8K **716.02 tok/s**（W1022 记录，本轮未复测）。
