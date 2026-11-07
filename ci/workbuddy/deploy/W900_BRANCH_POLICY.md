# W900 · 源码变更的分支纪律（2026-11-02 定）

> 触发：R54 要改源码，问「是否要在当前分支再分支、业内怎么做」。本节只写**可执行规则**，
> 依据是 GitHub Flow / trunk-based / Git Flow 的公开定义与 `git-worktree` 官方文档（见 §4）。

---

## 1 一句话

**要再开分支，而且已经开了**：`r54-port` 从部署分支 `gfx906/mi50`（`d963c791`）切出，
放在独立 worktree `/home/albus/strata166/work/r54`。
**部署分支本身永不直接提交**——它被 tag `mi50-0.2.9-r27` 和镜像 `strata-gfx906:0.2.9-101` 引用，是我们的生产资产。

## 2 为什么是「再开一个分支 + worktree」

| 需求 | 做法 | 依据 |
|---|---|---|
| 改动不污染生产分支 | 从部署分支切 `exp/*` 主题分支 | GitHub Flow：main 永远可发布，改动走短命分支 |
| 不改动主工作树（生产资产） | `git worktree add -b <branch> <path> HEAD` | `git-worktree` 官方文档：一个分支同时只能被一个 worktree 检出；worktree 共享 `.git`，比克隆省磁盘 |
| 实验可丢弃 | 分支短命；失败直接删分支，结论留在 W 号文档 | trunk-based：分支按小时/天计，不按周 |
| 合并可控 | 过本项目的闸门（plan_lint / ledger / audit_recheck）+ A/B 后才合回部署分支并重打 tag | GitHub Flow 的「PR + 必过检查」在本项目的等价物 |

**为什么不直接在主树改**：本项目 `铁律` 里写着「改工作树 = 改生产资产」。主树 `/home/albus/strata166/pr/strata-fork`
就是镜像与二进制的来源；在上面改一个 `#include` 都可能让下一次重建带上未验证的代码。

## 3 项目内规则（从今天起照此办）

1. **分支名**：`exp/R<号>-<一句话>`（例：`exp/r54-megakernel`）；纯文档轮次不需要分支。
2. **基线**：一律从**部署分支的当前 HEAD** 切；切之前 `git status --porcelain` 必须为空。
3. **隔离**：用 worktree，不 clone 第二份；路径固定 `/home/albus/strata166/work/<分支短名>`。
4. **合并门**：`plan_lint PASS` + `ledger 欠账 0` + `audit_recheck 全 PASS` + 该条目的 A/B 判据（`|Δ| ≥ 2×CV`；
   decode 侧只守不劣化）**四项全过**，才 squash 合回部署分支。
5. **合回后**：重打 tag（`mi50-0.2.9-rNN`）、重建镜像、更新 `PROGRESS` 与 `SESSION_STATE`；
   分支保留 7 天再删（便于取证）。
6. **禁止**：在部署分支直接提交；`push --force`；`--no-verify`；把 `third_party/` 的 vendored 改动
   混进业务分支（那类改动单开 `vendor/*` 分支或落 patch 文件）。
7. **实验失败**：删分支即可，**但结论必须留在 `deploy/W*.md` 与 `PROGRESS`**（分支是过程，文档是资产）。

## 4 依据（公开资料）

- GitHub Flow：main 永远可部署，任何改动从 main 切短命分支、开 PR、过检查、合并即部署
  （多数团队默认；分支寿命「小时到天」）。
- Trunk-Based：分支 <1 天 + feature flag，Google/Meta/Netflix 系；要求强 CI。
- Git Flow：main/develop/release/hotfix，适合有发布列车与多版本并存的产品——**不适合我们**（单一生产分支）。
- `git worktree`：同一仓库多工作树，共享对象库；**同一分支不能被两个 worktree 同时检出**；
  用完 `git worktree remove` / `prune`，不要直接 `rm -rf`。

## 5 当前状态（本轮实做）

```
$ git -C ~/strata166/pr/strata-fork worktree list
/home/albus/strata166/pr/strata-fork   d963c791 [gfx906/mi50]      # 部署分支，干净
/home/albus/strata166/work/r54         d963c791 [r54-port]         # R54 实验分支
```

R54 的三个文件只存在于 `work/r54`，主树 `git status` 仍为空，生产二进制与 config 未变。
