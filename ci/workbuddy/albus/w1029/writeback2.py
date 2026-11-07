# -*- coding: utf-8 -*-
import io
PLAN="deploy/W832_OPT_PLAN_V2.md"; PROG="deploy/PROGRESS.tsv"
s=io.open(PLAN,encoding="utf-8").read()
a="| 进度分母 | **303 条 / 已结 219 / 72.3%** |"; b="| 进度分母 | **305 条 / 已结 221 / 72.5%** |"
assert a in s; s=s.replace(a,b,1)
a2="`mi50-0.2.11-r33-11` @ `bc56628a`"; b2="`mi50-0.2.11-r33-12` @ `8476b78c`"
assert a2 in s; s=s.replace(a2,b2,1)
a3="behind 0 / ahead 74 / merges 0）"; b3="behind 0 / ahead 75 / merges 0）"
assert a3 in s; s=s.replace(a3,b3,1)
BLOCK = """

### 六（补）W1029 续：Settings 那一页只是策略，fork 还要在 Actions 页点一次

截图确认 **Actions permissions = Allow all actions and reusable workflows**，但 dispatch 仍 422。
两条同时为真不矛盾：`/actions/permissions` 说的是**策略允许什么**，422 说的是**这个 fork 的
workflows 有没有被启用**。外部证据与本案完全同形（apache/seatunnel 维护者对同一 422 的答复）：
① Settings → Actions → General 设 Allow all；② **Actions 页顶部横幅** "Workflows aren't being run on
this forked repository" → 点 "I understand my workflows, go ahead and enable them"；③ **推新提交**
（GitHub 不回填）；④ 若开关改不动 → 查 Billing 有无 hold。

实测第 ③ 条：空提交 **`e4f0867d`** 推到 origin，180 s 内 `actions/runs` 无新 run ⇒ 开关仍未开。

已做的两件事：四步写进 **`ci/README.md`**（仓库内可见，`gh_gate.py` 的 exit 6 也照这四条报）；
`.github/workflows/downstream-gate.yml` 里指向 `deploy/CI_CD_BLUEPRINT.md` 的注释改成 `ci/README.md`——
因为 **`deploy/` 在本仓 git 里 0 个跟踪文件**，那句引用指向的是一份只存在于我笔记本的文件（又一个同族缺陷）。

判据不变：`python3 ci/gh_gate.py --wait 300`；点完横幅后再推一次即可，`deploy.sh` 第 0 步随即放行。
"""
if "Settings 那一页只是策略" not in s:
    s = s.rstrip("\n") + BLOCK
io.open(PLAN,"w",encoding="utf-8",newline="\n").write(s)
print("plan updated")

rows=[("B8工程","P370","fork 的 Actions 需两处开关 + 一次新推送（GitHub 不回填）；空提交 e4f0867d 实测 180 s 无 run",
       "W1029","DONE",
       "**W1029 立**：`/actions/permissions`=`Allow all`（机主截图）时 dispatch 仍 422 ⇒ 策略 ≠ fork 启用。外部同形案例（apache/seatunnel 对同一 422 的答复）给出四步："
       "Settings→Actions→General 设 Allow all；**Actions 页横幅** I understand…enable them；**推新提交**（不回填）；开关改不动则查 Billing。"
       "实测：空提交 `e4f0867d` 推 origin 后 180 s 无 run ⇒ 仍关。四步已写进 `ci/README.md`，`gh_gate.py` exit 6 照此报错。",
       "ci/README.md"),
      ("B8工程","P371","`deploy/` 在本仓 0 个跟踪文件，工作流注释却引用 `deploy/CI_CD_BLUEPRINT.md`（只存在于笔记本）",
       "W1029","DONE",
       "**W1029 立**：`git ls-files deploy | wc -l` = **0**，而 `.github/workflows/downstream-gate.yml` 头部写着 See deploy/CI_CD_BLUEPRINT.md。"
       "同族缺陷第三次（W1018 证据只在笔记本 / W1025 报告两个副本）。修：注释改为指向 `ci/README.md`（受跟踪），四步文档落在那里。",
       ".github/workflows/downstream-gate.yml")]
lines=io.open(PROG,encoding="utf-8").read().split("\n")
hi=next(i for i,l in enumerate(lines) if not l.startswith("#") and l.count("\t")>=9)
ID=lines[hi].split("\t").index("id")
have={l.split("\t")[ID] for l in lines if l.count("\t")>=9}
add=["\t".join([b,pid,item,src,"count","1","1",st,note,ref]) for b,pid,item,src,st,note,ref in rows if pid not in have]
if add:
    while lines and lines[-1]=="": lines.pop()
    lines += add + [""]
io.open(PROG,"w",encoding="utf-8",newline="\n").write("\n".join(lines))
print("progress +%d"%len(add))
