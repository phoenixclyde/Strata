#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 更正：P408 的归因写错了（PLE/P254 是推断，不是实测），按数据重写。

纪律：撤回结论必须追到所有下游 —— 账本 → 方案分母 → 报告 → 记忆。
"""
import io
import shutil
import sys

PROG = "deploy/PROGRESS.tsv"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

NEW = "\t".join([
    "B10环境与版本", "P408",
    "请求驱动的磁盘读归因：全部是 gguf shard-2 的 mmap 缺页；旧页不会过期（0.00 MB）",
    "W1035", "count", "1", "1", "DONE",
    "**W1035 立，同日 W1035 更正**：① 空闲 60 s **无任何进程读盘**（只有 sda 147 KB/s 写）⇒ 读盘只跟着请求走；"
    "② **按文件归因**（`albus/w1035/attr_req.py`：请求前后对同一进程 `/proc/<pid>/smaps` 逐映射取 Rss 差）："
    "读 **34.45 MB** 的那次，Rss 增量 **32.9 MiB 全部落在** "
    "`Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf`，`rchar` 仅 0.02 MB ⇒ **mmap 缺页**，不是 read()、不是日志/监控；"
    "③ 该 shard **49.86 GB 只有 6.9 GiB（13.9%）常驻**；④ **页不会过期**：20 分钟前热过的提示再跑 **0.00 MB / 0.32 s**，"
    "同一随机提示立刻再跑也是 0.00 MB ⇒ 不是缓存抖动，是「新内容 = 新页」；"
    "⑤ 量级（全新随机文本，n=1/点）：901 tok **16.25 MB**、1752 tok **34.45 MB**、2660 tok **70.66 MB** ⇒ "
    "**18–37 KB/token、16–70 MB/请求**，方差大（取决于文本路由到哪些专家/PLE 行）；"
    "⑥ 时间平均：容器启动后 **320 个请求** × ~34 MB / 8190 s ≈ **1.33 MB/s**，与机主观测 1–2 MB/s 自洽；"
    "容器累计 91.4 GB 的其余 ~80 GB 是启动装载。"
    "**⑦ 撤回**：先前把主因写成「PLE 表 + `P254` 去 mlock」是**推断**（依据只有 `P138` 的 16 页/token 与两点线性拟合 28 MB+15.9 KB/token），"
    "已被 901/1752 tok 的实测推翻；`P254` 现在只是「可能降低驻留率」的候选，**未证实**。"
    "**未结**：驻留率是否低于切换前，需一次前后对照（重启或 `--ple-io ram` 臂），未做。",
    "P254",
])

ADD = """
- **更正（同日，机主追问「你确定吗」）**：上一条把读盘主因归到 `PLE`+`P254` 是**推断，已撤回**。按文件归因（`attr_req.py`，前后 smaps Rss 差）实测：34.45 MB 全部落在 `Qwen3.8-...-00002-of-00004.gguf`（Rss +32.9 MiB），`rchar`≈0 ⇒ mmap 缺页；该 shard 49.86 GB 仅 **13.9%** 常驻；**页不会过期**（20 min 前热过的提示再跑 0.00 MB / 0.32 s）；新随机文本 901/1752/2660 tok = 16.25/34.45/70.66 MB ⇒ **18–37 KB/token**，方差大。时间平均 320 req × 34 MB / 8190 s = **1.33 MB/s**，与机主观测自洽。`P254` 降为「可能影响驻留率」的候选，未证实。
- **方法学教训（本轮最重要）**：我在**只做了一次观测 + 一个巧合**（16 页/token）的情况下就写进了账本，还通过了全部 11 道门——因为门只查「有没有写」，不查「写得对不对」。归因类结论必须先做对照实验（同输入再跑一次 = 0.00 MB），**再**落账。
"""


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    lines = prog.rstrip("\n").split("\n")
    hit = None
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P408"]:
            hit = i
            break
    if hit is None:
        print("!! P408 not found")
        return 2
    shutil.copyfile(PROG, PROG + ".bak_w1035c")
    lines[hit] = NEW
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("P408 rewritten (line %d)" % (hit + 1))

    rep = io.open(REP, encoding="utf-8").read()
    tail = ("\n**8. 撤回并纠正（同日，机主追问「你确定吗？你自己有没有分析？」）。** 我在只做了"
            "一次观测、外加一个巧合（`P138` 的「16 页/token」）的情况下，就把「磁盘读 = PLE 表 + `P254` 去 mlock」"
            "写进了 `P408`——而且它通过了当时全部 11 道门。门只查「有没有写」，不查「写得对不对」。"
            "补做的三个对照实验把结论改了：① 20 分钟前热过的同一提示再跑，**读盘 0.00 MB / 墙钟 0.32 s**（冷时 1.11 MB / 2.77 s）"
            "⇒ 页**不会**过期，不是缓存抖动；② 请求前后对同一进程的 `smaps` 逐映射取 Rss 差，"
            "34.45 MB 的读**全部**落在 `...-00002-of-00004.gguf`（Rss +32.9 MiB），`rchar` 仅 0.02 MB ⇒ mmap 缺页；"
            "③ 该 shard 49.86 GB 只有 **6.9 GiB（13.9%）** 常驻，而全新文本 901/1752/2660 tok 分别读 16.25/34.45/70.66 MB "
            "⇒ **18–37 KB/token**，方差大。时间平均 320 请求 × 34 MB / 8190 s = **1.33 MB/s**，与机主观测吻合。"
            "`P408` 已按此重写，`P254` 降为「可能降低驻留率」的候选、未证实；驻留率是否低于切换前需要一次前后对照，未做。\n")
    if "8. 撤回并纠正" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + tail)
        print("reply.md +§8 retraction")

    mem = io.open(MEM, encoding="utf-8").read()
    if "更正（同日" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write(ADD)
        print("memory corrected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
