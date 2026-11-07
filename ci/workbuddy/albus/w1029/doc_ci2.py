import io
R = "/home/albus/strata166/pr/strata-fork/"

p = R + "ci/README.md"
s = io.open(p, encoding="utf-8").read()
add = """

## Fork 的 Actions 开关（W1029，实测；`gh_gate.py` 就按这四条报错）

`POST /repos/{owner}/{repo}/actions/workflows/{file}/dispatches` 返回
**422 `Actions has been disabled for this repository`**，而
`GET /repos/{owner}/{repo}/actions/permissions` 同时报 `enabled: true, allowed_actions: all`。
两句可以同时为真：前者是**这个 fork 的 workflows 有没有被启用**，后者是**策略允许什么**。

四条要一起做，缺一条都不动：

1. **Settings → Actions → General → Allow all actions and reusable workflows**，然后点这一节的 **Save**。
   只选中不 Save 等于没改。
2. **Actions 标签页**（`https://github.com/<owner>/<repo>/actions`）顶部的横幅
   *"Workflows aren't being run on this forked repository"* → 点
   **"I understand my workflows, go ahead and enable them"**。Settings 里没有替代品。
3. **推一个新提交**。GitHub **不回填**：开关关着时推上去的 sha 永远不会补跑。
   实测 `e4f0867d`（空提交）推到 origin 后 180 s 内无 run。
4. 第 1 步若改不动/自己变回去，是账号或组织策略，去 **Settings → Billing and plans** 看有没有 hold。

判据一条命令：`python3 ci/gh_gate.py --wait 300`（exit 6 = 没 run，并会打印上面四条）。
`ci/deploy.sh` 第 0 步就是它：**开关没开 = 部署被拒**，这是故意的。
"""
if "Fork 的 Actions 开关" not in s:
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip("\n") + add)
    print("ci/README.md updated")
else:
    print("ci/README.md already has it")

w = R + ".github/workflows/downstream-gate.yml"
t = io.open(w, encoding="utf-8").read()
old = "See deploy/CI_CD_BLUEPRINT.md for why that stays local."
new = "See ci/README.md for why that stays local (deploy/ is not tracked in this repo)."
if old in t:
    io.open(w, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
    print("workflow comment fixed")
else:
    print("workflow comment: anchor not found (left as is)")
