# Downstream: gfx906 / MI50 维护说明

本仓是 [Niko1221/Strata](https://github.com/Niko1221/Strata) 的**下游厂商分支**：
我们跟随上游，但**不向上游提交 commit、不提 PR**。上游对本仓是只读的
（`remote.upstream.pushurl = DISABLED-no-push-to-upstream`）。

## 锚点

| 项 | 值 |
|---|---|
| 基于上游 | **v0.2.9** = `c62d5e3a15b40ea51c96aae9e8d36928965f53ab` |
| 长期分支 | `gfx906/mi50`（版本号不进分支名） |
| 发布 tag | `mi50-0.2.9-r1` |
| 生产引擎 | `strata-0.1.55h`（md5 `9a2ff8742f9918f657a468a7baeb177c`） |

## 下游补丁台账（rebase 时逐条重放；被上游吸收的就删掉）

| 序 | 内容 | 为什么 | 验证 |
|---|---|---|---|
| 1 | `gfx906: replay the 0.2.8 local patches onto v0.2.9` | 0.2.8 线上已验证的 gfx906 改动整体重放到 0.2.9 | 引擎起得来、48 层全 MMQ、decode 47 tok/s 量级 |
| 2 | `gfx906: rows-per-wavefront table for the Q8_0 wave kernel` | 单请求 decode 走投机验证窗口（ncols>1），wave kernel 每波只算 1 行，激活与 dp4a 不跨行共享 | 9 形状 × ncols 1/6 逐位 `diff=0`；同镜像 A/B **+4.0%** |

## 规矩

1. **只 fetch 上游，永不 push 上游**；分支与 commit 只在本仓。
2. **rebase，不 merge**：上游发新版就 `git rebase upstream/main`，保持薄补丁栈。
3. **分支名不带版本号**；版本信息进 tag（`mi50-<上游版本>-r<N>`）。
4. 补丁必须进上表；合并上游后逐条核对，能删的立刻删。
5. 二进制 / bench 副本 / `*.bak` **不进仓库**（放 `/home/albus/strata166/w863/`）。
6. 生产只跑「发布 tag 对应的 HEAD」；未打 tag 的提交不进生产。

## 跟随上游的操作

```bash
cd /home/albus/strata166/pr/strata-fork
git fetch upstream
git log --oneline upstream/main ^HEAD          # 看上游多了什么
git rebase upstream/main                       # 薄补丁栈整体上移
# 重新编 + 验证（见 deploy/W863_R23_DEPLOY.md 的 d11/d13/d14 脚本）
git tag -a mi50-<新版本>-r1 -m "..."
git push origin gfx906/mi50 --force-with-lease && git push origin --tags
```

## 已知限制

本 clone 是 **shallow**（`.git/shallow`），`git merge-base` / `rev-list --count` 的结论不可信。
判断「落后几个提交」一律用 GitHub API 或 `git rev-parse <tag>^{commit}` 交叉验证；
在浅克隆上**不要 rebase 老分支**，改用「从 upstream/main 起新分支 + cherry-pick」。
