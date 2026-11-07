#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 追加：把「PLE 改 mmap 后的磁盘读」登记为 P408，并同步分母 / 报告 / 记忆。"""
import io
import shutil
import sys

PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

ROW = "\t".join([
    "B10环境与版本", "P408",
    "PLE 改 mmap 后的持续磁盘读：机主观察 1-2 MB/s，实测根因是 P254 去掉了 mlock",
    "W1035", "count", "1", "1", "DONE",
    "**W1035 立（机主提问触发，零停机实测）**：① 空闲时 NVMe 读 **0.0 KB/s**、无进程在读 ⇒ 读盘跟着推理走；"
    "② 固定文本 940 tok：首次 **1.11 MB**（1.2 KB/tok），同一提示再跑 **0.09 / 0.00 MB** ⇒ 页缓存命中即归零；"
    "③ 随机文本（冷页）：1343 tok **49.69 MB（37.0 KB/tok、请求内 17.9 MB/s）**、2660 tok **70.66 MB（26.6 KB/tok、16.8 MB/s）**，"
    "每 token 随长度下降 ⇒ 固定项=专家权重、每 token 项=PLE（`P138`：一 token 16 行落 16 个不同 4 KiB 页）；"
    "④ 机理 = `P254`（2026-11-05 02:48）把 `--ple-io` 由 `ram`（mmap+**mlock** 26.8 GiB）改为纯 `mmap`，"
    "表从「钉死」变「可回收」⇒ 冷页按需回读；`rchar`≈0 证明是 mmap 缺页而非 read()；"
    "⑤ 量级判定：49.69 MB 在 NVMe（/models 与 /home 同在 `nvme0n1p1`，ROTA=0）上按 ≥500 MB/s 折 ≤0.1 s，"
    "而冷首请求 2.77 s 的大头是专家/内核预热（同提示第二次 0.53 s、第三次 0.42 s 且 0 读盘）⇒ **读盘不是延迟来源**；"
    "⑥ 时间平均：3 s prefill 读 50 MB + 之后 30 s 解码 0 ⇒ 整轮均值 ≈1.5 MB/s，与机主观测吻合；"
    "⑦ 新风险（举一反三）：表可回收后与 ComfyUI（本机 20-34 GB 模型）抢页缓存，MemAvailable 掉到 10 GB 以下时 prefill 会变慢。",
    "P254",
])

ADD = """
- **追加（机主追问磁盘读）**：那条 1–2 MB/s 不是故障，是 `P254`（2026-11-05 02:48，`--ple-io ram→mmap`）把 26.8 GiB PLE 表从 mlock 改成可回收后的**按需回读**。实测：空闲 0.0 KB/s；固定文本 940 tok 首跑 1.11 MB、再跑 0.09/0.00 MB；随机冷文本 1343 tok 49.69 MB（37.0 KB/tok，请求内 17.9 MB/s）、2660 tok 70.66 MB（26.6 KB/tok）。`rchar≈0` ⇒ mmap 缺页，不是 read()。时间平均 = 3 s prefill 读 50 MB + 30 s 解码 0 ≈ **1.5 MB/s**，与他看到的一致。代价：NVMe 上 ≤0.1 s，**不是延迟来源**；风险是与 ComfyUI 抢页缓存。登记 `P408`。
- **线程那条**：`--pool-workers` 默认 20（22 物理核留 1 给 aux）→ 10，见 `P265`（W989 2026-11-05 19:40）：prefill@2K 524.45 vs 511.73（+2.49%，band 1.00%）、@8K +0.22%、TTFT 3.992 vs 4.074（−2.0%）、decode 持平 ⇒ **正向**。`P26`（W776-C1b）只否掉「显式 21」这一个值，不覆盖 10。
"""


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP408\t" not in prog:
        shutil.copyfile(PROG, PROG + ".bak_w1035b")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write(prog.rstrip("\n") + "\n" + ROW + "\n")
        print("PROGRESS.tsv +P408")
    else:
        print("P408 already present")

    plan = io.open(PLAN, encoding="utf-8").read()
    old = "**349 条 / 已结 267 / 76.5%**（W1035 校正；"
    new = "**350 条 / 已结 268 / 76.6%**（W1035 校正；"
    if old in plan:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035b")
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(old, new))
        print("W832 §0.1 -> 350/268/76.6%")
    else:
        print("!! §0.1 denominator not updated (pattern not found)")

    rep = io.open(REP, encoding="utf-8").read()
    o2 = "**349 条 / 已结 267 / 76.5%**（本轮 +1 条：`P407`）"
    n2 = "**350 条 / 已结 268 / 76.6%**（本轮 +2 条：`P407`、`P408`）"
    if o2 in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.replace(o2, n2))
        print("reply.md 四、进度 -> 350/268/76.6%")
    else:
        print("!! report progress line not updated")

    mem = io.open(MEM, encoding="utf-8").read()
    if "P408" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write(ADD)
        print("memory appended")
    else:
        print("memory already has P408")
    return 0


if __name__ == "__main__":
    sys.exit(main())
