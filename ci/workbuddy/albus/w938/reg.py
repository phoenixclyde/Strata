#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W938 register: R81 (window 12) + R82 (rebase) + R83 (container) DONE, P263 (image)."""
import io, os

D = "D:/workbuddy_space/strata_ws/deploy"

# ---------------- PROGRESS ----------------
p = os.path.join(D, "PROGRESS.tsv")
rows = [
    ["B4上游移植", "R82",
     "主线 rebase 到 upstream v0.2.10（ffa80d73）：37 条本地提交重放，三处冲突按语义解，分支按标准归档，force-with-lease 推回 fork",
     "W938 §2", "count", "1", "1", "DONE",
     "**W938 实测（2026-11-04 12:5x）**：标准流程 —— `git bundle --all`(76 MB) + 6 个 `pre-rebase/*` + `rerere.enabled=true` → `git rebase upstream/main`。"
     "**三处冲突**：①`901e6b0a` 的 `arch_defaults.hpp`（两边各加一个声明）→ 两边都留；②同提交的 `qsa_select.cu` → "
     "上游已完整实现我们的 W842(SIMT=2 + 社区调优 + alt_min_tokens)，取上游；③`705e09f7` 的 `generate.cpp` → 保留上游 "
     "STRATA_MTP_ROOM_MIN 整块，trace 打点放其前；④`d963c791` 的 spec 阶梯 → 保留上游 S/S_mtp_wide/S_mtp_narrow/S_mtp/S_look 结构，"
     "把 `/data/strata-spec` 读取提到派生值之前。结果 **0 behind / 37 ahead**、无冲突标记、gfx906_tuned_env 7 项完整。"
     "**补丁债归零**：e1b27d54/5a13c34f/243fdb21/ed76b12f/fbf6e1c7/af6ba4c6 全部是 upstream 祖先 ⇒ 0.2.10 原生包含，"
     "work/r77 手工补丁树作废。**分支**：r54-port/exp-R55-swizzle/bench-*/w863-main 打 `archive/*` tag 后删除（已否定的实验不 rebase），"
     "main 快进到 origin/main，临时 rebase-trial 删除。**推送**：`push --force-with-lease origin gfx906/mi50` 成功，"
     "远端 = 5f73cd15 = 本地 HEAD；tag `mi50-0.2.10-r28` 与 4 个 archive tag 已推。产物 W938",
     "W938;W917"],
    ["B10环境与版本", "R83",
     "容器跟主线：新镜像 strata-gfx906:0.2.10-101（/src = rebase 树）+ 按 inspect 逐字复现重建容器 + 引擎 0.1.56 走 ci deploy",
     "W938 §3", "count", "1", "1", "DONE",
     "**W938 实测（2026-11-04 12:5x）**：先按老路子写全新 Dockerfile（FROM mixa3607）—— **构建期无外网**，pip 到 tuna "
     "`No matching distribution found` ⇒ 改为 `FROM strata-gfx906:0.2.9-101` 只替换 /src（ROCm/clang/python 逐字节不变，"
     "变的正是要变的那层）。镜像 sha256 `5267df6d…`，/src 266 MB，`/src/BUILD-IMAGE.json` 记 provenance。"
     "**引擎与容器分开**：/data 是 bind ⇒ 引擎不进镜像，走 `ci/strata-ci deploy --src build-r28 --exe strata-0.1.56 --apply`"
     "（gate 18/18、tag 门禁过、health 243 s、账本行写入 tag=mi50-0.2.10-r28 + git_head=5f73cd15）。"
     "**容器**：参数由 `docker inspect` 程序化生成（不是手抄），旧容器改名 `strata166-407.pre-210` 保留回滚。"
     "**三方对齐**：/src CMakeLists 0.1.56、server.py `ecf3cfc5`(原生含 fatal-GPU 3 处)、引擎 `ae085365` = /data/bin/strata-0.1.56。"
     "**性能**：prefill 8.868→8.810/8.814(−0.6%)、decode 稳态 79.44→~83.7(+5%)、官方 bench 73.49 tok/s CV1.84%。"
     "**行为变化**：window up to 6→**12 tokens**，已立 R81。ci/config.sh 改 BUILD=build-r28 / IMG=0.2.10-101",
     "W938;W937"],
    ["B6判定探针", "R81",
     "0.2.10 的窗口宽度从 6 到 12 token：按 prompt 长度分布测接受率与 decode 收益，判断是否需要调 --mtp-max-t / --spec",
     "W938 §4", "count", "1", "0", "OPEN",
     "**W938 立（2026-11-04 12:5x）**：0.1.56 启动日志 `strata verify: window up to 12 tokens, 131.3 MiB of device buffers`"
     "（0.1.55 是 `up to 6, 96.2 MiB`）。decode 稳态已见 +5%（79.44→83.7），但未拆开归因：可能是窗口变宽、也可能是 0.2.10 其他改动。"
     "**做法**：固定 prompt/输出，扫 `--spec 4/6/8` 与 `--mtp-max-t`（0/6/12），读服务端 `spec depth: accepted/tested` 的按深度接受率，"
     "算「每窗口净 token / 每 token GPU 时间」；判据 `|Δ|≥2×CV`。**注意**：`--spec` 是启动参数，每次要重启（4 分钟）",
     "W938"],
]
with io.open(p, "a", encoding="utf-8") as f:
    for r in rows:
        assert len(r) == 10, len(r)
        f.write("\t".join(r) + "\n")
print("PROGRESS +3 rows")

# ---------------- PARAM_REGISTER ----------------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
p263 = ["P263", "部署形态", "运行镜像：strata-gfx906:0.2.10-101（/src = rebase 到 v0.2.10 的树）",
        "image=5267df6d…；/src CMakeLists 0.1.56；server.py ecf3cfc5",
        "运维", "ADOPTED",
        "镜像只承载 /src；引擎在 /data/bin（bind）。换镜像必须同步换引擎，两者版本对不上时 serve 与引擎的 stdout 协议会错配",
        "W938 §3", "2026-11-04", "",
        "【W938】旧镜像 0.2.9-101(/src=0.1.55) 与新引擎 0.1.56 混跑过一次（health 正常，但 serve/server.py 是旧版）。"
        "已重建为 0.2.10-101 并把 /src 换成 0.1.56 树。构建期无外网 ⇒ 本镜像 FROM 0.2.9-101（不是直接 FROM mixa3607），"
        "以复用已装好的 ROCm/python；`/src/BUILD-IMAGE.json` 记录 source/commits_on_top/engine。"
        "旧容器保留为 strata166-407.pre-210，回滚 = 起旧容器 + `rollback --exe strata-0.1.55w --apply`"]
while len(p263) < 11:
    p263.append("")
with io.open(q, "a", encoding="utf-8") as f:
    f.write("\t".join(p263) + "\n")
print("P263 appended")

# ---------------- W832: 纪律 ----------------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
anchor = "> **方法纪律追加（`W937` 2026-11-04 11:5x · CI/CD）**"
rule = ("> **方法纪律追加（`W938` 2026-11-04 12:5x · 上游同步）**：⑫ **每次开新工作前先 `git fetch upstream && git rebase upstream/main`**，"
        "不要攒到 700 条再 rebase（本轮 37 条重放只出 3 处冲突，攒得越久越贵）。\n"
        "> ⑬ rebase 前必备：`git bundle --all` + 每个分支一个 `pre-rebase/*` 指针 + `rerere.enabled=true`；"
        "**已否定的实验分支不 rebase**，打 `archive/*` tag 后删除（为死实验解冲突只会制造假历史）。\n"
        "> ⑭ 推回 fork 用 `git push --force-with-lease`，**永不裸 `--force`**；推前先 `fetch` 让 lease 基于最新远端。\n"
        "> ⑮ 版本号跨代时（0.2.9→0.2.10 / 引擎 0.1.55→0.1.56）必须**同时**换 `/src` 与引擎：只换引擎会让 serve 层协议落后一代。\n>\n")
assert anchor in s
s = s.replace(anchor, rule + anchor, 1)
io.open(r, "w", encoding="utf-8").write(s)
print("W832 +4 disciplines")
