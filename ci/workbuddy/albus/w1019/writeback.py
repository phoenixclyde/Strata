import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1019（rebase 了 / 所有分支 rebase 了 / 镜像和容器确实没跟，机制查清了）

**1. rebase 做了（上轮是 merge，不是 rebase）。** 机主问得对：上一轮 `e21b1b01` 是 `--no-ff` 合并，
历史里留了一个 merge commit。本轮改成 rebase：

```
git rebase upstream/main          # 64 个提交重放，0 冲突
behind=0  ahead=64  merges=0      # 线性
git push --force-with-lease       # 85297483 → 22abb0c0
tag  mi50-0.2.11-r33-2
备份 branch backup/pre-rebase-w1019 + tag pre-rebase-w1019
```

**2. 所有分支 rebase。** 逐个查了分叉，只 rebase **活**分支；`pre-rebase/*` 与 `backup/*` 是带日期的存档，
rebase 它们等于毁掉它们存在的理由（这一条写进本节，免得下次有人"顺手"把存档也 rebase 了）。

| 分支 | 之前 | 之后 | 说明 |
|---|---|---|---|
| `gfx906/mi50` | ahead 63 / behind 208 | **ahead 64 / behind 0** | 64 提交重放，线性 |
| `main` | ahead 3 / behind **916** | **ahead 3 / behind 0** | 已 force-push |
| `exp/R90-080`（独立 worktree `work/r90-080`） | ahead 41 / behind 208 | **ahead 0 / behind 0** | 它最后那条 `R90: print the J` 早已在主线（`c39e85ea`），重放时被 git 判为已应用 ⇒ 分支现与主线同一 tip；41 条旧提交留在 `backup/pre-rebase-expR90` |
| `pre-rebase/*`（7 条）、`backup/*`（2 条） | — | **不动** | 名字即用途：存档 |

顺带一条判据：`exp/R90-080` 第一次 rebase 到 `upstream/main` 后 pre-push **被拒**——那个分支上没有 `ci/round_gate.py`
（门只在 `gfx906/mi50` 上），hook 正确地拒绝了"没有门的树"。所以实验分支的正确做法是 rebase 到**主线**而不是裸上游：
主线本身 behind 0，等价于上游，但带着门。

**3. 镜像和容器确实没跟，机制第一次查清。**

- 镜像 `strata-gfx906:0.2.10-101` 里 **`/src` 是 v0.2.10 的树**（`serve/server.py` md5 `ecf3cfc5…`）；
- 生产容器 `4f387a12e84b` 只挂 **`/data`** 与 **`/models`**，**不挂 repo** ⇒ 运行中的 HTTP 层（`serve/server.py`，
  上游这 208 个提交里改了 16 次）和 `/src/data/*` 都来自镜像；
- **引擎二进制不在镜像里**（`Dockerfile-0.2.10` 头注释逐字："引擎二进制不放进镜像（/data 是 bind，引擎走 /data/bin 的版本文件 + ci 账本）"）
  ⇒ 跟上游要**两条腿**：镜像重做 + 引擎重编后走 `ci/deploy.sh`。
- `BUILD-IMAGE.json` 就是镜像的指纹指针（`source: rebase onto upstream v0.2.10 (ffa80d73)`, `commits_on_top: 37`, `engine 0.1.56`）——
  新镜像必须写一份新的，否则下一个人不知道这镜像里是哪棵树。
- `data/expert-profile.bin` 三处同一 md5 `ff1bc654…`（镜像 / repo / 运行中）⇒ 重建镜像不会动这个引擎输入。

**4. 全量重编试了一次，卡在 ggml 参考树。** 154 个 TU、8 并行：150 个通过，**4 个失败**，链接因此失败
（`mul_mat_q_case<(ggml_type)7/21/23>`、`ggml_compute_forward_mul_mat_tiled` 未定义）。真实错因是第一条：

```
clang++: error: no such file or directory: '/llama.cpp/ggml/src/ggml-cpu/iqp.cpp'
```

`build-r28` 的 `STRATA_GGML_DIR=/llama.cpp`，而本机三个 ref（`llama_b10700` / `b12099` / `b12110`）**都没有**
`ggml/src/ggml-cpu/iqp.cpp` ⇒ **v0.2.11 需要比 b12110 更新的 ggml**，而我们手上没有；运行时镜像里也没有 `/llama.cpp`
（`NO_LLAMA_CPP`），也没有构建用镜像（`docker images` 里只有 strata 运行时）。

**副作用（必须记）**：ninja 的链接行先 `cmake -E rm -f strata`，链接失败 ⇒ **`build-r28/strata` 现在不存在**。
生产不受影响（`/data/bin/strata-0.1.56-090` 是另一份，md5 `eea5ea37…` 未变），但在补齐 ggml 之前**不能 deploy**
（`deploy.sh` 读 `$BUILD/strata`，文件缺失会直接报错而不是装错东西）。

**5. 所以「镜像和容器跟上游」的准确代价**（下一步，未做）：

1. 取与 v0.2.11 配套的 llama.cpp（含 `ggml-cpu/iqp.cpp`），挂到 `/llama.cpp`；
2. 全量重编 154 TU（8 并行，上一轮 150/154 通过的那套流程，~5–8 分钟）；
3. `ci/deploy.sh`（gate → tag → identity → `cp .new` → `mv` → restart → verify），失败自动回滚；
4. 新镜像 `strata-gfx906:0.2.11-101`（`Dockerfile-0.2.11` 从 0.2.10 派生 + 新 `BUILD-IMAGE.json`）；
5. 引擎与镜像各自跑一遍 A/B（`cfg_apply` 与 `quant_quality` 相对门）才允许进生产。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1019" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
s = s.replace("树 = `v0.2.11-69-g85297483`", "树 = `mi50-0.2.11-r33-2`（rebase，线性，behind 0 / ahead 64）")
s = s.replace("| **主线 / 上游基线** | 树 = `mi50-0.2.11-r33-2`（rebase，线性，behind 0 / ahead 64）（上游 `9f7d977d`，208 提交已于 `e21b1b01` 零冲突并入）；**生产二进制未重编**，仍是 `0.1.56-090` | `git describe --tags`；`git rev-list --count upstream/main..HEAD` |",
              "| **主线 / 上游基线** | 树 = `mi50-0.2.11-r33-2`（rebase 到上游 `9f7d977d` / v0.2.11，线性，behind 0 / ahead 64）；**生产二进制未重编**，仍是 `0.1.56-090`；**镜像仍是 `0.2.10-101`（`/src` 为 v0.2.10 树）** | `git describe --tags`；`git rev-list --count upstream/main..HEAD`；`docker images` |")
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P340", "rebase 取代 merge：64 提交重放到 upstream v0.2.11，线性、0 冲突，force-push 到 `22abb0c0`", "W1019", "DONE",
  "**W1019 立**：`git rebase upstream/main` 重放 64 提交、0 冲突、`merges=0`，`behind=0 ahead=64`；`--force-with-lease` 推送 `85297483→22abb0c0`；"
  "备份 `backup/pre-rebase-w1019` + tag `pre-rebase-w1019`；新 tag `mi50-0.2.11-r33-2`。上轮的 `e21b1b01` 是 merge，历史里留了 merge commit。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1019"),
 ("B8工程", "P341", "所有活分支 rebase：`main`（behind 916）/`exp/R90-080`；存档分支不动；实验分支要 rebase 到主线而非裸上游", "W1019", "DONE",
  "**W1019 立**：`main` 3 提交（behind 916→0）、`exp/R90-080` 41 提交（其末条 `R90: print the J` 已在主线 `c39e85ea`，重放后与主线同 tip，41 条旧提交留 `backup/pre-rebase-expR90`）。"
  "`pre-rebase/*`(7) 与 `backup/*`(2) 不动（存档）。判据：实验分支 rebase 到**主线**——第一次 rebase 到裸上游后 pre-push 被拒，因为那个树没有 `ci/round_gate.py`。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1019"),
 ("B5本机缺口", "P342", "镜像不跟上游的机制：镜像内 `/src` 是 v0.2.10 树；容器只挂 `/data`、`/models`；引擎二进制在 `/data/bin`", "W1019", "DONE",
  "**W1019 立**：`strata-gfx906:0.2.10-101` 内 `serve/server.py` md5 `ecf3cfc5…`（v0.2.10），`BUILD-IMAGE.json` 记录 `rebase onto v0.2.10 (ffa80d73)`/37 提交；"
  "生产容器挂载只有 `/data`、`/models` ⇒ HTTP 层与 `/src/data` 全部来自镜像；`Dockerfile-0.2.10` 头注释写明引擎二进制不进镜像。`data/expert-profile.bin` 三处同 md5 `ff1bc654…`。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1019"),
 ("B5本机缺口", "P343", "全量重编卡在 ggml：三个 ref 都没有 `ggml-cpu/iqp.cpp`；且链接失败删掉了 `build-r28/strata`", "W1019", "OPEN",
  "**W1019 立**：154 TU / 8 并行 → 150 通过、4 失败，链接报 `mul_mat_q_case<7/21/23>` 与 `ggml_compute_forward_mul_mat_tiled` 未定义；真实错因 "
  "`no such file: /llama.cpp/ggml/src/ggml-cpu/iqp.cpp`（本机 b10700/b12099/b12110 均无）⇒ v0.2.11 需要更新的 ggml。运行时镜像无 `/llama.cpp`、无构建镜像。"
  "**副作用**：ninja 链接行先 `rm -f strata`，失败后 `build-r28/strata` 不存在（生产 `/data/bin` 未受影响，md5 `eea5ea37…`）。补齐 ggml 前不能 deploy。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1019"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
