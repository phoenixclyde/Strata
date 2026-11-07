**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0）——**本轮未重编** |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:45:25Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮**未动用**，零改动零重启） |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` **三方一致**（`build-r28` 里另有一份合并后重编的产物，未部署）；树从 `v0.2.10` 基线变为 **`v0.2.11-69`** |

**二、主线** gfx906/mi50 @ 85297483 · tag `mi50-0.2.11-r33-1`（`git describe` = `v0.2.11-69-g85297483`）· **落后上游 0 / 领先上游 65** · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；回滚件未用；代码面 3 提交（`e21b1b01` 合并、`1ec9c750` 修 `build.sh`、`85297483` 修证据跟踪）。
**四、进度** 269 条 / 已结 189 / **70.3%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、上游不是「0」，是 **208 个提交**

每轮报告都写「上游 `ffa80d73`」。`git fetch upstream` 之后：

```
ffa80d73..9f7d977d  main -> upstream/main        (new tag: v0.2.11)
ahead=63  behind=208
```

**「落后 0 / 领先 0」那句一直说的是 `origin/gfx906/mi50`（自己的远端），不是上游。** 两条不同的比较写成一个词，和 `1.91×` 同源：口径没写清就等于说错。

合并**零冲突**：`git merge-tree --write-tree HEAD upstream/main` 先预演（rc=0、0 条 `CONFLICT`），再 `--no-ff` 真合并 `e21b1b01`：**338 文件 +21,481 / −1,187**。合并后 we're **behind 0 / ahead 65**。

## 六、引擎面只有 3 个 TU，两项与我们无关但值得记

| 文件 | 上游改了什么 | 对我们的影响 |
|---|---|---|
| `src/prefill/prefill.cpp:418` | `STRATA_GFX12_RING`：gfx12 专属的更深 ring（R9700 4K **+12.5%**、UD-Q4 +6.9~9.5%；16K 略负；`:414` 是它的注释原文） | **gfx906 不走这条分支**；反向印证 `R98`——ring 深度是**卡相关**的（他们要 192/256，我们 768 慢 0.5–0.6%） |
| `src/prefill/gemm.cu` | Q5_0 同族的 dot 偏移整理（含 `aa678f10`） | 盘上无 Q5_0（down=Q5_1/Q8_0、gu=Q4_K/Q5_K）⇒ 无行为变化 |
| `src/prefill/gemm_w16_parity.cu` | 配套 parity 用例 | 只影响测试 |

上游 `aa678f10`（Q5_0 的 −16 取「量化激活之和」）给了一条判据：**换 pack 类型必须逐族核 `Σq` 偏移**，同族之间真的会漏一个常量。

## 七、验证（机械的，但只到「能编能链」）

- `bash ci/strata-ci check` → **23 checks / 0 failed**；`python3 ci/round_gate.py --ci` → **PASS**。
- `ci/build.sh --file src/prefill/gemm.cu` → 编译+归档+链接通过：`strata` **42,924,432 → 42,924,600 B**（md5 `ae085365… → 327c9476…`）。
- `ci/build.sh --file src/prefill/prefill.cpp` → 先失败、修好后 **14.6 s 通过**，重链接 md5 不变（确定性）。

**没有做**：合并后的二进制**未部署、未做运行期验证**。生产仍是 `eea5ea37…`。要不要把 v0.2.11 变成新二进制，走的是 build→bench→compare→deploy 那条门，不属于「跟上游」这一步。

## 八、这一轮抓到两个门缺陷，其中一个是我自己的谎报

**① `ci/build.sh:47` 编不了 host C++ TU。** 它用 `grep -- '-x hip -c'` 找编译行，而 `prefill.cpp` 是 host C++（命令行里只有 `-c`）⇒ 只打印
`COMPILE LINE NOT FOUND for prefill.cpp.o` 并 `exit 11`（`ci/build.sh:51`），**而调用方的 for 循环接着跑下一个文件**，看起来像跑过了。已改成匹配 ` -c `（排除 `-E -M`）。合并后最重要的那个 TU 恰好是它。

**② CI 已经红了五次，我报的是「run #31 success」。**（`tools/report_lint.py:25` 要求主线写 `mi50-<版本>`，本轮补 tag `mi50-0.2.11-r33-1` 而不是放宽这条正则。） 查下来 `#32`（`759a4edb`）起就连红：`BUNDLE.tsv` 两行把证据指向 `ci/state/cfg/*.json`——**gitignore 的生成物**，本机有、CI 没有。本机绿、GitHub 红，连续四个提交没人看。

修法：三份 A/B 记录移进 `ci/bundle_budget/evidence/`（受跟踪），`ci/bundle_budget/bundle.py:79` 在 **git 工作树内**要求证据被 `git ls-files` 认得，否则报「exists here but is NOT tracked by git (CI cannot see it)」（`bundle.py:96`）。本地工作区不是 git 仓库 ⇒ 这条检查本地被跳过，**这正是「本地跑不能是唯一一次跑」的原因**，已写进脚本注释。修复后 **run #37 success @ `85297483`**。

## 九、举一反三：三种「眼睛只装在一处」

`W832` 本机↔166（W1003 冻结两天）、报告文件↔聊天（W1015 我自己压缩）、证据本机↔CI（这轮四次红）。三次都是**同一份事实有两个副本、校验只覆盖一个**。规矩再加一条：**凡是「本机能跑、远端也有」的东西，验收必须包含远端那一次**；本地绿只能作为必要条件。

## 十、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1018`、`P336`（208 提交零冲突并入 v0.2.11）、`P337`（`build.sh` host TU 静默失效）、`P338`（Q5_0 −16 / GFX12_RING 判据）、`P339`（CI 连红 5 次与本机绿），`§0.1` 新增「主线 / 上游基线」一行。
