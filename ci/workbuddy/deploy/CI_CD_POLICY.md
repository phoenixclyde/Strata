# W863 · CI/CD 方针（下游 fork）

> 触发原因：2026-11-01 07:49–08:03 邮箱收到 5 封 GitHub Actions 失败通知，全部是
> **"Minimal serving runtime"**，落在我们分支的 4 个 commit 上（`7c38cb4e` / `aef9d256` /
> `f8bfcd6d` / `339c1a8f`）。本文记录根因、修法，以及这类下游仓的 CI 该怎么配。

## 1 结论先说

**红灯是我们的补丁打出来的，不是上游本来就红。** 一条 4 行的改动，`serve/telemetry.py`。

| 分支 | 同一个 workflow | 说明 |
|---|---|---|
| `main`（= v0.2.9 + docs） | **success** | 没有下游补丁 |
| `gfx906/0.2.8-mi50` | failure | 有我们的 PCIe 带宽补丁 |
| `gfx906/0.2.9-mi50` | failure | 同上（重放后） |
| `gfx906/mi50`（修复后 `c3574d42`） | **success**（run 41288894503，8 分 38 秒，1298 用例全过） | 修完即绿 |

判据：`main` 绿、`gfx906/*` 红，差异面只有 `serve/telemetry.py` 54 行 ⇒ 归因明确。

## 2 根因（已实测反证）

我们的 PCIe 带宽补丁把这一行改成了匿名线程：

```python
# 上游 v0.2.9
self._thread = threading.Thread(target=self._loop, daemon=True)
self._thread.start()

# 我们的补丁（错）
threading.Thread(target=self._loop, daemon=True).start()
```

上游 v0.2.9 **新加**了 `serve/test_responses.NoLeakedSampler`，它靠 `telemetry._thread`
判断"停服后采样线程有没有结束"：

```python
thread = getattr(sampler, "_thread", None)
self.assertIsNotNone(thread, "the server did not start its hardware sampler thread")
```

属性恒为 `None` ⇒ 断言必挂。CI 原文：

```
FAIL: test_server_close_ends_the_sampler (test_responses.NoLeakedSampler)
AssertionError: unexpectedly None : the server did not start its hardware sampler thread
Ran 1298 tests in 431.520s
FAILED (failures=1, skipped=17)     # 1297 过、1 挂
```

**两臂反证**（同一棵树，只换 `telemetry.py`，容器内跑，不碰生产 GPU）：

| 臂 | 结果 |
|---|---|
| `.w863bak`（发出去的那版，匿名线程） | `FAILED (failures=1)`，报错与 CI 逐字一致 |
| 修复版（保留 `self._thread`） | `OK`，0.52 s |

修法（`c3574d42`）：恢复两个线程引用，并让 `close()` 真的 `join` 它们
（1 Hz 采样 + 5 s PCIe 读取，两个线程都要在停服时结束）。

> 这不是"测试太严"。线程引用丢了，`close()` 就没法 join 采样线程——测试替我们抓到了一个
> 真实的资源泄漏点。

## 3 这类仓的 CI 该怎么分层（业界做法）

下游/厂商 fork 的 CI 只有三种颜色含义，混淆就会浪费大量时间：

| 颜色 | 含义 | 处置 |
|---|---|---|
| **绿** | 我们的补丁没破坏上游行为 | 继续 |
| **红（我们的）** | 补丁破坏了上游测试 | **必修**，不许屏蔽 |
| **红（环境的）** | 该测试需要 GPU/网络/外部服务，托管 runner 给不了 | 该测试改 `skipUnless`，不是加 `\|\| true` |

三条标准做法（本轮全部落地）：

1. **default-deny 触发**：`branches:` 白名单 + `paths:` 只留相关路径。文档明确：
   *"No paths: filter means match-all；路径过滤在分配 runner 之前生效，是最便宜的守卫"*。
2. **concurrency + cancel-in-progress**：同一分支连推三次，取消前两次。
   本轮第一个 run **排队 50 分钟**才拿到 runner（run 时长 1h8m55s，job 实际只跑 9m18s）。
3. **重试放在测试级、不放在 job 级**；quarantine 必须有 owner + 期限，
   "没有期限的隔离清单和删掉测试等价，只是还在烧机器时间"。
   我们这个失败**不是 flaky**（两次都挂在同一断言），所以不重试、直接修。

## 4 现有 8 个 workflow 的定位

| workflow | 触发 | 下游是否需要 | 处置 |
|---|---|---|---|
| `terminal-minimal-server` | push / PR（`serve/**` 等） | **要**，唯一覆盖服务端的门 | 收窄分支 + concurrency |
| `terminal-portable-monitor` | push / PR（`strata_cli/**` 等） | 要，覆盖监控客户端 | 收窄分支 + concurrency |
| `intake` | `pull_request_target` / issues | 否（上游 PR 治理） | 不动（我们不开 PR，不会跑） |
| `title-area` | PR / issues | 否 | 不动 |
| `reopen` | issue_comment | 否 | 不动 |
| `scripts-test` | PR（`.github/scripts/**`） | 否 | 不动 |
| `metal-build` | PR（macOS） | 否 | 不动 |
| `docker-images` | `workflow_dispatch` | 手动，不自动跑 | 不动 |

结论：**push 时真正会跑的只有前两个**，其余 6 个要么 PR 触发、要么手动，不烧额度。
所以不需要删文件，只需要把前两个的触发收窄。

## 5 本轮改动（提交 `ci: narrow the two push-triggered workflows`）

```yaml
on:
  push:
    branches: [main, gfx906/mi50, 'ci/**']   # 长期分支 + 显式的 ci/ 试验分支
    paths: [...]                              # 上游原样保留
  pull_request:
    branches: [main]                          # 只有发 PR 时才跑
    paths: [...]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

三点设计意图：

1. **tag push 不再触发**。只写 `branches:` 不写 `tags:` 时，tag 事件不匹配 —— 正好：
   `mi50-0.2.9-r1` 那个 run 排了 50 分钟队，测的是已经测过的代码。
2. **`gfx906/*` 旧命名分支不再触发**。实验线不应烧额度；要跑 CI 有两条明路：
   合到 `gfx906/mi50`，或开 `ci/<名字>` 分支。
3. **`paths` 一个字没动**，所以 rebase 上游时这里最多 4 行冲突。

## 6 明确不做的事

- **不 `|| true`、不 `continue-on-error`、不删这个测试**。它是我们唯一能发现
  "改 serve 改坏了"的机器证据，屏蔽掉等于自废探针。
- **不搞 job 级自动重试**。这个失败是确定的（两次同错），重试只会把真失败洗成绿。
- **不在 fork 里重跑上游 PR 治理类 workflow**（intake/title-area/reopen）。上游怎么管 PR
  是他家的事，与本仓无关。

## 7 还没覆盖的洞（要你定）

**现有的 CI 完全不测引擎内核。** `terminal-minimal-server` 的 `paths` 里没有
`src/`、`include/`、`CMakeLists.txt`。这意味着：

- 我们的核心改动（`native_mmvq.cu` 的 R 表、`STRATA_MMVQ_WAVE_ROWS`）**一次 CI 都没过**；
- 上次"env 回退开关只存在于注释里"这种缺陷，CI 抓不到，只能靠人。

两条路：

| 方案 | 做法 | 代价 | 风险 |
|---|---|---|---|
| **A 静态门（推荐先做）** | 在托管 runner 上跑一个纯 Python 检查：R 表形状齐全、`getenv` 真存在、`wave_rows_for` 返回落在 1..4、无 `\|\| true` 式兜底 | 零 GPU、零停服、10 秒 | 只能防"配置面"缺陷，防不了数值/性能回归 |
| B 自托管 runner | 把 166 注册成 self-hosted runner，跑"编译 + 逐位等价" | 需要与生产互斥（单卡 33.5/34.3 GB，编译时不能推理） | 抖一下就是一次生产事故；必须先做互斥锁 |

A 可以作为下一个提交，B 需要你点头（会在生产机上常驻一个进程）。

## 8 出红灯时的处置手册（三条判据，按序）

1. **看分支**：`main` 绿而我们的分支红 ⇒ 是我们的补丁，必修（本轮就是这个）。
   两边都红 ⇒ 先看上游是否本来红（API 查上游同 workflow 的 runs）。
2. **看步数**：失败在 `Run full server suite` ⇒ 真测试；失败在 `Install pinned runtime
   requirements` ⇒ 依赖/网络，先查 PyPI 可达性，别改代码。
3. **看断言**：报错里有 `AssertionError: unexpectedly None` 这类"拿不到对象"⇒ 优先怀疑我们
   删了上游新代码依赖的属性/接口（本轮正是）。上游 v0.2.9 新增测试校验旧属性，是 rebase 后
   最常见的红法。

> 经验沉淀：**上游每加一个新测试，等于给我们的补丁加一道回归门**。每次 rebase 后第一时间
> 看 CI，比事后在生产上排查便宜得多（本轮 4 行代码，代价是 5 封邮件 + 一次 9 分钟排队）。
