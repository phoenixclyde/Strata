# CI/CD 蓝图建议（下游 fork · 单机 GPU · 单人维护）

> 触发：邮件里的 `Minimal serving runtime` 红灯已修完（`deploy/CI_CD_POLICY.md`）。
> 本文回答更上一层的问题：**我们这种仓库，GitHub Actions 和 workflow 一般该怎么组织**。
> 依据：GitHub 官方 secure-use / hardening 文档 + 2026 年小团队 CI/CD 实践（DORA 口径：elite < 10 min）+ 本仓实测。

## 0 先纠正三个前提（否则会照抄大厂方案）

1. **public 仓库的标准 runner 是免费的**。我们的 fork 是 `public`，所以"省额度"不是钱的问题，
   真正的成本是**注意力**（每次红灯一封邮件）和**排队时间**（r1 那个 run 排了 50 分钟队）。
   ⇒ 优化目标不是"少花钱"，是"少打扰、快反馈"。
2. **我们没有云端生产环境，所以 CD 不该放 GitHub**。生产是 166 那一台物理机
   （引擎 `0.1.55h`、容器 `strata166-407`、`/data` bind mount）。GitHub 的 runner 连不到它，
   也不应该连——让云端 token 能改生产，是把风险放大，不是自动化。
   ⇒ **CI 上云，CD 留在本地**（脚本 + 门禁）。这不是妥协，是这类部署的正确形态。
3. **单人维护 ≠ 小号企业**。分支保护、必需审批、merge queue、多环境审批，这些解决的是
   "多人协作下谁批准"的问题；我们没有这个问题，照搬只会拖慢自己。
   真正要保留的只有一条：**红灯必须看见、且不许被忽略**。

## 1 业内的标准骨架：四类 workflow

任何规模都逃不出这四类。区别只在于跑多快、跑多少。

| 类 | 触发 | 时长预算 | 失败意味着 | 我们有没有 |
|---|---|---|---|---|
| **PR 检查** | `pull_request` | < 5 min | 别合 | 有（但不发 PR，等价于"push 前的门"） |
| **主干全套** | `push` 到长期分支 | < 10–15 min | 主干不可发布 | 有（8m38s） |
| **发布** | tag | 几分钟 | 制品不合格 | 无（我们手工部署） |
| **夜间/定时** | `schedule` | 随便 | 环境或依赖漂移 | **无**（这是缺口） |

排序原则（业内一致）：**先跑快的、只跑受影响的**；慢的往后放，或挪到夜间/主干。
不做"每次 push 全跑一遍"——那是把 CI 当保险，结果是所有人学会忽略它。

## 2 我们的映射：8 个 → 2 个 active

| workflow | 现状 | 建议 | 怎么做 |
|---|---|---|---|
| `Minimal serving runtime` | active，8m38s，1298 用例 | **留**（唯一覆盖服务端的真门） | 已收窄分支 |
| `Portable monitor client` | active，~2 min，ubuntu+windows | **留** | 已收窄分支 |
| `Intake` | active，**带每日 cron** | **禁** | 仓库设置层 disable，不改代码 |
| `Reopen` | active，issue 评论触发 | **禁** | 同上 |
| `Title area` | active，PR/issue 触发 | **禁** | 同上 |
| `Scripts test` | active，PR 触发 | **禁** | 同上 |
| `Metal build` | active，macOS PR | **禁**（我们没有 mac 改动） | 同上 |
| `Docker images` | active，手动，推 `ghcr.io/niko1221/*` | **禁**（推的是上游 namespace，在 fork 里无意义） | 同上 |

**为什么用 disable 而不是删文件**：删文件就是一个下游补丁，每次 `rebase upstream/main` 都要处理冲突，
而且上游以后改进这些 workflow 我们就收不到了。`disable` 是仓库设置层，**一个 API 调用、随时 `enable` 回来、
零 rebase 成本**。这是"fork 里管 CI"最干净的一层。

代价：设置不在 git 里，别人 clone 看不到 ⇒ 必须写进 `docs/DOWNSTREAM.md`（已写）。

## 3 我们真正缺的三块（按性价比排序）

### 3.1 引擎改动零 CI（最大缺口，建议先补）
`src/`、`include/`、`CMakeLists.txt` **不在任何 workflow 的 `paths` 里**。
我们的核心改动（`native_mmvq.cu` 的 R 表、`STRATA_MMVQ_WAVE_ROWS`）一次 CI 都没过；
上次"env 回退开关只存在于注释里"这种缺陷，CI 也抓不到。

**建议做静态门**（零 GPU、10 秒、托管 runner）：
- R 表覆盖的形状在允许集合内、`wave_rows_for` 返回值 ∈ {1,2,4}；
- `STRATA_MMVQ_WAVE_ROWS` 有真正的 `getenv`（不是只有注释）；
- `wave_rows_env` 的默认分支必须返回 1（回滚路径可用）；
- 关键文件缺少 `-DNDEBUG` / 用错 `hip_compat` 路径时报警（这两个坑各值 47% / 45% 性能）。

这层挡不住数值回归，但能把"配置面"的错挡在提交前。

### 3.2 没有夜间回归
push 收窄后，实验分支不再自动跑。一旦上游/依赖漂移，我们只会在下次 push 时发现。
**建议加一个 nightly**（只跑 `Minimal serving runtime` + 静态门），失败只发一封邮件。
成本：每天一次 9 分钟免费 runner。

### 3.3 真机门只能靠自托管（不急）
编译 + 逐位等价 + A/B 必须在那张 MI50 上。自托管 runner 的代价不是技术，是**互斥**：
单卡 33.5/34.3 GB，编译或 bench 时不能推理。要么停机窗口跑，要么做锁。
**现在不做**，等"内核改动开始频繁"时再做——否则会为了自动化牺牲生产。

## 4 安全基线（五条，成本极低）

| # | 条款 | 我们的状态 | 动作 |
|---|---|---|---|
| 1 | `permissions:` 最小化，禁用 `write-all` | 已满足：仓库默认 token = **read**；各 workflow 自己声明 | 保持 |
| 2 | 不用 `pull_request_target` 跑不可信代码 | 上游的 `Intake` 用了，但**只 checkout 默认分支的脚本**、不跑 PR 代码 | 禁用后风险归零 |
| 3 | 不把不可信输入插值进 `run:` | 上游用 `env:` + 引号，合规 | 保持 |
| 4 | 第三方 action 固定 SHA | 我们**只用官方 action**（checkout / setup-python / github-script） | **不强制** |
| 5 | 定期更新 action | 未开 Dependabot | 可选（单人 + 官方 action，收益低） |

⚠️ **一个反直觉的点**：仓库设置里有 `sha_pinning_required = false`。**千万不要打开它**。
上游全部 workflow 用的是 `@v7` / `@v4` 这类 tag，一旦强制 SHA pinning，**上游这两条测试 workflow 会立刻全红**，
而我们不改上游文件（改了就每次 rebase 冲突）。这一条属于"看起来更安全、实际把我们锁死"的选项。

## 5 我们的 CD 该长什么样

生产在 166，部署靠脚本，所以 CD 的形态是"**一条命令 + 一个 tag + 一条回滚命令**"，不是 GitHub 流水线。

现有资产已经够了（本轮验证过）：

```bash
# 编译（逐字取 ninja 的命令，避开 CMake 重生成）
bash albus/w863/d11_build3.sh
# 换二进制（cp -> .new -> mv）+ 改 config 的 exe
bash albus/w863/d13_deploy.sh
# 重启 + 健康门
bash albus/w863/d14_restart.sh
# 回滚（30 秒，不重编）
#   config 的 env 加 STRATA_MMVQ_WAVE_ROWS=1 → restart
#   config 的 exe 改回 /data/bin/strata-0.1.55g → restart
```

要补的只有两条，都属于"让人不犯错"：

1. **部署前强制看 tag**：`git describe --exact-match HEAD` 必须命中 `mi50-*`，
   否则不许部署（防止拿未打 tag 的提交上生产）。
2. **部署后自动写一行台账**：exe md5 / cfg md5 / 镜像 id / 启动时间 / VRAM，
   追加到 `deploy/PROD_BASELINE.tsv`。这样"落产"永远可对账，不靠记性。

## 6 三步走（2026-11-01 现状）

| 阶段 | 做什么 | 状态 |
|---|---|---|
| **今天** | ① disable 6 个无关 workflow ② 写进 `docs/DOWNSTREAM.md` ③ 默认分支上的调度副本 | ✅ 完成（8 → 2 active，干掉每日 cron） |
| **本周** | 静态门（§3.1）+ 上游监视 | ✅ 完成（`ci/gate.py` 18 项；`Upstream watch` 每日跑） |
| **以后** | 自托管 runner、测试 shard、nightly | ⏸ 见下 |

### 已落地的东西

| 位置 | 入口 | 实测 |
|---|---|---|
| GitHub · 静态门 | workflow `Downstream gate` → `ci/gate.py --source-only` | run `45cee350` **success**（11 项） |
| GitHub · 上游监视 | workflow `Upstream watch`，每日 09:23 CST | run `41291722718` **success**，日志 `BEHIND: 0` |
| 166 · 全量门 | `ci/strata-ci check` | **18 项全过**（源码 + build.ninja + 生产 config） |
| 166 · 部署门 | `strata-ci deploy` | 未打 tag 时**拒绝**（已实测）；`--allow-untagged` 走完 7 步 dry-run |
| 166 · 回滚 | `strata-ci rollback --last` | 一条命令，读台账定位上一版 |

### 为什么 nightly 暂时不做

`requirements.txt` 是 `==` 全 pin 的，PyPI 漂移面很小；真正的漂移源是 **runner 镜像升级**
（已收到 Ubuntu 26 迁移通知），GitHub 会提前公告。
每天多一封可能失败的信，收益不抵噪声。
**触发条件**：真被镜像升级坑过一次，或开始用非 pin 的依赖 —— 那时再加，一个 schedule 就够。

### 为什么自托管 runner 也不急

编译 + 逐位等价在那张 MI50 上，而单卡 33.5/34.3 GB 意味着 runner 跑起来时**不能推理**。
自动化的收益（省一次手动）小于它带来的风险（抖一下就是生产事故）。
**触发条件**：内核改动频率上升到"每周多次"，或出现必须靠机器判的数值回归。


## 7 明确不做（以及为什么）

| 不做 | 原因 |
|---|---|
| 分支保护要求"至少一人 approve" | 单人仓，等于自己批自己，纯仪式 |
| merge queue | 没有并发合并，无用 |
| 多环境（staging/production）+ 人工审批 | 只有一台机，环境即生产 |
| 每次 push 全量跑 | 会退化成一封封邮件，人学会忽略（本轮就是 5 封） |
| 矩阵扩 OS / Python 版本 | 只服务 Linux，扩了是自找红 |
| 在 fork 里跑上游的 issue/PR bot | 那是上游的治理流程，与我们无关 |
| 把 CI 做成 CD | 生产不在云端，云端不该有改生产的权限 |

## 8 判据（下次再有人问"CI 红了我该管吗"）

1. **是长期分支吗**（`main` / `gfx906/mi50` / `ci/**`）？不是 ⇒ 关掉/别管。
2. **`main` 也是红吗**？是 ⇒ 先查上游本身；否 ⇒ 我们的补丁破了上游（必修）。
3. **失败在依赖安装还是测试**？依赖 ⇒ 网络/PyPI，别改代码；测试 ⇒ 看断言。
4. **断言是 "unexpectedly None / 找不到属性"** ⇒ 优先怀疑我们删了上游新代码依赖的东西（本轮正是）。
