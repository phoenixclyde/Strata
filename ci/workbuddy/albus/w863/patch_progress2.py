# -*- coding: utf-8 -*-
"""R23 -> DONE (deployed on 0.1.55h, A/B +4.0%); keep R22 as updated by patch_progress."""
import io
import shutil

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
shutil.copy2(P, P + ".w863b")
lines = io.open(P, encoding="utf-8").read().split("\n")
out, changed = [], []
for ln in lines:
    f = ln.split("\t")
    if len(f) > 9 and f[1] == "R23":
        f[7] = "DONE"
        f[8] = ("**已上生产（W863）**：`deploy/W863_R23_DEPLOY.md`。引擎 0.1.55g → **0.1.55h**"
                "（md5 9a2ff874…，40,764,992 B），config exe 改指，镜像仍 0.2.9-101（/data 是 bind mount，镜像不带引擎）。"
                "上的是**实测表**不是 W862 公式（公式 ncols=1 选 R=4 ⇒ 0.982× 倒扣，见 W863_WAVE_ROWS_TABLE.md）。"
                "顺手补了 `STRATA_MMVQ_WAVE_ROWS` 的真读——原文档声称有、代码里只有注释，回滚开关此前是假的。"
                "同镜像同二进制 A/B（T B T B 交错，唯一变量是该 env）：**48.6 vs 46.8 tok/s ⇒ +4.0%**，"
                "两轮配对 +4.31%/+3.53% 同向。逐位等价沿用 W862（9 形状 diff=0）。"
                "收益上限被 T≈2 的窗口卡住（drafts ≈0.9/窗口），更大的杠杆是草稿链长度")
        f[9] = "W863-3"
        changed.append(f[1])
    out.append("\t".join(f))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("changed:", changed)
for ln in io.open(P, encoding="utf-8").read().split("\n"):
    f = ln.split("\t")
    if len(f) > 9 and f[1] in ("R22", "R23"):
        print("%s\t%s\tcols=%d\tref=%s" % (f[1], f[7], len(f), f[9]))
