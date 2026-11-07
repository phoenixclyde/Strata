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
| 8 | 本轮改动 | 生产零改动、零重启（只读）；仓库 1 提交（报告门）；disk = build = running 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 360cbd4c · tag `mi50-0.2.11-r33-9` · 落后上游 0 / 领先 72 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 1 提交（`360cbd4c`，报告门 12→14 项）。
**四、进度** 291 条 / 已结 211 / **72.5%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50，另 `P359`（b12169 分派层，OPEN）。

---

## 五、你问「落权威调优方案了吗」——落了，给你 grep 得到的位置

| 内容 | 落点 |
|---|---|
| W1024 全部结论（容器内版本、rebase 复核、b12169 阻塞） | `deploy/W832_OPT_PLAN_V2.md:1961`（§6.5 回写·W1024） |
| 三个编号 | `P357`（容器内版本）/ `P358`（rebase 复核）/ `P359`（b12169 分派层，**OPEN**） |
| 依赖 pin | `deploy/W832_OPT_PLAN_V2.md:26`（§0.1「依赖 pin（llama.cpp）」） |
| **本轮新增** | 同文件 `:26` 的「**ROCm（容器内）**」行 + §6.5 回写·W1025 + `P360`/`P361` |

`P359` 是 OPEN 不是 DONE —— 它是要做的事（改 `src/prefill/moe_mmq.cu:505` 的 `mmq_args` 构造），估 **2–3 小时**，不是已完成的结论。

## 六、四项报告加了两个字段，而且是「行级」校验

原来的门（`tools/report_lint.py`）**全是全文级**：正文任何地方提到 `llama.cpp` 就算过 —— 这正是
「表里没有、正文里有、门还是绿的」的形状。本轮改成两条**行级 + 限定段落**（`tools/report_lint.py:36` 的 `LINE_REQ`，
`:71` 的 `scope` 只取「一、生产容器」段）：

| 字段 | 判据 | 为什么必须行级 |
|---|---|---|
| `F9 ROCm 版本` | 一段内某行同时含 `ROCm` + 版本号 + `HIP`/`hipconfig`/`.info/version` | 这台机器三套 ROCm 编号互不相等：打包 `10.1.0`、构建 ID `7.14.0-gfx906+20260802001858`、HIP `7.16.26323-0000000`。全文匹配会随便认一个 |
| `F10 llama.cpp 版本` | 同一段内某行同时含 `llama.cpp` + `bNNNNN` + **40 位 sha** | 7 位前缀不可校验；树 hash 才证明"哪棵树" |

实测有效性：同一份报告补 **2 行**前 `REPORT_LINT: FAIL (2)`（报"表内 0 行"），补完后 `PASS (14 fields)` —— 门从 **12 项** 变成 **14 项**，其中 2 项是行级。
`ci/round_gate.py:24` 的正样本也补了这两行，`ROUND_GATE: PASS`（7/7 + 4/4 + 两道自测）。

## 七、四项报告成了独立技能：`strata-report`

`~/.workbuddy/skills/strata-report/SKILL.md`，与 `strata-release` 分工明确：

- `strata-release`：**做**一版（rebase → 编 → 镜像 → 容器 → 验证）；
- `strata-report`：把这一版**写清楚**（四项 + 十字段 + 证据 + 门）。

技能里给了每一条的取值命令，包括容器内那三个：

```bash
docker exec strata166-407 cat /opt/rocm/.info/version      # 10.1.0
docker exec strata166-407 hipconfig --version              # 7.16.26323-0000000
docker exec strata166-407 cat /src/BUILD-IMAGE.json        # llama_cpp / build / tree
docker exec strata166-407 sh -c 'cd /src/third_party/llama.cpp && \
  find . -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum | md5sum'   # 6feee589…
```

还写进了 **6 条**真实失败模式（8 行表过门、聊天版缩水、版本写"7.x"、7 位前缀、机制无证据、门只装在一处），正文要求 ≥**1500 字符** 与 ≥**4 处** `file:line`。

## 八、判据再收紧一条：依赖版本必须「容器内」取

宿主版本、镜像台账、上一轮报告里的数字，**都不算**。这三处都曾经对不上：宿主是 ROCm 6.4.4，
容器 `.info/version` 是 10.1.0，而 `ROCM_BUILD` 又是 7.14.0-gfx906 —— 只有 `hipconfig` 和树 hash 是运行期事实。

## 九、门与同步

`REPORT_LINT: PASS (14 fields)`；`REPORT_DEPTH: PASS`；`ROUND_CLOSE: PASS`；`ROUND_GATE: PASS`；`plan_lint` A–F PASS；
`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `release_check`（10/10）全 PASS；
六件权威件双侧逐字节。本轮新增：§0.1「ROCm（容器内）」行、§6.5 回写·W1025、`P360`（报告门 12→14）、`P361`（`strata-report` 技能）。
