# -*- coding: utf-8 -*-
"""P141 追加 W815 的启动两档与 RAM 取舍；并新增 P143（STRATA_UNBUFFERED_LOAD）判否。"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"

ADD141 = (
    "【W815 补充】启动本身分两档：**pack 在页缓存时 42-46 s 就绪**，**冷启 201-280 s**"
    "（55.43 GiB 竞技场以 0.27-0.40 GiB/s 读进主存；那个 8.79 GiB 平台台阶就是这个阶段，"
    "高度 = 全部上卡显存减去 22.25 GiB 专家缓存，`8.79 + 22.25 = 31.04` 逐字节对得上）。"
    "`--ple-io ram` 的 +85 s 就是 26.8 GiB ÷ 0.35 GiB/s。⇒ RAM 账绕不开：128.7 GB 里 anon 已占 59.7 GB，"
    "表再占 26.8 GiB 之后 pack 的 55.4 GiB 页缓存就留不全 —— **「启动快」与「提示快」二者只能选一个**。"
)

V143 = (
    "**REJECTED（W815 实测）**。本构建在 Linux 上这个开关**只把竞技场的读线程从 6 提到 16，没有 O_DIRECT**"
    "（上游 #3624 逐字：\"There, `STRATA_UNBUFFERED_LOAD=1` only raises the reader count to 16, and the load "
    "still runs at the page-cache path's speed.\"）。交错 P/U 两启：P 0.27 GiB/s / 242 s，U 4.47 GiB/s / 42 s，"
    "看起来 16 倍 —— **但收尾那次「生产配置、不设该 env」照样 3.02 GiB/s / 46 s**，"
    "说明差异 100% 来自页缓存、与这个开关无关（规则「自比同形状」）。"
    "⇒ 本机启动快慢的唯一变量是 pack 在不在页缓存；要真正加速只能等 #3624 的 O_DIRECT 分支。"
)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], rows[1:]
for r in body:
    if r and r[0] == "P141":
        r[10] = r[10] + ADD141
if "P143" not in {r[0] for r in body}:
    body.append([
        "P143", "ENV", "STRATA_UNBUFFERED_LOAD", "1", "startup/arena", "REJECTED",
        "-", "-", "-",
        "`src/core/expert_source.cpp:864/2495`（本构建只用来抬高 reader 数）；`src/core/pinned.cu:827`"
        "（非 Windows 恒返回 buffered）；上游 #3624（open，才是真正加 O_DIRECT 的那条）",
        V143,
    ])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)
print("rows", len(body), "P141 len", len([r for r in body if r[0] == 'P141'][0][10]))
print("P143", [r[5] for r in body if r[0] == "P143"])
