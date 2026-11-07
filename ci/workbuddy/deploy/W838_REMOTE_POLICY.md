# W838　远端策略：上游只读，只推我们自己的库

> 机主 2026-10-31 明确：**"我们就在 166 和咱们 GitHub 自己的库维护就行了，不要发 strata 上游。"**
> 本文是这个决定的落地点，也是 `pr/strata-fork/.git/hooks/pre-push` 里引用的那份文件。

---

## 1 结论

| 远端 | 用途 | push |
|---|---|---|
| `origin` = `git@github.com:phoenixclyde/Strata.git` | **我们自己的库**，唯一接收写入的地方 | ✅ 允许 |
| `upstream` = `git@github.com:Niko1221/Strata.git` | 只用来**跟上游** | ❌ **禁止**（push URL 已置为 `DISABLED-no-push-to-upstream`） |
| `ghup` = `https://gh-proxy.com/.../Niko1221/Strata.git` | 同上，走代理拉取（SSH 慢时用） | ❌ **禁止**（同上） |

**不开 PR、不提 issue、不向上游写任何东西。** 需要让上游知道的事，先记录在本仓库文档里，等机主明确指示再动。

## 2 为什么加这层锁（不是因为我推过）

已核实**没有**向上游推送过：

| 检查 | 结果 |
|---|---|
| `git remote -v` | `origin` 是 `phoenixclyde/Strata`；`upstream`/`ghup` 只做过 fetch |
| `refs/remotes/` | 只有 `ghup/main`、`upstream/main`（fetch 得到的只读引用）+ `origin/gfx906/0.2.8-mi50`（我们推的） |
| push 记录 | `923c2118..642de24f  gfx906/0.2.8-mi50 -> gfx906/0.2.8-mi50`，目标是 `github.com:phoenixclyde/Strata.git` |
| `.bash_history` | 没有任何指向 Niko1221/Strata 的 push 行 |
| PR | 未开任何 PR（`#3986`/`#4766` 的作者是 MarcoTool / nfriedly，不是我们） |

加锁的理由是**原来两个上游 remote 都带着 push 地址**——虽然 gh-proxy 不支持 push、SSH 大概率无权限，
但"碰巧推不上去"不能当保障。养成结构性禁止，比事后解释可靠。

## 3 两层防护

**第一层：push URL 置为无效地址**

```bash
git remote set-url --push upstream DISABLED-no-push-to-upstream
git remote set-url --push ghup     DISABLED-no-push-to-upstream
```

实测：`git push upstream ...` → `rc=128, fatal: 'DISABLED-no-push-to-upstream' does not appear to be a git repository`
（**在触网之前**就失败，所以不可能误伤上游）。

**第二层：`pre-push` 钩子**（`pr/strata-fork/.git/hooks/pre-push`）

按**URL**判断（不按 remote 名，因为 remote 可以改名），只放行 `phoenixclyde/Strata`：

```sh
name="$1"; url="$2"          # git 传的是 $1=remote 名, $2=URL
case "$url" in
  *phoenixclyde/Strata*|*phoenixclyde/strata*) exit 0 ;;
esac
echo "pre-push: REFUSED ..." >&2; exit 1
```

实测（按 git 真实参数顺序）：

| 调用 | 结果 |
|---|---|
| `pre-push origin git@github.com:Niko1221/Strata.git` | **rc=1 REFUSED** |
| `pre-push ghup https://gh-proxy.com/.../Niko1221/Strata.git` | **rc=1 REFUSED** |
| `pre-push origin git@github.com:phoenixclyde/Strata.git` | rc=0（安静通过） |
| `git push --dry-run origin gfx906/0.2.8-mi50` | rc=0，`Everything up-to-date` |
| `git push --dry-run upstream gfx906/0.2.8-mi50` | rc=128 |

⚠️ **踩过的坑**：我第一版钩子只判断 `$1`，把 remote 名当成了 URL，结果连我们自己的 fork 都被拦了。
git 的 pre-push 参数是 `$1 = remote 名`、`$2 = URL`；而且判断必须用 **URL**，否则换个 remote 名就能绕过。

## 4 拉取上游仍然正常（这层不能锁死）

策略是"只读"，不是"断开"。实测：

- `git fetch ghup main --depth=1` → 成功，`ghup/main = c62d5e3a`
- `git ls-remote upstream` → 成功，`c62d5e3a... refs/heads/main`
- 分支完好：`gfx906/0.2.8-mi50` @ `642de24f`，**ahead 8 / behind 0**
  > **【B6 · AUDIT21】以上是 2026-10-31 的快照。** 现分支为 `gfx906/mi50` @ `d963c791`，**领先 37**；
  > `gfx906/0.2.8-mi50` 只留在旧检出 `~/strata166/gfx906` 里，`pr/strata-fork` 已无此分支。

## 5 如果将来机主改主意要发 PR

不要直接推。按这个顺序：

1. 机主明确同意，并指定**发哪个补丁**（我们的 8 个 commit 是一个补丁一个，可以单独摘；**【B6 · AUDIT21】现为 37 个提交，但真正改引擎的仍是 3 条：`901e6b0a` / `f8bfcd6d` / 注释一条** —— 见 `W865 §1`）；
2. 先查上游是否已有同题 PR（已知：`#3986` / `#4766` 都在修 dflash2 的 gfx906 构建 = 我们的 W776）；
3. 在**我们的 fork** 上开分支（`git push origin <branch>`），用 GitHub 网页从 fork 开 PR——**永远不要往上游 remote push**；
4. 若确实需要给上游 remote 写权限，那是**一次性**动作，用完立刻把 push URL 改回 `DISABLED-no-push-to-upstream`。

## 6 同步维护在哪里

| 位置 | 角色 |
|---|---|
| `166:/home/albus/strata166/pr/strata-fork` | **源码真相源 + 推送仓**（`gfx906/mi50` @ `d963c791`，2026-11-02 现场） |
| `166:/home/albus/strata166/gfx029-build` | **现役构建树**（0.2.9；`src028` 仍在但属 0.2.8） |
| ~~`166:/home/albus/strata166/gfx906`~~ | **【B1 更正 · AUDIT21】已是旧检出**：`gfx906/0.2.8-mi50` @ `cc8a0711`，**不再是真相源**（原文写「源码真相源」，是 0.2.8 时代的事实） |
| ~~`166:/home/albus/strata166/src028`~~ | **【B1 更正 · AUDIT21】旧构建树**（0.2.8），已被 `gfx029-build` 取代 |
| `166:/home/albus/strata166/pr/strata-fork` | 推送用的工作仓库（带上面的 pre-push 钩子） |
| GitHub `phoenixclyde/Strata` | 远端备份与分享 |
