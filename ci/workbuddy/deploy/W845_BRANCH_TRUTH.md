# W845 · 分支真相与 rebase 可行性（含对 W844 的更正）

> 2026-10-31 19:40–19:55。触发：机主三问 ——「你这是 rebase 成功了？」「下一次 rebase 可以做吗？」「现在在分支顶端吗？」
> 以及「镜像未重建这个要做吗？」
> **本轮的结论有两条推翻了我自己 W844 的说法**，逐条给了原始证据。

---

## 0 三问三答（结论先行）

| 问 | 答 | 证据 |
|---|---|---|
| **是 rebase 吗？** | **不是。** W844 那次是 `git worktree add v0.2.9` + 手工重放 12 个补丁文件；而且当时**一个都没提交** | 19:39 实测 `HEAD=c62d5e3 (tag: v0.2.9, upstream/main)` + `ahead/behind vs v0.2.9 = 0/0` + 12 个文件全是 ` M`（未暂存） |
| **下次能 rebase 吗？** | **能，而且现在就能跑。** 上一轮「做不了」是**浅克隆伪影**，不是分支事实 | `git fetch --unshallow upstream` → `is-shallow=false`，`.git` 58M→109M，`HEAD` 可达 **4930** 个提交；`git rebase upstream/main` 实跑输出 `Current branch gfx906/0.2.9-mi50 is up to date.` |
| **在分支顶端吗？** | **现在在。** 此前不在（等于没上去） | `gfx906/0.2.9-mi50 @ aef9d256`，`ahead upstream/main = 1`，工作区 **0 dirty**，`origin/gfx906/0.2.9-mi50 = aef9d256`（0/0） |

---

## 1 W844 到底做了什么（按现场还原）

1. `git fetch upstream --tags --depth=1` → 得到 tag `v0.2.9`（注解 tag `d94bac6` → commit `c62d5e3a`）。
2. `git worktree add -B gfx906/0.2.9-mi50 ~/strata166/gfx029 v0.2.9` → 新工作副本，分支指向 `c62d5e3a`。
3. 从旧副本复制 10 个文件 + 打 `generate.cpp` 锚点 + 打 `CMakeLists` 三锚点 → **工作区改动，未提交**。
4. 树外构建 `gfx029-build/` → `strata-0.1.55g`，md5 `29b15bb4…`；门禁 17 项 PASS；三臂 A/B 中性；落产。

**关键缺陷**：第 3 步之后没有 commit。所以分支 HEAD 一直是 `c62d5e3a`——
`git log --oneline` 只有上游那一条，`ahead/behind = 0/0`。
也就是说**"分支落到了 v0.2.9"这句话只对了一半：树是 0.2.9+补丁，历史里没有我们的东西。**

---

## 2 更正一：旧分支本来就是 v0.2.9 树，所谓「没有共同祖先」是浅克隆伪影

W844 写的是：*"`gfx906` 是 depth-1 浅克隆，与上游没有共同祖先 ⇒ `git rebase` 无对象"*。
前半句对，**结论错**：

| 检查（unshallow 之后，19:48） | 结果 |
|---|---|
| `git merge-base gfx906/0.2.8-mi50 upstream/main` | **`c62d5e3a`**（非空） |
| `git rev-list --count gfx906/0.2.8-mi50` | **4940** 个提交（浅克隆时只看到 6 个） |
| `git cat-file -e gfx906/0.2.8-mi50:serve/replicas.py` | **存在** —— 该文件只在 0.2.9 有 ⇒ **旧分支的树就是 v0.2.9** |
| `git diff --stat v0.2.9 gfx906/0.2.8-mi50` | **12 files, +265 −11**（正是我们那 12 个补丁） |

⇒ 旧分支 = **v0.2.9 的提交 + 11 个补丁提交**，一直如此。
`git rebase` 当时失败的唯一原因是**本地对象库不连通**（`merge-base` 空），而修法是一条命令
`git fetch --unshallow upstream`，**不是** worktree + 重放。

**所以 W844 的重放工作是重复劳动**。它没有害处（结果与旧分支逐文件一致），但它把
"分支历史不连通"误读成了"分支与上游无关"，这个误读会让后面所有关于 rebase 的判断都失效。

补充一条区别（不是零差异）：新分支比旧分支多 **2 行注释**，全在 `src/program/generate.cpp`
的 `W839_TRACE` 段落（锚点补丁器 `apply_w839_generate.py` 的当前版本会带这两行注释）：

```
+        // STRATA_W839_TRACE=1 prints the device probe, which is how "the call never ran" was told apart
+        // from "it ran and set nothing".
```

其余 11 个文件 `git show <branch>:<file> | md5sum` **逐一相等**（见 §6 校验表）。

---

## 3 更正二：门禁的 PROVENANCE 一度被我改成了自证

W844 为了"让门禁按原路径找到产物"，做了两件事：

```
ln -sfn gfx029-build  gfx029/build-029g
cp -f  gfx029-build/strata-0.1.55g  gfx029/strata     # ← 问题在这里
```

门禁第 100 行原本是 `find "$TREE" -maxdepth 2 -name strata -type f`，然后 grep 部署 md5。
把一个**部署副本**放进树里，等于让"部署产物 == 树里产物"这句话恒真 —— **PROVENANCE 变成自证**。
这比漏检更糟：它会让人相信一个没被验证过的等式。

**已修**（两处，都可复核）：

1. `rm gfx029/strata`（树里现在只有上游自带的 `bin/strata` 包装脚本，5756 B，git 跟踪）。
2. 门禁改成跟随符号链接：`find -L "$TREE" -maxdepth 3 -name strata -type f`
   —— 通过 `build-029g -> gfx029-build` 比对**真正的 ninja 产物** `gfx029-build/strata`。
   原脚本备份在 `verify_patches.sh.bak_w845`。

修完复跑：**GATE PASS（17 项）**，`PROVENANCE deployed binary matches a build artifact … OK`
（这次是真的：`gfx029-build/strata` == `/data/bin/strata-0.1.55g` == `29b15bb4…`）。

---

## 4 更正三：镜像重建的成本被我说大了（分层可查）

W844 写的是「完整 0.2.9 还需重建镜像（约 40 min 全量回归）」——**没核过**。实际：

| 事实 | 值 | 含义 |
|---|---|---|
| 镜像 | `strata-gfx906:0.2.8p2`，**6.97 GB** | 大头是 ROCm/终端层 |
| 那层的年龄 | `docker history` 里 ROCm/`RUN rm -rf /src/build…` 层是 **6 days ago** | 基础层可全部复用 |
| serve 层 | `COPY serve /src/serve` = **4.43 MB** | 只这一层随 serve 变 |
| Dockerfile | `src028/Dockerfile` 三 stage：`engine-build`（第 24 行）、`terminal`（70）、runtime（92）；`engine-build` 里 `COPY . .`（30 行） | **从源码重建才会重编引擎** |
| 引擎是否依赖镜像里的库 | `ldd /data/bin/strata-0.1.55g` 只有 **ROCm + libc/libstdc++**，无 `/src` 产物 | 只换引擎二进制是安全的 |

⇒ 若要 serve 0.2.9，**不需要重跑三 stage**，一条叠层就够：

```
FROM strata-gfx906:0.2.8p2
COPY serve /src/serve
```
（秒级，不碰引擎编译层；代价只在新镜像 tag + 重建容器。）

---

## 5 镜像/serve 层要不要做：**现在不做**，但缺口是真的

### 5.1 现状是"引擎 0.1.55 + serve 0.2.8"的拼接

容器 `Cmd = cd /src && python3 serve/server.py …`，挂载只有 `/models`（ro）和 `/data`（rw）
⇒ **`/src` 是镜像内建的，不是宿主挂载**。所以跑的 serve 就是镜像里那份 0.2.8：

| 位置 | `serve/server.py` md5 | `COALESCE_PREFILL` | `PAR_COUNTERS` |
|---|---|---|---|
| 容器 `/src/serve/server.py`（0.2.8） | `abf8634e…` | **0** | **0** |
| 宿主 `gfx029/serve/server.py`（0.2.9 原文） | `b1aa1d36…` | **10** | **3** |

### 5.2 缺口有实际内容，不是"版本号落后"而已

v0.2.8→v0.2.9 的 serve 改动：`server.py +263/−9`、`replicas.py +162`（新文件）、`frontend.py +40/−11`、`setup.py +303/−38`。
其中 **`COALESCE_PREFILL`（PAR-H）是唯一有性能含义的一块**：把多个等待中请求的 prompt 合成**一次 layer-major 读**，
专家只流一遍、大家共用。

而**引擎侧已经就绪**——0.1.55 的 `src/program/generate.cpp` 里有 `BCO …`（13559）与 `BCOK …`（15261）。
所以现在是"引擎会、serve 不会"，能力被**卡在 serve 层**。

但它是否对我们有价值，取决于并发：

- 触发条件在 serve 源码里写死：需要 `--batch`，且统计窗口内至少 `COALESCE_MIN_REQS=3` 个请求在 `COALESCE_BURST_MS=250` 内到达；
- 我们的负载是**单用户串行**（mt_read/mt_gen 一次一条），运行日志里 `BCOK` 命中 **0**。
- `replicas.py` 只在多引擎副本时有用；`PAR_COUNTERS` 是研究用队列计数；`frontend.py` 是 UI。

### 5.3 判词

**不做。** 收益 0（单流不触发），风险非 0（换容器 = 重建 `/src`，要重放 telemetry/app.css/app.js 三个补丁、重跑冒烟与三臂基线）。
已登记为 `PROGRESS.tsv` 的 **X13**，**触发条件写死**：要跑 `--batch` / 并发 ≥3 / 多副本，或要用队列计数时再叠层。

### 5.4 但要记住这个偏差（新的判定纪律）

**树里 ≠ 跑着的**，至少在 serve 层：宿主 `gfx029/serve/server.py` 是 0.2.9，容器里跑的是 0.2.8。
今后任何"serve 侧行为"的结论都不能拿树里的文件当证据；只有 `docker exec … md5sum /src/serve/…` 算数。
引擎侧没有这个问题（二进制从 `/data/bin` 挂载，md5 可对）。

---

## 6 现在能不能 rebase（可复核的六项）

| 检查 | 值 |
|---|---|
| `git rev-parse --is-shallow-repository` | **false**（`.git/shallow` 已不存在） |
| `.git` 体积 | 58 M → **109 M** |
| `git rev-list --count HEAD` | **4930**（浅克隆时链断在 `c62d5e3`） |
| `git rev-list --parents -1 v0.2.9` | `c62d5e3a… 7aa9a58…`（有父提交了，不再是 `grafted`） |
| `git merge-base HEAD upstream/main` | **`c62d5e3a`** |
| `git rebase upstream/main` | `Current branch gfx906/0.2.9-mi50 is up to date.`（真跑了，no-op） |

**结论**：`git rebase` 的机器前提（历史连通 + merge-base 可算）现在全部满足。上游前进后直接 `git rebase upstream/main` 就会把我们的 1 个提交重放到新上游上。

### 6.1 下次的常规动作

```
# 一条命令（已固化）
bash ~/strata166/tmp/rebase_gfx906.sh            # 默认 upstream/main
```
脚本做的三件事：`fetch --tags` → 浅克隆就报错退出并提示 `--unshallow` → 有 merge-base 就 `git rebase`。

### 6.2 冲突风险面（按 0.2.9 的实际改动预测）

上游 0.2.9 动过、同时我们也改过的文件：

| 文件 | 上游 0.2.9 改动 | 我们的改动 | 冲突风险 |
|---|---|---|---|
| `src/program/generate.cpp` | **+261 / −7** | +29（W839 入口 + 注释） | **高**（锚点上下文会变） |
| `src/core/arch_defaults.cpp` | +26 / −0 | +68 | **中**（同文件两处独立改动） |
| `CMakeLists.txt` | +29 / −1 | +19 | **中**（W793a/W793b/W776 三锚点） |
| `src/kernels/cuda/qsa_select.cu` | 未动 | +24（W842） | 无 |
| `src/kernels/cuda/qsa_decode_attn.cu` | 未动 | +14 | 无 |
| `serve/telemetry.py`、`serve/web/app.*` | 未动（0.2.9 动的是 `frontend.py`） | +64 | 无 |

⇒ 真到冲突那天，**先看 `generate.cpp` 的锚点补丁**：它按上下文串匹配，上游一动注释就可能失配。
处理顺序：`git rebase` → 冲突时手工保留两侧 → 重跑 `apply_w839_generate.py` 断言 → 重建 → 门禁。

---

## 7 顺带纠正一处文档失真（与本次无关但同属"看起来对"）

运行配置的 `--pack` 是 **`/data/packs/ud-q4_k_xl`**、`--native` 是
`Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf`，`/health` 回报
`model = qwen3.8-flash-next-ud-q4_k_xl-abliterated`。
也就是说**生产模型是 UD-Q4_K_XL，不是 UD-IQ4_XS**；配置文件名叫
`strata-huihui-ud-iq4_xs.json` 只是历史遗留命名。
此前多份文档（含长期记忆）写"iq4_xs"，是照文件名抄的。已改。

---

## 8 本轮落产：**0**（生产未动）

| 项 | 值 |
|---|---|
| 引擎 | `/data/bin/strata-0.1.55g`（未变），md5 `29b15bb4418bf15a98c22ec565f2447b` |
| args / env / 镜像 | 33 / 6 / `strata-gfx906:0.2.8p2`（未变） |
| 容器 | `strata166-407`，started `2026-10-31T11:29:55Z`，**restarts=0** |
| 运行时 | `slots=7463`、`vram_free=920 MiB`、`pcie_frac=0.20` |
| 门禁 | **PASS（17 项）**，PROVENANCE 走真产物 |
| 启动横幅 | `engine 0.1.55`；`MI50-class` 两行在（2 exact + 7 rounding） |

本轮对生产的**唯一**改动是把 `verify_patches.sh` 的 PROVENANCE 判定收紧（脚本，不是运行时）。

## 9 产物出处凭据（供以后对账）

```
commit  aef9d256
tree    4ce087ba3ac2969ecf8eabd62b2a4f1c3e1be5d0
binary  29b15bb4418bf15a98c22ec565f2447b   (= gfx029-build/strata-0.1.55g = /data/bin/strata-0.1.55g)
built   2026-10-31 19:06（构建早于提交，但 12 个文件自构建起未再改动：git diff HEAD = 0 行）
remote  origin/gfx906/0.2.9-mi50 = aef9d256（0/0，与本地一致）
```
