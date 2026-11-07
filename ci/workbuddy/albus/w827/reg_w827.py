# -*- coding: utf-8 -*-
"""W827：v0.2.8 / 引擎 0.1.54 判定落账。"""
import csv, os

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "params", "PARAM_REGISTER.tsv"))
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], [r for r in rows[1:] if r and r[0].strip()]
ids = [r[0] for r in body]

NEW = [
    ["P178", "upstream", "engine 0.1.53 -> 0.1.54（tag v0.2.8）", "暂不升",
     "governance", "DEFERRED", "—", "—", "P152/P160/P172",
     "v0.2.8（2026-10-29 22:40 UTC）发布，引擎 0.1.54。本轮查证：70 提交 / 148 文件，引擎面 42 个，"
     "核心只有一件事 —— **verify 窗口从 8 行放到 16 行**（HIP 独占，CUDA 因 48 KB 共享内存限制保持 8）。"
     "`include/strata/kernels/window_limits.hpp`（新增）逐字：`a window of up to kVerifyNarrowT (8) rows runs "
     "EXACTLY the code it ran at 8 … the wider code is reached only by a window of 9..16 rows`。"
     "我们 `--spec 4`、`--suffix-draft` 未设（默认 3、最多到 8）⇒ 窗口 5-8 行 ⇒ **逐位等价、零速度收益**。"
     "正文给的 R9700 decode +8.1%（73.7→79.7）是综合结果，来源正是 16 行窗口，我们拿不到。",
     "**暂不升**。逐条对照用法后能命中的只有两条，且都不在关键路径："
     "①#4474 自动专家缓存保留 reserve（我们用 `--expert-cache auto` + headroom 0.5）；"
     "②#4051 新引擎等旧引擎释放内存（只在重启时，W826 撞过 `memory guard 105.4 GiB`）。"
     "**不命中**：#4420 park 丢前缀（`--batch` 未设）、#4518 PLE 锁定时对话缓存（我们 PLE 未锁）。"
     "工具调用容错（98.3% vs 92.9%）在 `serve/frontend.py +242` / `serve/server.py +77`，属 **server 层**，"
     "混版本有耦合风险，不单独更新。"
     "**触发条件（写死）**：任一成立即升 —— ①要把 `--spec` 提到 5+ 或窗口超 8 行（0.1.53 会拒 `max_t > kVerifyMaxT`）；"
     "②要开 `--batch` / `--parallel`（那时 #4420 命中且需 16 行窗口）；③上游出现 gfx906 相关的速度/正确性修复；"
     "④出现只在本版修、且我们实际踩到的缺陷。"],

    ["P179", "measurement", "calibrate 与引擎版本耦合（顺序约束）", "先定引擎版本，再跑 calibrate",
     "measurement", "REFERENCE", "—", "—", "P160/P178",
     "`tools/calibrate.py` 要启动引擎跑真实 prefill/decode，标定 `--spec-min-p`（跟 verify 行为相关）、"
     "`--adapt-*`（跟 VRAM 专家层跟随相关）、`--pool-workers`、`STRATA_SH_STREAM`。"
     "引擎版本一变，这些结论都可能变。",
     "**顺序写死**：先决定升不升引擎，再跑 calibrate。本判定为「暂不升」⇒ **P0 可直接在 0.1.53 上跑，不必等**。"
     "若将来因 P178 的触发条件 1/2 升级，**calibrate 必须重跑**，这条要进那时的执行清单。"],
]

added = []
for r in NEW:
    if r[0] in ids:
        print("skip", r[0]); continue
    body.append(r); added.append(r[0])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr); w.writerows(body)

print("added:", added)
print("rows:", len(body), "cols_ok:", all(len(r) == 11 for r in body))
