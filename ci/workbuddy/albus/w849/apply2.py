# -*- coding: utf-8 -*-
"""W849：记录分支顶端检查、关闭 R2（前提不成立）、基线补 commit/tree。"""
import io

ROOT = "D:/workbuddy_space/strata_ws/deploy/"

# ---------- PROGRESS：R2 判 N/A ----------
p = ROOT + "PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
lines = s.splitlines()
out = []
hit = 0
for ln in lines:
    if ln.startswith("#") or ln.startswith("block\t") or not ln.strip():
        out.append(ln)
        continue
    f = ln.split("\t")
    if len(f) > 1 and f[1] == "R2":
        hit += 1
        f[6] = "1"
        f[7] = "NA"
        f[8] = ("前提不成立（W849 实测）：专家缓存 7463 槽 = **全部专家**，policy `PROFILE ... no eviction`，"
                "启动 `pre-filled 7463 of 7463 slots`；`cc.evictions=0`；`hardware.gpu_pcie_rx_mb` 60 个样本恒 "
                "**0.01 MB**（max 0.02），每请求 `pcie_share` 0.000-0.004。"
                "⇒ 没有淘汰/没有读盘，加大 reserve 只会缩小缓存，**本条无收益**。")
    out.append("\t".join(f))
s = "\n".join(out) + "\n"
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("R2 命中 %d 行 → NA" % hit)

# ---------- 基线：补 commit / tree ----------
p = ROOT + "PROD_BASELINE.tsv"
b = io.open(p, encoding="utf-8-sig").read()
if "\ncommit\t" not in b:
    b = b.replace("exe\t", "commit\taef9d256077a33d4687c40ae29c7c9f3bda486c9\n"
                            "branch\tgfx906/0.2.9-mi50\n"
                            "tree\t4ce087ba3ac2969ecf8eabd62b2a4f1c3e1be5d0\n"
                            "upstream\tc62d5e3a15 (v0.2.9)\n"
                            "exe\t", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(b)
print("baseline 补 commit/branch/tree/upstream")

# ---------- SESSION_STATE §7：把 verify_tip 加进每轮口径 ----------
p = ROOT + "SESSION_STATE.md"
s = io.open(p, encoding="utf-8").read()
anchor = "```\npython tools/ledger_audit.py"
if "verify_tip.sh" not in s:
    s = s.replace(
        "| `166:~/strata166/tmp/state_q.py` + `verify_patches.sh` | 生产实况与门禁，每次现取 |",
        "| `166:~/strata166/tmp/state_q.py` + `verify_patches.sh` | 生产实况与门禁，每次现取 |\n"
        "| `166:~/strata166/tmp/verify_tip.sh` | **“生产是否就在分支顶端”的唯一检查**（W849）：branch/HEAD/tree、工作区、"
        "与 origin 一致、**/src 逐文件 md5 == HEAD 树**（5319 文件）、引擎二进制 == 构建产物、门禁；全过才打印 `TIP-OK` |", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("SESSION_STATE §7 加 verify_tip")
else:
    print("verify_tip 已在文里")

# ---------- W832 队列：R2 标已结 ----------
p = ROOT + "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = "| **1** | **R2 `--vram-reserve-mib 1536`** |"
i = s.find(old)
if i > 0:
    end = s.find("\n", i)
    s = s[:i] + ("| ~~1~~ | ~~**R2 `--vram-reserve-mib 1536`**~~ **已结（NA，W849）**：专家缓存 7463 槽 = 全部专家、"
                 "`no eviction`、`evictions=0`、PCIe rx 恒 0.01 MB ⇒ 前提不成立，无收益 | — | — |") + s[end:]
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("W832 队列 R2 标 NA")
else:
    print("W832 队列未找到 R2 行")
