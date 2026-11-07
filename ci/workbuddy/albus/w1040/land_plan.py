#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: update §0.1 (facts + queue), append the §6.5 回写 block and its directory row."""
import io, os, shutil, time

ROOT = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
s = io.open(PLAN, encoding="utf-8").read()
shutil.copy2(PLAN, PLAN + ".bak_w1040_" + time.strftime("%Y%m%d_%H%M%S"))

OLD_ENG = ("| 引擎 md5 / 大小 | **`d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B（`strata-0.1.57-b12180`，"
           "llama.cpp b12180 == master `bcb01528` + mmq@4c1004c）**；回滚 `strata-0.1.57-k10p` = "
           "`e0a6987f732a401f780f5dad5812812f`，更早 `strata-0.1.57-001` = `5e63174dbd7cc04e5fa1b5fc455b2a73` | "
           "disk = build = running 三方 |")
NEW_ENG = ("| 引擎 md5 / 大小 | **`a85743d7f554159e8ac1e2d432d2e5ea` / 43,214,976 B（`strata-0.1.57-kvg`，"
           "= b12180 的同一棵树 + `vmm.cpp` 一处条件改 OR，让 gfx906 走 HIP VMM；`--kv-grow` 在生产开启）**；"
           "回滚 `strata-0.1.57-b12180` = `d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B，更早 "
           "`strata-0.1.57-k10p` = `e0a6987f732a401f780f5dad5812812f`、`strata-0.1.57-001` = "
           "`5e63174dbd7cc04e5fa1b5fc455b2a73`（`/data/bin` 共 53 件） | disk = build = running 三方；"
           "`docker exec md5sum /data/bin/strata-0.1.57-kvg` |")

OLD_CFG = ("| config md5 / args / env | **`5e9b81e2f66ca48999766d2ae0201fb6`**（`exe=/data/bin/strata-0.1.57-b12180`）/ "
           "37 / 9 | 同上 |")
NEW_CFG = ("| config md5 / args / env | **`ee69ebc272ce41a116f50ecb3bf0edc2`**（`exe=/data/bin/strata-0.1.57-kvg`，"
           "args 多且仅多 `--kv-grow`）/ **38** / 9 | 增量门 `tools/deploy_gate.py --cfg-base/--cfg-new --reg-ids P32`；"
           "旧值 `5e9b81e2…`（37 args）是回滚面 |")

OLD_DEN = "| 进度分母 | **432 条 / 已结 345 / 79.9%**（W1039 校正；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
NEW_DEN = "| 进度分母 | **438 条 / 已结 351 / 80.1%**（W1040；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"

OLD_Q = ("| **唯一队列** | **R104（进行中，`P472`–`P474`：VMM 已证可用、候选 `kvg` 已建、待窗口）** → ")
NEW_Q = ("| **唯一队列** | **R104 已结（W1040 装机：`P490`，`kvg` + `--kv-grow` 进生产，槽 7463→8301、"
         "config `ee69ebc2`、停机 275 s、D4 逐位相同）** → **R106（新立，`P492`：`gen_config` 与生产 config "
         "九处漂移，改参唯一道的工具链要先对齐；`P491` 的 D5 增量门是临时桥）** → **R105（")

for old, new, tag in ((OLD_ENG, NEW_ENG, "eng"), (OLD_CFG, NEW_CFG, "cfg"),
                      (OLD_DEN, NEW_DEN, "den"), (OLD_Q, NEW_Q, "queue")):
    assert s.count(old) == 1, (tag, s.count(old))
    s = s.replace(old, new)
print("§0.1 updated: eng/cfg/den/queue")

BLOCK = """
---

### 回写 · W1040（2026-11-07 14:10–14:14）R104 装机：`--kv-grow` 落生产，**+838 槽**，数值逐位不变

> 停机 **275 s**（14:10:03 停 → 14:14:38 健康），一次停/起；回滚件 `b12180`（`d24f8293`）与 config 备份都在位。

- **门槛在「改的那行到底编进去了没有」**：`vmm.cpp:167` 的条件从 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 改成 `(STRATA_USE_HIP || STRATA_HIP_GFX906)`。只删 `!defined` 的那一版**编过了、md5 却没变**（`P473`）——该 TU 的 `DEFINES` 里只有 `-DSTRATA_HIP_GFX906=1`，没有 `-DSTRATA_USE_HIP` ⇒ 条件仍假、stub 又编一遍。**判据只能是「二进制变了吗」**：`nm -D` 里 `hipMemAddressReserve`/`hipMemCreate`/`hipMemMap`/`hipMemSetAccess` 新件各 1 条、在产 0 条。这是 `P425`/`P441`/`P446` 之后同族第四次「改了没在跑」。
- **装机门首次真的判了配置面（`P491`）**：`tools/deploy_gate.py` 的文档写着 D1–D6，代码里一直只有五条——**D5「改参唯一道」从来没被机械验过**。本轮补成**增量门**：新 config 除 `exe` 外，只能多出本轮 ADOPTED 行声明的 CLI flag / ENV，少了任何键也拒；D3 同时扩成「延迟型 / 容量型」两类目标（容量型的目标量是整数槽数、零方差，墙钟降级为护栏）。**门输出**：D1 `a85743d7…`、D2 53 件、D3b 槽 7463→8301、D3c 四条护栏全在 2×CV 内、D4 逐位相同、D5 `args +--kv-grow（来自 P32）` ⇒ PASS。
- **数值证据换了取样面（`P495`）**：不是「再跑一次 KL 门」，而是比 **batched prompt 路径的 float32 全词表 logits**（993,280 B/个），1000/8000/16000/**20000** 四个长度，两臂（`b12180` vs `kvg`+`--kv-grow`）**四个文件逐字节相同**，`pcompare` = `top-1 100.00% / KL 0.00000`。1000–16000 三点 ≤ `STRATA_KV_GROW_INIT`(16384)，本来就不该增长，是对照；**20000 那一点强制增长，位仍没动**——这一条才是真正的结论。
- **为什么增长了还不掉位（`P494`，源码 + 日志互证）**：一次 20K 请求只借 **19 槽**（生产 28.7K 上是 25–55 槽），且让出的是「prompt path loan 正下方」的中等热度槽，其中 **15 个更热的专家被搬到更冷者的槽里**，被真正赶走的只有剩下的几个，而这段文本没有路由到它们 ⇒ **驻留集合近似不变，只有槽号变**。原文：`K/V grown to 20512 cells (0.26 GiB); the expert cache gave 19 slots for it, 15 hotter experts moved to colder ones' slots (1896 of 1915 slots hold experts)`。
- **生产现场（新日志切片，不整文件 grep）**：`expert cache 8301 slots, 24.23 GiB`、`elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB)`、**没有** `--kv-grow is off`；增长/归还都实跑过（`grown to 24576/32768 cells`、`trimmed to 8192 cells; 55/80 slots back … refilled from the profile`），无 `could not map`、无 `ERR the K/V could not give its VRAM back`。**功能面**：28,695 token 的 needle 安装前/后都命中（38.6 → 39.0 s，两臂 `cached_tokens=0`）。
- **取数纪律（`P493`）**：`elastic K/V` 行**不能整文件 grep** —— 日志是 append-only，上一次窗口的旧行会让新检查假通过（装机后 `tail -2` 仍拿到 13:44 那次的行）。凡「引擎自报状态」的门一律**按启动/请求切片**读：`P478` 的门本身对，取样面错了。
- **一个必须记账的工具链缺陷（`P492` → `R106`）**：`gen_config --live` 与生产 config 差 **9 处**——4 个在用 env（`STRATA_GFX906_TUNED`/`DECODE_TIMING`/`SPEC_DEPTH`/`PREFILL_TIMING`）登记成 MEASUREMENT/POLICY scope 不生成，3 个 ENV 行的 name/value 混进注释（会生成 `STRATA_GFX906_ATTN_REDUCE12=1（…）` 这种垃圾键），`tokenizer`/`model_name` 还停在 IQ4_XS。**照铁律原样执行会把 `GFX906_TUNED=1` 丢掉**（全部 tuned kernel 的总开关）⇒ 本轮改参走「在产 config ⊕ 声明增量」，工具链对齐另立 `R106`。
- **代价面仍未定量**：decode 侧 tok/s 跨 run 2×CV 28%，只作方向证据（CPU experts 0.64→0.49、VRAM hits 25.28→29.09）。**下一步**：`R106`（工具链）与 `R105`（`hipk` 三开关，搭车测 `STRATA_HIP_QUEUE_PRIME`）。
"""

DIR_ROW = ("| `回写 · W1040（2026-11-07 14:10–14:14）R104 装机：`--kv-grow` 落生产，**+838 槽**，数值逐位不变` | "
           "停机 275 s；`vmm.cpp` 一行 OR 让 gfx906 走 VMM；槽 7463→8301；四个长度（含 20000）fp32 logits 逐字节相同；"
           "顺手补上从未实现的 D5 增量门与容量型 D3 |")

# directory: insert as the last row of the 6.5.0 table (before the block's trailing separator/next heading)
i0 = s.index("### 6.5.0 回写块目录")
t0 = s.index("| 小节 |", i0)
tend = s.find("> **【AUDIT27", t0)
tend = tend if tend > 0 else t0 + 40000
last = s.rfind("| `回写 ·", t0, tend)
i1 = s.index("\n", last) + 1     # insert right after the last directory row
head, tail = s[:i1], s[i1:]
assert "| 小节 |" in head
s = head + "\n" + DIR_ROW + tail
assert s.count(DIR_ROW) == 1

s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
print("plan bytes", os.path.getsize(PLAN))
