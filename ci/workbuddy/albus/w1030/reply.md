**一、生产容器（10 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）——本轮未重建 |
| 2 | 运行中引擎 | `strata-0.1.57-001`（**实验后已回滚**），md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`（逐字节回退）；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-06T13:57:58Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | **本轮动用两次** `ci/rollback.sh --exe strata-0.1.57-001 --apply`；试版 `strata-0.1.57-003`（S1）留在 `/data/bin` |
| 8 | 本轮改动 | 引擎换 2 次（003）+ 回滚 2 次；镜像/容器未改；**disk = build = running = `5e63174d…` 三方一致**；代码面 0 提交 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 6501c28f · tag `mi50-0.2.11-r33-14` · 落后上游 0 / 领先 78 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 2 次（S1 装上 → 回滚，共两轮）；**重启 2 次**；停机合计约 **4 分钟**；回滚件动用 2 次；代码面 0 提交。
**四、进度** 309 条 / 已结 229 / **74.1%**；队列 **R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50**（R99 已关闭）。

---

## 五、先把上一轮的旧结论推翻：那个「hang」根本不复现

W1027 我记的是「S1 在 75-token prompt 上 hang，watchdog `exit -6`」。今天用**同一个二进制**
`strata-0.1.57-003` 重新装上机，三个探针全部正常：

| prompt | tokens | 耗时 | 结果 |
|---|---:|---:|---|
| 8 词 | 67 | **1.51 s** | OK |
| 75 词 | 154 | **1.79 s** | OK |
| 400 词 | 555 | **2.50 s** | OK |

`/health` ok、`restarts=0`。⇒ 上次那个 hang 是**刚启动后首个请求**撞上的忙等，不是代码缺陷。
这条更正写进 `P375`——**判决建立在一次不可复现的现象上，本身就是错的**。

## 六、真正的缺陷是「能跑但算错」，比 hang 严重

数值门（48-token 贪心指纹，与 b11062 基线逐字节比；自测 fixture 见 `ci/selftest_pin.py:41`）**三例全不同**：

```
short  same=False len 118/122   first diff at 118
en2k   same=False len 224/224   first diff at 59
       old "…lyze. User provided repeated sentence: "The quick brown fox…"
       new "…lyze. User provided many repetitions of pangram: "The quick…"
zh2k   same=False len   7/5     first diff at 5
```

en2k 长度一样、**第 59 字符就换了说法**（`repeated sentence` → `many repetitions of pangram`）——
这是 **prefill 算术变了**，不是采样噪声、不是 48-token 边界。`tile_spec` 是分派数据（哪个 tile 归哪个专家），
写错不报错、只把列算到别人身上：**这正是我在 W1024 写"这是本项目最贵的一类 bug"的那类**，今天它发生了。

## 七、速度门也没过：2K 直接 503

`cfg_apply --record-only --n 6 --lengths 2000,8000` 在 **2K 就 HTTP 503**；此前 968-token prompt 用了 **5.92 s**
（含 48 token 生成），远慢于现役的 530.43 tok/s / 716.02 tok/s（2K/8K，W1022 记录）。
也就是说：S1 既没有"更快"，也承受不住基准的**重复相同请求**。

## 八、R99 关闭：按我自己写的死法关闭

`deploy/W832_OPT_PLAN_V2.md:2055`（§6.6）里写死的三条死法，第一条就是「门1 数值不过 = spec 语义错，禁止进 S2」，还有"两轮修不好即关闭"。
今天是第二轮（W1027 一次、W1030 一次）⇒ **R99 → DONE_NEG**（`P374`），账本写清死在哪：**算错 + 基准下 503**，不是"效果不好"。

保留物一个不动：`exp/lcpp-b12169` = `7fdd5d3c`、二进制 `strata-0.1.57-003`、构建目录 `build-lcpp`。
将来谁要把 spec 语义与上游对齐，从这里起步；`ci/deploy.sh:41` 的 GitHub 门（查 run 的是 `ci/gh_gate.py:96`）对这种实验照样管用——
它今天放行的正是 `6501c28f` 那条绿 run。

## 九、举一反三：三次教训合成一句

- **失败形态不止一种**：hang 看得见，算错看不见；只盯"崩没崩"会把最贵的 bug 放进去。
- **"能跑"≠"算对"**：探针 1.5 s 返回、日志好看，数值仍然错——所以门1 必须是**逐字节**，不能是"通不通"。
- **基准要包含真实负载**：单次请求 OK，`cfg_apply` 的重复请求直接 503；只跑一次 smoke 会漏掉这一点。

具体到流程，这一轮把"实验"做成了可回滚的：`trap restore` 保证无论探针怎么死，都会 `ci/rollback.sh` 回 001，
两次实验后 config md5 都回到 `53ac61e0…`、`restarts=0`、三方指纹一致。

## 十、下一轮

队列回到 **R95**（`P309`：launch 前后两个事件量 `busy/phase`，把 `host grouping` 那 91 ms 归因）——
它在 CI 绿、部署门活的条件下才值得做，现在两个前提都满足了。

## 十一、门与同步

`GH_GATE: PASS`（run #47，`6501c28f`；离线门 `ci/release_check.py:58` 的 SKIP 语义见 §6.5·W1029）；`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `MIRROR_CHECK` 全 PASS；
六件权威件双侧逐字节。本轮新增 `P374`（R99 关闭）、`P375`（hang 不复现的更正），`§0.1` 队列去掉 R99。
生产已回滚，现役性能仍是 prefill@2K **530.43 tok/s** / @8K **716.02 tok/s**（W1022 记录，本轮未复测）。
