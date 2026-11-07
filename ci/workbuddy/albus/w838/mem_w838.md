## W838　远端策略：上游只读（机主 2026-10-31 指示）

- **机主指令**：只在我们自己的 GitHub 库与 166 维护，**不要发 Strata 上游**。
- **核实（从未推过上游）**：`origin` = `git@github.com:phoenixclyde/Strata.git`；`upstream`/`ghup` 只做过 fetch；
  `refs/remotes` 下只有 `ghup/main`、`upstream/main`（只读引用）；push 记录 `923c2118..642de24f -> phoenixclyde/Strata`；
  `.bash_history` 无指向 Niko1221 的 push；**未开任何 PR**（`#3986`/`#4766` 作者是 MarcoTool / nfriedly，不是我们）。
- **加固两层**：
  1. `git remote set-url --push upstream|ghup DISABLED-no-push-to-upstream` —— 实测 `git push upstream` **rc=128**，
     在触网前就失败；
  2. `pr/strata-fork/.git/hooks/pre-push` 按 **URL** 只放行 `phoenixclyde/Strata` —— 实测上游 URL **rc=1 REFUSED**、
     我们 fork **rc=0**、ghup **rc=1**。
- **拉取不受影响**：`git fetch ghup main --depth=1` OK（`ghup/main` = `c62d5e3a`）、`git ls-remote upstream` OK、
  分支 `gfx906/0.2.8-mi50` @ `642de24f`，**ahead 8 / behind 0**。
- **踩坑**：第一版钩子把 `$1` 当 URL（git 传的是 **`$1`=remote 名、`$2`=URL**），导致连自己的 fork 也被拦；
  判断必须用 **URL**，否则换个 remote 名就能绕过。
- **将来若要发 PR**（需机主明确同意）：从 **fork** 开分支 + GitHub 网页开 PR，**永远不往上游 remote push**；
  若临时需要，用完立刻改回 `DISABLED`。
- 文档 `deploy/W838_REMOTE_POLICY.md`；登记 **P225（POLICY/ADOPTED）**，222 行。生产未动。
