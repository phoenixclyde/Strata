#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT27: repair the single-source-of-truth plan + a stale ledger note."""
import io

PLAN = "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
PROG = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"


def sub(src, old, new, label):
    assert src.count(old) == 1, "%s: expected 1 occurrence, got %d" % (label, src.count(old))
    return src.replace(old, new, 1)


def main():
    s = io.open(PLAN, encoding="utf-8").read()

    s = sub(s,
            "| 进度分母 | **309 条 / 已结 229 / 74.1%** | `deploy/PROGRESS.tsv`（唯一分母） |",
            "| 进度分母 | **342 条 / 已结 260 / 76.0%**（AUDIT27 校正；值由 `tools/progress.py` 派生，"
            "`tools/plan_facts_lint.py` 拦手写） | `deploy/PROGRESS.tsv`（唯一分母） |",
            "denominator")

    s = sub(s,
            "| **唯一队列** | **R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50**"
            "（`R99` 已于 W1030 判 **DONE_NEG**：tile_spec 版算错且基准下 503；"
            "`R21`/`R98` 已于 W1013 判源码、W1014 判实测） | 本节 + `§6.5` 各回写块 |",
            "| **唯一队列** | **R51**（W1031 重开：先补 `P392` 的 prefill-only 数值门，再在 10-19 栈上限内做单点 A/B；"
            "账本 `R51` 仍记 W904 原题的 DONE_NEG，重开证据 `P390`/`P391`/`P392`）→ **R95** → **R94** → **R91** → "
            "**R89** → **R46** → **R49** → **R50**；`R99`(W1030)、`R100`(W1031) 均 **DONE_NEG**，"
            "`R101` OPEN 随 `P392`，`R102` DONE_NEG(`P391`) | 本节 + `§6.5` 各回写块；**AUDIT27 校正** |",
            "queue")

    s = sub(s,
            "> **2026-11-06 重排（W1031）**：",
            "> **【AUDIT27 更正 2026-11-07】** 下面这行「R100-S5 插到最前」是 W1031 当时的排期，**S5 已完成、R100 已判 DONE_NEG**"
            "（H1 `P382` 排除 #31247、H2 `P383` 把 3.8% 归到 MMQ kernel 重写、K10/K13 `P390`/`P391` 锁到 #29948）；"
            "现行队列**只认 §0.1 那一行**。本节余下文字是历史决策记录，不再作为执行顺序。\n>\n"
            "> **2026-11-06 重排（W1031）**：",
            "s5 banner")

    s = sub(s,
            "### §6.6 R99 — 把生产 llama.cpp 升到最新：四阶段方案（单变量、每阶带退出判据）",
            "### §6.6 R99 — 把生产 llama.cpp 升到最新：四阶段方案（单变量、每阶带退出判据）\n\n"
            "> **【已关闭 · W1030 · DONE_NEG】** 本节立于 **W1026**，是当时的方案记录；"
            "**R99 已于 W1030 关闭**（`P374`：S1 自建 `tile_spec` 算错、48-token 指纹三例全不同、2K 直接 HTTP 503，"
            "`P375` 同时更正 W1027 的 75-token hang 不可复现）。**不要按本节再执行 S0–S4**；"
            "保留物 `exp/lcpp-b12169`=`7fdd5d3c`、`strata-0.1.57-003`，见 §6.5「八、R99 关闭」。AUDIT27 补回源头横幅与 W1026 落点。",
            "r99 banner")

    s = sub(s,
            "**5. 所以「镜像和容器跟上游」的准确代价**（`P343`，下一步，未做）：",
            "**5. 所以「镜像和容器跟上游」的准确代价**（`P343`，**AUDIT27 更正：已于 W1020/W1021 做完，状态已结**）：\n\n"
            "> `W1020` 改挂 pin 的 `llama_3cf0325`（166 上四个 ref 中只有它含 `ggml-cpu/iqp.cpp`，2026-11-07 现场复核）"
            "+ 两处 ggml API 修正 ⇒ 154/154 LINK_OK；`W1021` 复核 `--version`=0.1.57、四指针对齐。"
            "下面五步保留为当时的判断，不再作为待办。\n",
            "p343 banner")

    s = sub(s,
            "#### 6.2.1 配置 / 环境面条目（同一套规则，只是不动源码）",
            "> **【AUDIT27 外网核实】** `P391` 的 −5% 有一条硬件前提此前没写：上游 #29948 的 PR 正文逐字限定 "
            "**Q4_K/Q5_K/Q6_K/Q8_0/IQ4_XS on NVIDIA Turing+**（DGX Spark Q4_K_M +7.1%、RTX 5090 +1.9~4.7%），"
            "gfx906 根本不在融合面，且我们 `mmq_args.fusion = {}` ⇒ `fusion.gate == nullptr`。"
            "所以 K13 的退化是 **kernel 体 codegen 代价**，不是「融合在跑却更慢」；R102 已据此判 DONE_NEG。\n\n"
            "#### 6.2.1 配置 / 环境面条目（同一套规则，只是不动源码）",
            "r51 web note")

    tail = """
### 回写 · AUDIT27（2026-11-07 01:xx）审计 W1006–W1031 共 26 轮

机主令「审计所有未审计轮次，该上网查一定要上网查」。范围用 `albus/audit27/scope.py` 从产物取差
（记忆件标题 / `deploy/W*.md` / `PROGRESS.source` 的并集，减去 `AUDIT_INDEX` 的覆盖区间），**不是**从索引表往前推。
审计件 `deploy/AUDIT27_W1006_W1031.md`，总判 **1 P0 / 8 P1 / 5 P2，已全部整改或登记**；账本 `P393`–`P400` + `R101`/`R102`。

本件对**本方案**的四处改动：① `§0.1` 分母 309/229 → **342/260（76.0%）**，改由 `tools/plan_facts_lint.py` 从
`PROGRESS.tsv` 派生；② `§0.1` 唯一队列与 `albus/w1031/reply.md:24` 统一（R51 起、保留 R89、R99/R100 不进队列），
队列里每个 R 号都有账本行；③ `§6.6` 抬头补 R99 关闭横幅 + W1026 落点（此前全文 `\bW1026\b` 命中 0）；
④ `§6.5` W1019 块的「P343 下一步未做」改为已结，并补 `§6.2` 的 #29948 硬件前提。

**外网复核结论（写进 `deploy/AUDIT27_W1006_W1031.md §4`，不在本方案复制数字）**：
#29948 只覆盖 NVIDIA Turing+；#31047 的 1.23× 只是 MI60/MI50·granitemoe Q4_0·mb=64 单一格；
ORT #32182 是 closed 未合并、FLA 在 T>1024 反超；tandem.cpp 的 3.3× 是 decode tok/s；
#29478 的 MI50 增益来自我们不编的 FATTN 屏障（为 W1031「零效果」提供第二种解释）。

**新门**：`tools/audit_scope.py`（审计债 / 废止门 / 缺报告 / 无账本 R 号 / 分母，任一项 FAIL 即 `ROUND_CLOSE` 不过）、
`tools/plan_facts_lint.py`、`tools/audit_index.py` 的合计与边界派生、`tools/plan_lint.py` 的三位数 R 号。
生产零改动（未重启、未换引擎、未改 config）。
"""
    s = s.rstrip("\n") + "\n" + tail
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

    p = io.open(PROG, encoding="utf-8").read()
    p = sub(p, "实际 340/259；", "实际 342/260（76.0%）；", "p394 note")
    io.open(PROG, "w", encoding="utf-8", newline="\n").write(p)
    print("plan + ledger notes patched")


if __name__ == "__main__":
    main()
