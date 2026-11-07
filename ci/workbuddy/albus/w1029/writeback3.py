# -*- coding: utf-8 -*-
import io
PLAN="deploy/W832_OPT_PLAN_V2.md"; PROG="deploy/PROGRESS.tsv"
s=io.open(PLAN,encoding="utf-8").read()
a="| 进度分母 | **305 条 / 已结 221 / 72.5%** |"; b="| 进度分母 | **307 条 / 已结 223 / 72.6%** |"
assert a in s; s=s.replace(a,b,1)
a2="`mi50-0.2.11-r33-12` @ `8476b78c`"; b2="`mi50-0.2.11-r33-14` @ `6501c28f`"
assert a2 in s; s=s.replace(a2,b2,1)
a3="behind 0 / ahead 76 / merges 0）"; b3="behind 0 / ahead 78 / merges 0）"
assert a3 in s; s=s.replace(a3,b3,1)
BLOCK = """

### 七、GitHub CI 绿了：run #47 @ `6501c28f`，14 秒

你点开开关后 `dispatch` 立刻从 **422 → 204**，随后三次推送连红，每次只往前走一步，
**每步都是同一个病：判据依赖了运行它的那台机器。**

| run | 卡在哪一行（日志逐字） | 被当成失败的那件事 | 修法 |
|---|---|---|---|
| #45 `8476b78c` | `[BAD] baseline … rc=1 / [FAIL] container image  error: no such object: strata166-407` | runner 上有 docker、没有我们的容器 | `release_check.py --offline`：5 行宿主项（容器/镜像 json/二进制/版本一致/树 hash）降为 **SKIP**，不再当失败 |
| #46 `a9677182` | `[FAIL] llama.cpp pin (release) (absent)` | `--offline` 跳过了 `BUILD-IMAGE.json`，而 release pin 那一行正是读这个文件 | offline 时改读 **`ci/docker/Dockerfile-*` 里的 `LLAMA_CPP_SHA`**（烤进镜像的那份声明），行还有意义而不是缺 |
| #47 `6501c28f` | — | — | fixture 补写该 Dockerfile（**fixture 缺了被检查的文件，就不算 repo**）⇒ **success，14 s，6/6 步全绿** |

判据链现在是活的：`ci/gh_gate.py` → **`GH_GATE: PASS 6501c28fecf2 run #47`**，`ci/deploy.sh` 第 0 步首次被一条**真实的 GitHub 绿 run** 放行；
本地 `round_gate` 与 166 接收端回执降为推送前自检与第二双眼睛。

**为什么值得记**：三次红都不是"CI 坏了"，而是**把宿主事实、镜像产物、fixture 形状当成了源码事实**。
干净 depth-1 clone（无容器、无 `/data`、无 tag）现在能一次跑通 `ROUND_GATE: PASS`——这才是能交给 runner 的判据。
"""
if "GitHub CI 绿了" not in s:
    s = s.rstrip("\n") + BLOCK
io.open(PLAN,"w",encoding="utf-8",newline="\n").write(s)
print("plan updated")

rows=[("B8工程","P372","GitHub CI 首次绿：run #47 @6501c28f（14 s）；此前 #45/#46 各卡一条「宿主事实当源码事实」",
       "W1029","DONE",
       "**W1029 立**：开关打开后 dispatch 422→204。#45 卡 `[FAIL] container image error: no such object: strata166-407`（runner 有 docker 无容器）⇒ `release_check --offline` 把 5 行宿主项降 SKIP；"
       "#46 卡 `[FAIL] llama.cpp pin (release) (absent)`（offline 跳过 BUILD-IMAGE.json 而这行读它）⇒ offline 改读 `ci/docker/Dockerfile-*` 的 `LLAMA_CPP_SHA`；"
       "#47 前补 fixture 的 Dockerfile（fixture 缺被检查文件就不算 repo）⇒ **success 14 s，6/6 步**。`GH_GATE: PASS 6501c28fecf2 run #47`。",
       "ci/release_check.py"),
      ("B8工程","P373","部署门首次由真实 GitHub 绿 run 放行（`ci/gh_gate.py` 从 exit 6 变 PASS）",
       "W1029","DONE",
       "**W1029 立**：`python3 ci/gh_gate.py --wait 200` → `GH_GATE: PASS 6501c28fecf2 run #47 https://github.com/phoenixclyde/Strata/actions/runs/42228754383`，rc=0。"
       "`ci/deploy.sh` 第 0 步据此放行；此前三次都是 exit 6/7。判据链：GitHub run（判据）→ 本地 round_gate（自检）→ 166 回执（第二双眼睛）。",
       "ci/gh_gate.py")]
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
