#!/usr/bin/env python3
# W937 登记：R80(OPEN) + P262；W832 纪律 12/13/14
import io, os

D = "D:/workbuddy_space/strata_ws/deploy"

# ---------- 1) PROGRESS: 追加 R80 ----------
p = os.path.join(D, "PROGRESS.tsv")
row = ["B10环境与版本", "R80",
       "给 ci/gate.py 加三项 provenance 检查：config.exe 的 md5 == 账本末条 exe_md5；该 md5 == build/strata 的 md5；账本末条 tag 非 - 且等于 HEAD 的 tag",
       "W937 §5", "count", "1", "0", "OPEN",
       "**W937 立（2026-11-04 11:5x）**：机主问「是不是不走 ci/cd 了」，核实成立 —— R66/R68/R78/R77 的 build 与 deploy 都绕过 ci/strata-ci："
       "手工 docker cp/mv/restart、手工抄 ninja 命令、用宿主机 bench_pair.py 代替 strata-ci bench/compare。**可验证的损害**："
       "①部署账本停在 2026-11-02T00:15（e0c6f250/r27），漏记 a97f4479(11-03 21:25)、8e92c662(11-04 09:14)、cf2ba243(11-04 11:31)；"
       "②rollback --last 取 tail-2 会从 cf2ba243 跳回 strata-0.1.55s(r26)，跳过三代；③版本文件名被覆盖：strata-0.1.55t 内容换成 cf2ba243，"
       "而账本记的是 e0c6f250（唯一副本在 gfx029-build/strata.bak-e0c6f250，已还原）；④state/runs 只有 11-01 的 4 条，11-02 以来二十多个 A/B 全在账外。"
       "**已修**：建 .55u=a97f4479 / .55v=8e92c662 / .55w=cf2ba243，.55t 还原成 e0c6f250，补三条 retro 账本行（tag 列记 -，不伪造），"
       "config exe 指向 .55w，rollback --last 现正确指向 .55v，strata-ci check 18/18 PASS。**未修**：生产二进制无对应 tag（补丁只在 work/r77 未提交）。"
       "**本条要做的**：把三项 provenance 检查写进 gate.py（只读、秒级），任一项不满足即 FAIL —— 这样绕过 deploy 会在下次 check 立刻暴露",
       "W937"]
with io.open(p, "a", encoding="utf-8") as f:
    f.write("\t".join(row) + "\n")
print("R80 appended")

# ---------- 2) PARAM_REGISTER: P262 ----------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
p262 = ["P262", "部署形态", "生产 exe 指针与版本文件名一一对应：/data/bin/strata-0.1.55X 一个字母一个内容，永不覆盖",
        "exe=/data/bin/strata-0.1.55w；.55t=e0c6f250(r27) .55u=a97f4479 .55v=8e92c662 .55w=cf2ba243",
        "运维", "CONFIRMED",
        "改 exe 或换二进制后必须：账本末条 md5 == config exe 的 md5 == 运行中 /proc/<pid>/exe 的 md5",
        "W937 §4", "2026-11-04", "",
        "【W937】修前 strata-0.1.55t 的内容被换成 cf2ba243，而账本（2026-11-02T00:15）记它是 e0c6f250 ⇒ rollback --exe strata-0.1.55t 会静默装错。"
        "已从 gfx029-build/strata.bak-e0c6f250 还原 .55t，并把三个实际部署过的引擎各建一个版本文件（.55u/.55v/.55w）。"
        "账本补三行 retro（tag 列 -），exe 现指 .55w（与运行中的 cf2ba243 同字节）。rollback --last 已验证 = .55v"]
while len(p262) < 11:
    p262.append("")
with io.open(q, "a", encoding="utf-8") as f:
    f.write("\t".join(p262) + "\n")
print("P262 appended")

# ---------- 3) W832: 纪律 12/13/14 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
anchor = "> **方法纪律追加（`W936` 2026-11-04 11:3x）**"
rule = ("> **方法纪律追加（`W937` 2026-11-04 11:5x · CI/CD）**：⑧ **部署只有一条路** —— `ci/strata-ci deploy --apply`"
        "（tag 门禁 + 7 步 + 写账本）。手工 `docker cp`/`mv`/`restart` 一旦发生，`rollback` 与账本就同时失真："
        "本轮实测账本落后 3 次部署、`rollback --last` 跳三代、版本文件名被覆盖。\n"
        "> ⑨ **版本文件名不可复用**：`strata-0.1.55X` 一个字母一个内容，永远新建、永不覆盖；盖掉它等于让 `rollback --exe` 说谎。\n"
        "> ⑩ **实验必须进 `ci/state/runs/`**：`strata-ci bench` 记 JSON、`compare` 判 2×噪声；只在 md 里写中位数不算记录。\n"
        "> ⑪ 构建/部署前后各跑一次 `ci/strata-ci check`，并把它输出贴进当轮档案（18 项，秒级）。\n>\n")
assert anchor in s, "anchor missing"
s = s.replace(anchor, rule + anchor, 1)

# 队列里插入 R80
a2 = "| **新14** | **R66** |"
if a2 not in s:
    # fallback: put before R79 row if present
    a2 = "| **1** | **R79** |"
r80 = ("| **流程** | **R80** | 给 `ci/gate.py` 加三项 provenance 检查（config.exe md5 == 账本末条 == build 物；末条 tag == HEAD tag）"
       " | 只读、秒级；任一项不满足即 FAIL | 零停服 |\n")
if a2 in s:
    s = s.replace(a2, r80 + a2, 1)
    print("R80 row inserted")
else:
    print("WARN: could not place R80 row")

io.open(r, "w", encoding="utf-8").write(s)
print("W832 updated")
