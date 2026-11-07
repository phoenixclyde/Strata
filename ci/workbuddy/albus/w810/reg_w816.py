# -*- coding: utf-8 -*-
"""W816-W818 落账：
  P141 的「答案等价性判不了」补上根因；
  新增 P144（--spec 0/1 结构性不可用）、P145（RT_SKIP=0 换复现性，否）。
"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"

TAIL_141 = (
    "【W816 定案：判不了的原因】不是「没测」，是**这个构建同一进程内就不可复现**："
    "同输入连发 6 次（temperature 0、96 token）出 **3-5 个不同答案**，最早在第 ~13 token 分岔，"
    "呈**多吸引子**（P1：R0=R3=R4 / R1=R2 / R5 各成一簇）。chunk 恒定（`lent 191 slots for 256 tokens`）"
    "⇒ 与启动期选路径无关；专家档案读的是镜像内固定文件 ⇒ 也无关。详见 `W816_DETERMINISM.md`。"
)

V144 = (
    "**N/A（结构性不可用，规则 Q 直接登记）**。`--spec 0` 会让引擎直接拒绝启动，日志逐字："
    "`is a native (IQ) pack: it needs --native SHARD1, --spec T (T >= 2) and --prefill CHUNK`；"
    "源码 `generate.cpp:4247` 也是 `o.spec < 2` 就不走 MTP 路径。⇒ **本 pack 上不存在「关掉投机」这一档**，"
    "「关掉投机看是否确定」这条路走不通（W817 已实测，启动即失败，原始件保留作证）。"
)

V145 = (
    "**REJECTED（W818 实测，且反向）**。假设是「尾跳依赖 miss，而 miss 随缓存演化 ⇒ 同输入走不同分支」，"
    "于是把 `STRATA_ROUTE_TAIL_SKIP` 由 7 改成 0 测复现性：**6 次同输入出 5 个不同答案**"
    "（生产 RT_SKIP=7 是 3 个）⇒ 尾跳不是不可复现的元凶，关掉它只会更糟（还白丢 +6.5% 解码，见 P127）。"
    "复现性在参数面里**无解**：残下的解释是批形状 / 专家驻留集合导致的浮点归约差异。"
)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], rows[1:]
for r in body:
    if r and r[0] == "P141":
        if "W816 定案" not in r[10]:
            r[10] = r[10] + TAIL_141
have = {r[0] for r in body}
if "P144" not in have:
    body.append(["P144", "CLI", "--spec 0|1", "(不可用)", "decode/spec", "N/A",
                 "-", "-", "P127",
                 "`generate.cpp:4247`（`o.spec < 2` 不走 MTP）+ 启动期拒绝：native IQ pack 要 T >= 2（`w817_spec0_*.txt`）",
                 V144])
if "P145" not in have:
    body.append(["P145", "ENV", "STRATA_ROUTE_TAIL_SKIP=0（为复现性）", "7(生产)", "decode/determinism", "REJECTED",
                 "-", "P127", "-",
                 "`expert_source.cpp:4853-4862` 的尾跳条件；`ab_p48.sh` + `mt_det2.py` 实测",
                 V145])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)
print("rows", len(body), "cols_ok", all(len(r) == 11 for r in body))
print([r[0] for r in body][-4:])
