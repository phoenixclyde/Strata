# W938 · 三件事：回溯补账 / 主线 rebase 到 v0.2.10 / 容器跟主线

- 日期：2026-11-04 12:5x（CST）
- 触发：机主三条指令 ——「回溯，都补回来」「主线跟上游 rebase，整个线包括所有分支按业内一贯做法」「容器也跟着主线走」
- 结果：**三件全部完成**。生产跑 0.1.56（v0.2.10），镜像 `strata-gfx906:0.2.10-101`，主线 `5f73cd15` 已推到 fork，tag `mi50-0.2.10-r28`，账本与实验记录补全。

---

## 一、回溯补账

### 1.1 部署账本 `ci/state/prod_history.tsv`

修前只有 15 行、最后一行停在 **2026-11-02T00:15**（`strata-0.1.55t` / `e0c6f250` / r27），而 11-02 之后生产换过三次引擎。

补法（**不改写任何已有行**）：

| 类别 | 内容 |
|---|---|
| r17 之前的历史引擎 11 个 | 按 `/data/bin/*` 的 **mtime + md5** 回填（`0.1.53`、`0.1.54n/w/n2/n3/n4`、`0.1.55g`、`-banner`、`-routed`、`-mmvq`、`0.1.55h`），`tag` 列写 `-`（无 tag 证据），备注 `pre-ledger reconstructed: mtime of /data/bin/<name>` |
| 11-02 之后漏记的三次 | `strata-0.1.55u`(a97f4479)、`.55v`(8e92c662)、`.55w`(cf2ba243)，`tag` 列写 `-`，备注 `retro-recorded` |

补后 **26 行**，按 `ts` 排序；`rollback --last` 取 `tail-2` 的目标从错误的 `strata-0.1.55s`(r26) 修正为 `strata-0.1.55v`(8e92c662)。

> 为什么不补 r1–r16：那些引擎文件在 `/data/bin` 已不存在，md5 与部署时间都无证据。**不编造**是这条账本的前提。

### 1.2 实验记录 `ci/state/runs/`

修前 4 条，全部是 2026-11-01 的（r28 before/after、noise baseline/steady）。11-02 以来二十多个 A/B 只在 md 里。

补 **17 条**，每条都带：

```json
"reconstructed": true,
"provenance": "deploy/W921_R66_OPTIN_AB.md ...",
"samples": [],
"samples_note": "per-sample rows were not kept; metrics below are the medians stated in the source document"
```

覆盖：R67（PLE 锁前/锁后）、W920 trace A-B-A 三臂、R66（三 opt-in 关/开）、M3（k8v4 / k8v8）、R70（chunk 8192/16384/32768 @32K）、R75/W932（64K 两臂、130K）、R78、R77。

**每一条都不含我推导出来的数** —— 只搬文档里已有的中位数与 CV。

---

## 二、主线 rebase 到 upstream v0.2.10

### 2.1 标准流程（先备份，再动）

```bash
git bundle create backup/strata-all-refs-20261104.bundle --all     # 76 MB，全 refs
git branch -f pre-rebase/<每个分支>                                # 6 个指针
git config rerere.enabled true                                     # 冲突解复用
git fetch upstream --tags                                          # upstream/main = ffa80d73 (v0.2.10)
git rebase upstream/main                                           # 37 条重放
```

备份件：`~/strata166/backup/strata-all-refs-20261104.bundle` + 6 个 `pre-rebase/*` 分支。

### 2.2 三处冲突，逐条怎么解的

| 提交 | 文件 | 情况 | 解法 |
|---|---|---|---|
| `901e6b0a`（0.2.8 补丁重放到 0.2.9） | `arch_defaults.hpp` | 两边在同一位置各加一个声明 | **两边都留**（上游的 `gfx12_prefill_share_default` 两条 + 我们的 `gfx906_tuned_env`） |
| 同上 | `qsa_select.cu` | 上游已完整实现我们的 W842（`SIMT=2` + 社区调优 + `alt_min_tokens`） | **取上游**（我们那条是 #3073 的本地移植，已被超越） |
| `705e09f7`（trace 打点） | `generate.cpp` | 上游在打点处插入了 `STRATA_MTP_ROOM_MIN` 一大段 | **保留上游整块**，把 `tr("previous commit joined")` 放在它前面 |
| `d963c791`（`/data/strata-spec` 阶梯） | `generate.cpp` | 上游重构为 `S / S_mtp_wide / S_mtp_narrow / S_mtp / S_look` 并加 `--draft auto` | 保留上游结构，把 `/data/strata-spec` 的读取**提到派生值之前**（否则 `S_mtp_wide` 等仍按旧 `S` 算） |

结果：`git rev-list --left-right --count upstream/main...HEAD` = **0 / 37**，全树无冲突标记，`gfx906_tuned_env` 的 7 项表完整。

### 2.3 一个意外收获：本地补丁债归零

| 我们手工移植/验证过的上游提交 | 是否已在 `upstream/main` |
|---|---|
| `e1b27d54` fatal GPU 自退（R77） | **是** |
| `5a13c34f` PLE 提限（R78） | **是** |
| `243fdb21` serve stop bound（R68） | **是** |
| `ed76b12f` penalty 窗口（R69） | **是** |
| `fbf6e1c7` `PF_GROUP_SCRATCH`（R66） | **是** |
| `af6ba4c6` dispatch counters | **是** |

⇒ 0.2.10 的树里这些逻辑**原生就有**（`generate.cpp` 7 处 fatal、`server.py` 3 处 `_raise_if_fatal_gpu`、`ngram.cpp` 3 处 getrlimit），**work/r77 那棵手工补丁树不再需要**。

### 2.4 分支：按业内做法处理

| 分支 | 处置 |
|---|---|
| `gfx906/mi50` | rebase 到 v0.2.10，**已 `push --force-with-lease`** |
| `r54-port` / `exp/R55-swizzle` / `bench-mi50-32gb-262k` / `w863-main` | 结论已出（DONE_NEG / 记录 / 临时指针）⇒ 打 `archive/*` tag **保留全部提交**，删除分支与 worktree（**不 rebase**：为已否定的实验解冲突没有价值，反而制造假历史） |
| `main` | 快进到 `origin/main`（镜像上游侧，业内做法：main 不放工作） |
| `rebase-trial`（临时） | 完成后删除 |

推送：

```
+ d963c791...5f73cd15 gfx906/mi50 -> gfx906/mi50 (forced update)
* [new tag] mi50-0.2.10-r28 / archive/r54-port / archive/exp-R55-swizzle / ...
远端 refs/heads/gfx906/mi50 = 5f73cd153b92…（与本地 HEAD 一致）
```

---

## 三、容器跟主线

### 3.1 为什么不是重新 `FROM mixa3607`

先按老 Dockerfile 的路子写了一份全新 Dockerfile，**构建期没有外网**：`pip install numpy` 直接 `No matching distribution found`（apt 那一步能过，pip 到 tuna 不通）。

⇒ 改为 **`FROM strata-gfx906:0.2.9-101`**，只替换 `/src`。这样 ROCm、clang、python 依赖逐字节不变，**变的正是「容器跟主线」要变的那部分**（源码 + `serve/*.py` + docker wrapper）。

```
strata-gfx906:0.2.10-101  (sha256 5267df6d…)
  /src = rebase 后的树（266 MB，含 third_party/llama.cpp）
  /src/BUILD-IMAGE.json = {source, commits_on_top:37, engine:0.1.56, rebase_date}
```

### 3.2 引擎与容器分开走

`/data` 是 bind mount ⇒ **引擎不在镜像里**。所以：

| 层 | 交付方式 |
|---|---|
| 引擎 0.1.56 | `ci/strata-ci deploy --src build-r28 --exe strata-0.1.56 --apply`（tag 门禁 + 7 步 + 账本）|
| `/src` | 新镜像 `strata-gfx906:0.2.10-101` |
| 容器 | 按 `docker inspect` 逐字复现参数重建，旧容器改名 `strata166-407.pre-210` 保留回滚 |

重建参数（从 inspect 生成，不是手抄）：`--restart unless-stopped`、`-v /models:/models:ro`、`-v …/data:/data`、`--device /dev/kfd --device /dev/dri`、`-p 8090:8090`、`--ulimit memlock=-1:-1`、`--group-add video`、`--security-opt label=disable`、`--ipc host`、`--shm-size 67108864`、`--workdir /src`、Cmd `bash -lc 'cd /src && exec python3 serve/server.py …'`。

### 3.3 三方对齐（验收）

| 项 | 值 |
|---|---|
| `/src/CMakeLists.txt` | `project(strata VERSION 0.1.56)` |
| `/src/serve/server.py` | `ecf3cfc5…`（0.2.10 原生，含 `_raise_if_fatal_gpu` 3 处） |
| 运行中引擎 | `ae085365…` = `/data/bin/strata-0.1.56` = `build-r28/strata` |
| git | `5f73cd15`，tag `mi50-0.2.10-r28`，落后 0 / 领先 37 |
| 账本末条 | 2026-11-04T12:38:24 `strata-0.1.56` `ae085365` tag **`mi50-0.2.10-r28`** git_head `5f73cd15` |

⇒ **provenance 断裂已修复**：账本末条的 tag 与 HEAD 的 tag 现在一致（R80 要检查的正是这一条）。

---

## 四、性能与行为

| 指标 | 0.1.55w（0.2.9） | **0.1.56（0.2.10）** | Δ |
|---|---|---|---|
| prefill 6.3K（n=9） | 8.868 s | **8.810 / 8.814 s**（两次） | **−0.6%**（CV 1.3%） |
| decode 稳态（rep6–9） | 79.44 tok/s | **84.6 / 85.2 / 77.7 / 82.9**（中位 ~83.7） | **+5%** |
| 官方 bench（`strata-ci bench --n 12`） | — | **73.49 tok/s**，CV 1.84% | 记录在 `state/runs/20261104T125356-r28-0.2.10-decode.json` |
| 显存布局 | cache 7463 槽 / borrows 2606 / PLE 26.82 GiB | **完全相同** | — |
| **窗口宽度** | `window up to 6 tokens` | **`window up to 12 tokens`** | **0.2.10 的行为变化，需评估** |

prefill 没有回退，decode 变快（与 `window up to 12` 一致：每个 verify 窗口承载更多 token）。

启动 243 s（历史区间 230–275 s），`restarts=0`，无 warning/error。

---

## 五、遗留与风险

1. **`window up to 12` 是新行为**，未单独测过长度分布下的接受率；已立 **R81**。
2. **R79**（自动重启后多轮会话是否完好）仍 OPEN —— 本轮换了引擎+容器，正好是它的场景。
3. **R80**（gate 加 provenance 三项检查）仍 OPEN；本轮把账本补到「tag == HEAD tag」，但**检查代码还没写**，下次绕过仍靠人看。
4. `ci/config.sh` 已改为 `BUILD=build-r28`、`IMG=strata-gfx906:0.2.10-101`；**旧的 `gfx029-build` 仍是 0.1.55 的构建目录**，保留不动（回滚与对照用）。
5. 旧容器 `strata166-407.pre-210`（0.2.9-101）保留；旧引擎 `strata-0.1.55w` 在 `/data/bin`，`ci/strata-ci rollback --exe strata-0.1.55w --apply` 可回。
6. 镜像基于 `0.2.9-101` 而不是直接 `FROM mixa3607`（构建期无外网），**lineage 里带了一层旧镜像**。要彻底干净，需要一次有外网的构建把 `FROM` 改回底座 —— 已写入 Dockerfile 注释。
