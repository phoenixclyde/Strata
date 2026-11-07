# 一次完整 CI/CD 怎么走（GitHub + 166）

> 这份是可直接照抄的操作单。上面那张泳道图是它的骨架，这里是每一步的真实命令、产物、失败处置。
> 三个入口场景：**日常改代码**、**上游发新版**、**出问题回滚**。

## 0 先明确一件事：哪些是自动的，哪些是我手动触发的

| 步骤 | 谁触发 |
|---|---|
| GitHub 上的静态门 / 上游测试 | **自动**（push 就触发） |
| 166 上的 check / build / bench / deploy | **手动逐条**（不是 push 自动） |

为什么 166 不自动：**单卡 33.5/34.3 GB 被生产占满**，自动构建会和推理抢 GPU，等于让 CI 打生产。
业内的解法是 self-hosted runner + 标签路由 + 停机互斥；在"一张卡就是生产"的形态下，
**人在环**是更安全的等价物。这不是没做到自动化，是显式选择了不自动。

## 1 场景 A：日常改代码（最常用）

### A1 改完，先本地看差异

```bash
cd /home/albus/strata166/pr/strata-fork
git status --porcelain          # 确认只改了你以为改的东西
git diff --stat
```

### A2 推上去，GitHub 自动跑（并行，你不用等）

```bash
git push origin gfx906/mi50
```

触发两个 workflow（按路径过滤）：

| workflow | 什么时候跑 | 时长 |
|---|---|---|
| `Downstream gate` | 改 `src/` `include/` `CMakeLists.txt` `ci/` `.github/workflows/downstream-gate.yml` | ~20 s |
| `Minimal serving runtime` | 改 `serve/` `strata.py` `requirements.txt` 等 | 8m38s（1298 用例） |

### A3 本机静态门（秒级，别等 GitHub）

```bash
/home/albus/strata166/ci/strata-ci check
```

18 项：R 表形状/取值、`getenv` 真存在、`-DNDEBUG`、hip_compat 路径、备份文件、生产 config、health。
**红了就停**，不要进下一步。

### A4 构建（8–10 分钟）

```bash
/home/albus/strata166/ci/strata-ci build
```

产物：`gfx029-build/strata`（新 md5）+ 新 `libstrata_kernels.a`。
逐字取 `ninja -t commands` 的三条命令，flag 不手抄（漏 `-DNDEBUG` 慢 47%，错 hip_compat 慢 45%）。

### A5 实验门（30 秒，这一步以前没有）

```bash
/home/albus/strata166/ci/strata-ci bench --n 12 --warmup 2 --label <这次改了什么>
/home/albus/strata166/ci/strata-ci runs            # 拿到 run id
/home/albus/strata166/ci/strata-ci compare <基线run> <新run>
```

产物：`ci/state/runs/<run_id>.json`（git sha / exe md5 / env / 逐次样本 / CV）。
判据：**差异 > 2×CV 才算数**（实测稳态 CV 1.06% ⇒ 阈值 2.12%）。
`compare` 会拒绝 CV > 10% 的 run，并打印"两次之间到底变了什么"。

### A6 打 tag（部署的门票）

```bash
git tag -a mi50-0.2.9-r3 -m "..." && git push origin --tags
```

`deploy` 拒绝无 tag 的 HEAD，这是工具强制的，不靠记性。**tag 只加不移动。**

### A7 部署（先 dry-run，再 apply）

```bash
/home/albus/strata166/ci/strata-ci deploy            # 打印 7 步，什么都不改
/home/albus/strata166/ci/strata-ci deploy --apply    # 4–5 分钟（重启 246–290 s）
```

7 步：gate → tag 门 → 二进制身份（符号 + env 字符串）→ `cp→.new→mv` → config 备份改 exe →
重启等健康 → 健康门 + 权重账目 + 台账。

### A8 收尾：台账 + 回写 GitHub

```bash
# 166 上已自动写 ci/state/prod_history.tsv
# 本机持有 token，把状态写回 commit
python albus/ci/publish.py
```

结果：commit 上出现 `strata/166 -> success | strata-0.1.55h · 69.5 tok/s (CV 1.06%) · VRAM 33.6 GB · env 6 · health ok`。

### A9 记账

`deploy/PROGRESS.tsv` 对应条目的 note 里写 `run=<run_id>`，结论可回溯到原始样本。

## 2 场景 B：上游发新版

```bash
/home/albus/strata166/ci/strata-ci watch     # 落后多少、新提交列表
```

GitHub 的 `Upstream watch` 每天 09:23 会自己开一个 issue 提醒（追平自动关闭）。

```bash
cd /home/albus/strata166/pr/strata-fork
git fetch upstream --tags && git rebase upstream/main
# 冲突高发：workflow 4 行 / telemetry.py 的 self._thread / R 表整块 / CMakeLists 取上游
git diff --stat <old-tip> <new-tip> -- src/ include/ serve/ CMakeLists.txt   # 必须为空
```

然后走 **A3 → A8 全流程**（rebase 后必须重编 + 验证，不能只推不验）。

## 3 场景 C：回滚（故障时）

```bash
/home/albus/strata166/ci/strata-ci rollback --last --apply     # 约 4–5 分钟
```

两种更快的运行时回滚（不重编，只重启）：

- config 的 `env` 加 `STRATA_MMVQ_WAVE_ROWS=1` → 关 R 表，回旧内核行数
- config 的 `exe` 改回 `strata-0.1.55g` → 整颗引擎回旧版

## 4 每步失败怎么办

| 红在哪 | 含义 | 处置 |
|---|---|---|
| `Downstream gate` | 配置面缺陷（表/开关/flag） | 修源码再推；**不进 166** |
| `Minimal serving runtime` | 改了 `serve/` 破坏上游行为 | 看断言；`unexpectedly None` 优先怀疑我们删了上游依赖的属性 |
| `strata-ci check` | 同静态门，但含构建树与生产 config | 同上 |
| `strata-ci build` | 编译失败 | 看 `docker logs strata-ci-build`；**不要**去容器 `/src` 下重编（镜像里 `native_mmvq.cu` 是旧版，会静默丢 R 表） |
| `bench/compare` 判 NOISE | 差异小于噪声 | 不要写进结论；要么加样本，要么用微基准 |
| `deploy` 拒在 tag 门 | HEAD 没 tag | 打 tag，或 `--allow-untagged` 仅在调试时用 |
| `deploy` 健康超时 | 起不来 | `rollback --last --apply`；看 `data/strata-*.log` |

## 5 时间预算（一次顺利的改动）

| 阶段 | 时长 | 是否阻塞你 |
|---|---|---|
| GitHub 静态门 | ~20 s | 否（并行） |
| GitHub 服务端用例 | 8m38s | 否（并行） |
| 166 check | 秒级 | 是 |
| 166 build | **1–2 min**（单 TU；8–10 min 是首次/冷启动口径） | 是 |
| bench + compare | ~35 s | 是 |
| deploy（含重启） | 4–5 min | 是，**期间服务不可用** |
| publish | 秒级 | 否 |

**串行关键路径 ≈ 13–16 分钟**，其中 4–5 分钟是停服。

## 6 边界（什么进仓库、什么不进）

| 进仓库 | 不进 |
|---|---|
| `ci/` 全部脚本（bash -n / py_compile 由 CI 检查） | `ci/state/runs/*.json`（运行数据） |
| `.github/workflows/` 我们自己的 3 个 | 生产 config / 二进制 / 台账 |
| `docs/DOWNSTREAM.md` 补丁台账 | `albus/ci/publish.py`（持 token，留本机） |

---

## 7 实跑记录（2026-11-01 18:0x–18:5x，一次真实改动）

用"把 R28 的结论写进内核注释"作为真实改动，走了一遍 L1→L2→L3→L4→回写，并逐项核验。

| 步 | 实测 | 结果 |
|---|---|---|
| L1 `gate.py` | 秒级 | 18/18 PASS |
| L3 基线 `bench --n 12` | ~40 s | median 68.86 tok/s，CV 4.36% |
| L2 `build` | **1 分 14 秒** | exit 0；**产物 md5 与旧版完全相同**（注释不改机器码） |
| L4 `deploy` | 231 s 重启 | 装成 `0.1.55i`，台账写入，健康 ok，权重账 499/3619.14 |
| L4 二次 `deploy` | 秒级 | 被新保护拒绝：`NOTHING TO DEPLOY` |
| L3 后测 + `compare` | ~40 s | −0.48%，阈值 8.72% → **NOISE**（控制组没误报） |
| 回写 `publish` | 秒级 | `strata/166 -> success | 0.1.55i · 68.5 tok/s (CV 3.86%) · VRAM 33.5 GB` |
| 核验 `dryrun_2_verify.sh` | 秒级 | **11 项全 PASS** |

### 这轮暴露并修掉的两个缺陷

1. **`deploy` 会为"内容相同"的二进制重启生产**。第一版只比较*目标文件*，而新版本号的文件还不存在
   （`strata-0.1.55i` 首次部署时 `[ -f ]` 为假）⇒ 一路走到重启，白停 4 分钟。
   改成比较**config 里生产正在跑的那个 exe** 的 md5，相等就退出（`--force` 可越过）。实测已生效。
2. **`build` 的实际耗时是 1 分 14 秒**，不是文档里沿用的 8–10 分钟。8–10 分钟是首次/冷启动的口径。
   以后时间预算按 1–2 分钟报，除非重建整棵树。

### 一条值得记住的现象

同一个引擎、同一台机，两次 12 样本测出的 **CV 分别是 4.36% 和 3.86%**，而更早一次是 1.06%。
也就是说噪声底本身在变（离群点 61.9 tok/s 反复出现）。**判据必须用当次 run 的 CV**，不能拿历史最小值套。

---

## 8 已知的两笔账（重建镜像时必须一起清）

| # | 欠什么 | 为什么现在不单独处理 | 怎么消 |
|---|---|---|---|
| **A11**（AUDIT19） | 镜像 `/src/serve/telemetry.py` 仍是旧版（缺 `self._thread` 的 CI 修复） | 它只是显示层的线程引用，**不影响推理**；为它单独停服重建镜像不值 | 下次重建 `0.2.9-102` 时随镜像带上；重建后 `docker exec strata166-407 md5sum /src/serve/telemetry.py` 应与主线一致 |
| **A8**（AUDIT18） | `ci/dryrun_2_verify.sh` 里硬编码了 `0.1.55i` | 它是一次性核验脚本，不是常设门 | 已在脚本头标注「一次性」；常设门用 `strata-ci check` |

**纪律**：重建镜像不是"顺手做的事"。`/src` 是镜像内容（不是挂载），重建等于换运行期 Python 层，
必须走 `strata-prod-upgrade` 技能里的建镜像流程，并在同一个窗口里把上面两笔账一起清掉。

---

## 9 屋顶探针（AUDIT19 / R29）：一次实测，永久有分母

```bash
bash /home/albus/strata166/ci/probe/stream_roof_run.sh    # 容器内编译 + 运行，~40 s
```

它测两件事，都是"别再猜"：

| 量 | 用途 |
|---|---|
| **读屋顶**（实测 884 GB/s = 86.3% 规格） | decode 一步几乎只读不写 ⇒ 所有「带宽利用率」的分母 |
| 拷贝屋顶（实测 752 GB/s） | 需要读+写的阶段才用它 |

顺带给出并行度曲线：1 block/CU 只有 55%，**4 blocks/CU 峰值 86%**，8 blocks/CU 反降到 82%。
探针只用 ≤256 MiB 显存，可与生产同时驻留——已经这么跑过一次，生产未受影响。
源码在仓库 `ci/probe/stream_roof.cpp`，换卡/换 ROCm 版本后重跑一次即可刷新分母。

---

## 10 每轮收尾门（W1002 新增，补的是「调用者」）

W980 承诺「改成机制、不靠我记得」，实际只装了 `pre-commit → gate.py --source-only`。
结果：16 个提交未推、报告 lint 在本机无人调、W999/W1001 的实验源码留在 `/tmp` 与
`build-tab/repacktest/`、活方案分裂到 `W986_PLAN_V3.md`（`plan_lint` 正在报 FAIL）。
**工具齐备但没有调用者，等于没有门。**

现在一条改动从写到发，会经过四道自动门：

```bash
# 提交（自动）
git commit                    # pre-commit: gate.py --source-only + round_gate.py --ci
# 推送（自动）
git push origin gfx906/mi50   # pre-push: fork 策略 + round_gate.py --ci
# 远端（自动）
#   GitHub Actions / Downstream gate: verify.py + round_gate.py --ci
# 166 收尾（每轮一次）
cd /home/albus/strata166/pr/strata-fork
/home/albus/strata166/ci/strata-ci check       # 18 项静态门
python3 ci/round_gate.py --status             # 已推? 树干净? 证据齐? 移植状态?
# 本机收尾（每轮一次）
python albus/w1002/round_close.py --report albus/w1002/reply.md   # 四个 lint
```

`round_gate.py --ci` 做三件事：跑 `ci/repack_ab/verify.py`（产物 / 结果一致性 /
fair-A/B 标记 / 移植状态 / CI 接线）、对 `report_lint` 做**正例必须 PASS + 反例必须 FAIL**
的自测、检查 `PORT_STATUS.md` 存在。`--status` 额外检查 hooks 已装、
工作树干净、`remote HEAD == local HEAD`。

**负向自测是硬要求**：`albus/w1002/negative_test.py` 注入 5 种破坏
（伪造 ratio / 清空移植状态 / 删 fair-AB 标记 / 摘掉 workflow 调用 / 让 lint 恒真），
每种都必须让门 FAIL、恢复后 PASS。W1002 实测 **5/5**。

### 本轮实跑记录（2026-11-05）

| 门 | 结果 |
|---|---|
| `commit ab68576c`（pre-commit 实跑） | PASS |
| `push 5f73cd15..ab68576c`（17 提交，pre-push 实跑） | PASS |
| GitHub `Downstream gate` **run #25** | `completed / success @ ab68576c`（API 查得） |
| `strata-ci check` | 18 checks / 0 failed / 0 skipped |
| `gate.py --source-only` | 11 checks / 0 failed |
| `verify.py` / `round_gate --ci` / `round_gate --status` | PASS / PASS / PASS |
| `round_close --self-test` | 坏报告被拒（PASS） |
| `plan_lint` | **FAIL → 整改后 PASS**（4 份 PLAN 未登记已处理） |
| `ledger_lint` | 59 → 29 problems（30 行 9 列台账已补第 10 列） |

门第一次正向运行就抓到真缺陷：Windows 上传的 `RESULTS.tsv` 带 UTF-8 BOM，
首行注释被计成第 5 条数据；`run.sh` 的 BOM 会让 shebang 失效。已去 BOM 并改
`utf-8-sig` 读取防复发。

> 边界不变：GPU 基准与部署仍留 166 **人在环**（单卡被生产占满，自动构建会抢 GPU）。
> 自动化的只有静态门与推送门；这不是没做 CD，是 `CI_CD_POLICY.md` §7 的显式选择。
