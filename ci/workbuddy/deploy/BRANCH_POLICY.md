# Strata 分支方针（166 / phoenixclyde / Niko1221 三者关系）

> 机主定于 2026-11-01 15:2x：**「后续 166 和 phoenixclyde 的 strata 和 niko 的 strata 的关系就按这个来。」**
> 本件是这条关系的唯一权威表述；以后任何分支动作按此执行，不再逐次确认。

---

## 1 三者关系（定死）

```
        Niko1221/Strata  ──────────  上游（upstream）
        （只读：fetch 只、push 永久禁用）
                 │
                 │  rebase / 对齐基底（只往下游拉，不往回推）
                 ▼
     phoenixclyde/Strata  ──────────  我们唯一的仓库（origin）
        （所有分支只建在这里、所有 commit 只落在这里）
                 │
                 │  git fetch / checkout
                 ▼
   166:/home/albus/strata166/pr/strata-fork  ──  测试台工作树（跟 origin 的分支走）
```

| 角色 | 仓库 | 权限 | 干什么 |
|---|---|---|---|
| 上游 | `Niko1221/Strata` | **只 fetch**（`remote.upstream.pushurl = DISABLED-no-push-to-upstream`，`ghup` 同） | 取新版本、作为我们分支的基底；**永不 push** |
| 我们 | `phoenixclyde/Strata` | 可 push | 分支只建这里、commit 只落这里 |
| 测试台 | `166:pr/strata-fork` | 工作树 | checkout origin 的某条分支，编引擎、跑 A/B |

## 2 五条操作规矩（按「下游厂商分支」标准，2026-11-01 15:5x 定）

1. **一条长期分支承载生产**：**`gfx906/mi50`**。**分支名不带版本号**——版本信息进 tag
   （`mi50-<上游版本>-r<N>`，如 `mi50-0.2.9-r1`）。生产只跑「发布 tag 对应的 HEAD」。
2. **对齐 = rebase 到 `upstream/main`**，不是 merge（merge 会出交叉历史，`git log upstream..ours` 就失效）。
   *当前不需要*：上游 main `c62d5e3a` = `v0.2.9`，我们分支的基底正是它（0 behind）。
3. **commit 只进 phoenixclyde**，一条都不进上游。要上行的改动只能另开 PR 由 Niko 合并（本仓不做）。
4. **166 的工作树必须等于 origin 某条分支 HEAD + 允许的未提交改动**；不允许长期游离。
   改了工作树 = 改生产资产（见 `AUDIT17_CLOSURE.md` 铁律 5），必须登记。
5. **补丁必须有台账**：`docs/DOWNSTREAM.md` 逐条列「改了什么 / 为什么 / 怎么验」，被上游吸收的立刻删；
   另存 `git format-patch` 导出（`166:w863/patches/`），rebase 撞车时手工重放。
6. **有两条线之后拆 stable / devel**：`devel` 跟新上游、跑验证；验过 `--ff-only` 快进到 `stable`，生产只跑 stable。
   （现在只有一条，够了；等要同时试两个上游版本时再拆。）

## 3 现状（2026-11-01 16:0x 现取，全历史已补全，数字可信）

**origin 只剩 4 条分支**（清理前 14 条，其余已归档成 `archive/*` tag）：

| 分支 | 本地 | origin | 相对上游 |
|---|---|---|---|
| **`gfx906/mi50`（主线）** | `df326f9e` | `df326f9e` | **落后 0 / 领先 5**；tag `mi50-0.2.9-r1`；生产引擎 0.1.55h 由它的代码编出 |
| `main` | `4441d55a` | `4441d55a` | 落后 0 / 领先 1（v0.2.9 + 我们的 docs） |
| `bench-mi50-32gb-262k` | `a0e9a96a` | `a0e9a96a` | 社区 benchmark 数据，留作成果 |
| `rc/0.1.30` | — | `8099fdb9` | 上游自己的 rc 镜像，与本项目无关 |

**已归档（tag 保留，分支已删）**：`archive/gfx906-0.2.9-mi50`、`archive/gfx906-0.2.8-mi50`、
`archive/gfx906-hipblaslt-vega20`、`archive/gfx906-mmq-plan-banner`、`archive/gfx906-routed-stream`、
`archive/amd-monitor-name-consistency`、`archive/amd-monitor-pcie-link`、`archive/gfx906-cpu-share-guard`、
`archive/web-sparkline-axis-floor`、`archive/gfx906-build-fixes-402`。
找回方式：`git checkout archive/<名字>`。它们的内容去向记在仓库的 `docs/DOWNSTREAM.md` 台账里。

**上游最新 = `v0.2.9`（tag → `c62d5e3a`，2026-10-31 发布）**，`main` 就停在它上面 —— 用 GitHub API 核过，不是猜的。

## 4 浅克隆问题（**已修**，2026-11-01 16:0x）

`git fetch --unshallow upstream` 已执行 ⇒ `is-shallow-repository` = **false**，可达提交 **4933**，`.git` 129 → 137 MB。
历史类判断（落后/领先、merge-base）现在可信。

修之前它造成过三个错，留在这里当规矩：

- `git merge-base a b` 直接 **报错**；
- `git rev-list --count` 把 **落后 3528 个提交** 算成「落后 1 个」——fork 的 `main` 实际停在 `v0.1.40.2`（10-07）；
- 在 `main` 上 `git rebase upstream/main` 会把它当**根提交整树重放** ⇒ 上千文件 `AA` 冲突（本轮真踩了，已 `--abort` 恢复）。

⇒ **规矩**：历史上不全时，任何「落后/领先几个提交」的结论必须用 **GitHub API** 或 `git rev-parse <tag>^{commit}` 交叉验证；
在浅克隆上**不要 rebase 老分支**，改用「从 upstream/main 起新分支 + cherry-pick 我们的提交」。

## 5 常用动作（可直接抄）

```bash
R=/home/albus/strata166/pr/strata-fork
# 看上游有没有新东西（不污染本地）
python3 albus/w863/gh_upstream.py        # 打 GitHub API：default branch head + tags + 最近提交

# 上游动了 -> 把主线 rebase 到最新（只在自己的仓库）
cd $R && git fetch upstream && git rebase upstream/main
git push --force-with-lease origin gfx906/0.2.9-mi50

# 确认推送边界（必须输出 DISABLED-no-push-to-upstream）
git config --get-all remote.upstream.pushurl
```
