#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1003 回写：把附录追加进 deploy/W832_OPT_PLAN_V2.md，并更新 deploy/PROGRESS.tsv。"""
import io
import os
import re

ROOT = r"D:\workbuddy_space\strata_ws"
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
BLOCK = os.path.join(ROOT, "albus", "w1003", "w832_w1003_append.md")


def norm(p):
    b = open(p, "rb").read()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.replace(b"\r\n", b"\n").decode("utf-8")


# ---------- 1. W832 ----------
plan = norm(PLAN)
block = norm(BLOCK)
if "§6.5 回写 · W1003" in plan:
    print("PLAN: already has W1003 block, skip")
else:
    if not plan.endswith("\n"):
        plan += "\n"
    plan = plan + block
    open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
    print("PLAN: appended %d chars" % len(block))

# ---------- 2. PROGRESS ----------
rows = [l for l in norm(PROG).split("\n") if l.strip()]
out = []
hit_r97 = False
for l in rows:
    c = l.split("\t")
    if len(c) >= 10 and c[1] == "R97":
        hit_r97 = True
        c[5], c[6], c[7] = "0", "0", "WITHDRAWN"
        c[8] = ("**W1003 解散（2026-11-05 22:3x）**：原前提「320 行 repacked 慢 15%」被三臂扫描推翻——"
                "同一点 w32=0.955 / w64=1.183，慢的是 mx 的分派规则 `use_w32 = n_assign < 2*BN_ID*ne02`"
                "（16 专家=4096 行），不是 kernel；固定 w32 即可，没有「该留给 canonical 的大段」。"
                "不计入分母。")
        c[9] = "deploy/W832_OPT_PLAN_V2.md §6.5（W1003 回写）"
        l = "\t".join(c)
    out.append(l)

NEW = [
    ("B4上游移植", "P285", "宽度×类型×形状三臂扫描（repack 判据实测）", "W1003", "count", "1", "1", "DONE",
     "**W1003（2026-11-05 22:2x）** canonical / repacked-w32 / repacked-64-wide 三臂，同进程同 stream hipEvent，"
     "两臂共用同一份 `mmq::quantize` 激活；产物 `ci/repack_ab/WIDTH_SWEEP.tsv`（20 行）+ `type_sweep.cu`（入仓）。"
     "gu Q4_K w32 2.26–2.98× / w64 1.02–3.87×；gu Q5_K w32 1.57–2.51×；down Q5_1 w32 0.79–0.81；"
     "down Q8_0 w32 0.54–0.69、w64 0.58–0.61。⇒ 320 行的「慢 15%」是分派规则而非 kernel（同点 w32 0.955 / w64 1.183）。",
     "ci/repack_ab/WIDTH_SWEEP.tsv"),
    ("B4上游移植", "P286", "生产专家的真实量化类型核对（pack 清单，不靠推测）", "W1003", "count", "1", "1", "DONE",
     "**W1003**：`/data/packs/ud-q4_k_xl/native_experts.txt` 的列是 `layer gu_type d_type …` ⇒ "
     "gate/up = Q4_K(12)/Q5_K(13) @[out 1280, K 2560]，down = Q5_1(7)/Q8_0(8) @[out 2560, K 640]。"
     "**K=640 不是 QK_K=256 的倍数 ⇒ K-quant 在 down 上几何不合法**（这才是 Unsloth UD 只在 gu 用 K-quant 的原因）。"
     "此事实推翻了此前拿 Q5_1 当全模型代理的做法。", "ci/repack_ab/PORT_STATUS.md §0"),
    ("B4上游移植", "P287", "repack 的尺寸账（决定借槽与 d_stride 要不要改）", "W1003", "count", "1", "1", "DONE",
     "**W1003**：Q5_1 down **尺寸中性**（1,228,800 = 1,228,800 B，`d_stride`／零尾／借槽账本全不动）；"
     "Q8_0 down **+2.3%**（1,740,800 → 1,781,760 B）⇒ 全套移植里唯一需要改账本的单元格。",
     "ci/repack_ab/PORT_STATUS.md §1 C1"),
    ("B5本机缺口", "P288", "权威方案回写 + 双份漂移修复（本机主拷贝 → 166 镜像）", "W1003", "count", "1", "1", "DONE",
     "**W1003（2026-11-05 22:3x）**：机主问「本轮输出加到权威调优方案了吗」——查实**没有**，且 "
     "`/home/albus/strata166/deploy/W832` 停在 2026-11-03 02:54（97,700 B / 839 行），本机那份 128,282 B / 1,015 行，"
     "W882 之后 18 轮全没进 166 ⇒ 权威件双份漂移。整改：§6.5 追加 W1003 回写块（R97 解散 / R86 收窄 / R96 N/A + 新执行序）；"
     "主拷贝定在本机、166 退为镜像，收尾 `scp` + 双侧 md5 一致才算完。",
     "deploy/W832_OPT_PLAN_V2.md §6.5"),
]

# 幂等：已存在则不重复追加
have = {l.split("\t")[1] for l in out if len(l.split("\t")) > 1}
for n in NEW:
    if n[1] in have:
        print("PROG: %s exists, skip" % n[1])
        continue
    out.append("\t".join(n))
    print("PROG: +%s" % n[1])

open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

# ---------- 3. 重算进度 ----------
data = [l.split("\t") for l in out if l.strip() and not l.startswith("#")]
hdr = data[0]
ci, di, si = hdr.index("count"), hdr.index("done"), hdr.index("status")
tot = done = 0
for r in data[1:]:
    if len(r) <= si:
        continue
    try:
        c, d = int(r[ci]), int(r[di])
    except Exception:
        c, d = 1, (1 if r[si] in ("DONE", "DONE_NEG", "NA") else 0)
    tot += c
    done += d
print("PROGRESS: weighted total=%d done=%d pct=%.1f%%" % (tot, done, 100.0 * done / tot))
print("r97_hit:", hit_r97)
