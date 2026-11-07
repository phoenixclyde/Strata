import io, os
p = "/home/albus/strata166/pr/strata-fork/deploy/CI_CD_BLUEPRINT.md"
if not os.path.exists(p):
    raise SystemExit("blueprint missing")
s = io.open(p, encoding="utf-8").read()
add = """

## Fork 的 Actions 开关（W1029，实测）

`POST /repos/{owner}/{repo}/actions/workflows/{file}/dispatches` 返回
**422 `Actions has been disabled for this repository`**，而
`GET /repos/{owner}/{repo}/actions/permissions` 同时报 `enabled: true, allowed_actions: all` ——
这两句话可以同时为真：前者说的是**这个 fork 的 workflows 有没有被启用**，后者说的是**策略允许什么**。

四条要一起做，缺一条都不动：

1. **Settings → Actions → General → Allow all actions and reusable workflows**，然后**点这一节的 Save**。
   （只选中不 Save 等于没改；W1029 的截图就是这一页。）
2. **Actions 标签页**（`https://github.com/<owner>/<repo>/actions`）顶部的横幅
   *"Workflows aren't being run on this forked repository"* → 点
   **"I understand my workflows, go ahead and enable them"**。这一条在 Settings 里没有替代品。
3. **推一个新提交**。GitHub **不会回填**：开关关着的时候推上去的 sha 永远不会补跑，
   所以启用之后必须再推一次（空提交即可）。W1029 用 `git commit --allow-empty` 验过：
   `e4f0867d` 推到 origin 后 180 s 内仍无 run。
4. 若第 1 步的开关**改不动/自己变回去**，那是账号或组织策略，去 **Settings → Billing and plans** 看有没有 hold。

判据（一条命令）：`python3 ci/gh_gate.py --wait 300` —— 有 run 就给 `PASS` 或失败 URL，没有就 exit 6 并列出上面这几步。
`ci/deploy.sh` 第 0 步就是它，所以**开关没开 = 部署被拒**，这是故意的。
"""
if "Fork 的 Actions 开关" not in s:
    s = s.rstrip("\n") + add
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("blueprint updated")
else:
    print("already there")
