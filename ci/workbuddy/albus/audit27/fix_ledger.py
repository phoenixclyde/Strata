#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT27 ledger remediation -- fail-closed: every old string must match exactly once."""
import io
import os

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

# (id, new status, text that must be appended to the note)
CLOSE = [
    ("P380", "DONE",
     "【AUDIT27 结清 2026-11-07】两个疑点都已定位：①4% 由 H1(`P382`)/H2(`P383`) 归因到 0.9.0 的 MMQ kernel 重写，"
     "并由 K10/K13 二分(`P390`/`P391`)锁到 #29948 一条；②zh 的 content/reasoning 分区假设已由 W1031 续二撤回"
     "（H2 的 zh 文本回到基线 `这段话主要说明：`）。注意 `P388` 已证明长提示逐字节贪心指纹不可重复，"
     "故本条的『分区变化』不能再作为数值证据；结论按『已定位 + 证据降级』结清，不再待办。"),
    ("P343", "DONE",
     "【AUDIT27 结清 2026-11-07】W1020/W1021 已完成：改挂 pin 的 `llama_3cf0325`（166 上四个 ref 中**只有它有** "
     "`ggml/src/ggml-cpu/iqp.cpp`，b10700/b12099/b12110 均无，2026-11-07 现场复核）+ 两处 ggml API 修正 ⇒ "
     "全量 154/154 LINK_OK、`strata-0.1.57-001` 部署（`W832` §6.5 回写·W1020/W1021）；`W994` 另证 build.ninja 可重生成。"
     "原『v0.2.11 需要比 b12110 更新的 ggml』属指向错误参考树，已更正；`build-r28/strata` 缺失的副作用随重编消失。"),
    ("P346", "DONE",
     "【AUDIT27 结清 2026-11-07】W1020 已把 `_ci_all.txt` 154 条命令的宏全改 0.1.57（`0.1.56` 计数 0）并重编；"
     "W1021 完整 review 第 3/4/5 项复核 `strata --version` = **0.1.57**、`BUILD-IMAGE.json` engine = 0.1.57、"
     "运行引擎 `/data/bin/strata-0.1.57-001` md5 `5e63174d…`。四指针已一致，本条不再 OPEN。"),
    ("P359", "DONE_NEG",
     "【AUDIT27 结清 2026-11-07】该『下一步』已由 R99/S1 做完并判否：`exp/lcpp-b12169`=`7fdd5d3c` 自建 tile_spec，"
     "W1027 首轮 75-token 503（后证不可复现，`P375`），W1030 重跑三例 48-token 指纹全不同、2K 直接 HTTP 503 ⇒ "
     "**算错而非慢**，`R99` = DONE_NEG(`P374`)。保留分支与 `-003` 供将来对齐语义，本条不再作为待办。"),
]

NEW = [
    ("B8工程", "P393", "AUDIT27：机械判定未审区间（W1006–W1031 共 26 轮）+ 补审 W706/W707 + 新门 audit_scope", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：`albus/audit27/scope.py` 从记忆件标题 / `deploy/W*.md` / `PROGRESS.source` 取并集，"
     "与 `AUDIT_INDEX.md` 的覆盖区间求差（支持 4 位轮号，旧 `audit12_scope.py` 的 `W(\\d{3})` 会把 W1006 读成 W100）；"
     "AUDIT26 到 W1005 为止 ⇒ 26 轮全部首次被审。`tools/audit_scope.py` 新增『审计债』硬门：尾部未审轮次 > 8 即 FAIL。",
     "deploy/AUDIT27_W1006_W1031.md §1"),
    ("B8工程", "P394", "§0.1 唯一事实块的分母与队列过期；新增 plan_facts_lint 派生校验", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：`W832:24` 仍写 309/229/74.1%（W1030 的数），实际 340/259；`W832:28` 的队列与 `albus/w1031/reply.md:24` "
     "互相矛盾（前者 R95 起且含 R89，后者 R51 起且丢 R89），且 §6.5 仍写『R100-S5 插到最前』而 R100 已 DONE_NEG。"
     "⇒ 三处统一到 §0.1，队列每个 R 号都有账本行；`tools/plan_facts_lint.py` 把分母改为从 `PROGRESS.tsv` 派生，写死即 FAIL。",
     "deploy/W832_OPT_PLAN_V2.md §0.1"),
    ("B8工程", "P395", "AUDIT_INDEX 的 AUDIT25 行漏 P 分级（2/7/6）⇒ 合计少 15；fix_total 硬编码 W1005", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：`AUDIT25_W952_W985.md §1` 明写 P0=2 / P1=7 / P2=6，索引该行四列全是 `—` ⇒ 合计 36/129/110/7 少算 15 条；"
     "`tools/audit_index.py:83` 的 `--fix-total` 把『W776–W1005』写死在函数里，新增审计后必然写错边界。均已改：补行、"
     "边界由覆盖表最大轮号派生、`check()` 增『合计≠逐行和即 FAIL』。",
     "deploy/AUDIT_INDEX.md"),
    ("B8工程", "P396", "四条已解决却仍 OPEN 的账本行（P380/P343/P346/P359）", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：同 AUDIT26 F3 的形态（R88 假设被自己证伪仍 OPEN）。四条的后续证据分别在 W1031 续二/续四、"
     "W1020/W1021、W1030，均已逐条写回 note 并改状态；`P309`/`P335` 仍 OPEN 属真未做，已补解除条件。",
     "deploy/PROGRESS.tsv"),
    ("B8工程", "P397", "§6.6 R99 四阶段方案源头无关闭横幅；W1026 在方案里 0 落点", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：R99 已于 W1030 判 DONE_NEG(`P374`)，但 `W832` §6.6 的四阶段表仍以现行指令形态存在，"
     "顺文档执行会重做一次已否掉的实验；且全文 `\bW1026\b` 命中 0（该方案立于 W1026）。已在 §6.6 抬头加关闭横幅 + W1026 落点。",
     "deploy/W832_OPT_PLAN_V2.md §6.6"),
    ("B8工程", "P398", "【P0】lcpp_picks 活流程文档仍命令已废止的逐字节贪心指纹门，且仍写 #29953 REJECTED；本地快照与分支漂移", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：`ci/lcpp_picks/README.md` §3 第 5 步逐字『48-token 贪心指纹三例（/tmp/greedy_fingerprint.py）…逐字节相同才算无变化』，"
     "而 `P388` 已实测同一引擎同一提示两次就不同（en2k 234 vs 242、zh2k 82 vs 79），脚本文件在断电后也不存在；§6 仍写"
     "『ladder-5 回答退化 ⇒ #29953 REJECTED』，与 `P389`/`P390` 及分支 `PICKS.tsv` 的 ADOPTABLE 直接冲突。"
     "⇒ 双份 README 加撤回横幅并换判据（prefill-only LOGPOS / `quant_quality` 相对门），`apply.sh` 状态枚举补 ADOPTABLE，"
     "本地 `albus/w1031/lcpp_picks_*` 与分支 `252ec8ff` 同步；`tools/audit_scope.py` 拦『废止门以现行指令出现』。",
     "deploy/AUDIT27_W1006_W1031.md §3"),
    ("B8工程", "P399", "W1020 缺 reply.md（违反 P329 唯一副本）；mirror_check 把『最新审计件』写死成 AUDIT26", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立**：W1006–W1031 共 26 轮，25 轮有 `albus/<轮>/reply.md`，唯 W1020 没有（其结论只在 `W832` §6.5 回写·W1020 "
     "与 P344–P347）。已写审计补录件并**明确标注非原始报告**、不伪造当时十字段；`albus/w1003/mirror_check.py` 的 FILES 改为"
     "按 `AUDIT(\\d+)_` 最大编号派生，否则 AUDIT27 之后 166 仍留着旧审计件而索引已前移（两份副本、门只看得见一份）。",
     "albus/w1020/reply.md;albus/w1003/mirror_check.py"),
    ("B8工程", "P400", "外网复核 5 条上游引用的适用范围 + 历史轮次补审登记", "W1032",
     "count", "1", "1", "DONE",
     "**W1032 立（GitHub API / 官方文档，逐条）**：#29948 正文写明只覆盖 **NVIDIA Turing+**（DGX Spark Q4_K_M +7.1%、"
     "5090 +1.9~4.7%），gfx906 不在融合面；#31047 的 **1.23×** 只是 `MI60 / MI50 · granitemoe 3B Q4_0 · mb=64 · pp8192` 单一格，"
     "merged 2026-11-05；ORT #32182 4.54×@T=1024 是 **closed 未合并**、只用 `mma.sync.m16n8k16`(sm_80+) 且正文自述 FLA 在 T>1024 反超；"
     "tandem.cpp 的 3.3× 是 **GSM8K decode tok/s**（29.8→97.3，单 4090 + IQ3_S + MTP），不是 prefill；#29478 的 MI50 收益（TG128 +8.54%）"
     "主要来自同 PR 的 FATTN Q4_0 屏障，而该文件**不在我们的 26 个 MMQ TU 编译面** ⇒ 为 W1031『零效果』提供第二种解释。"
     "另 W706/W707 属 era 之前仅历史轮次、W854/W855/W884/W885 经复核无此轮、W863 由 AUDIT18 单轮覆盖，均登记不追审。",
     "deploy/AUDIT27_W1006_W1031.md §4"),
]


def main():
    src = io.open(P, encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    out = []
    seen = set()
    for ln in lines:
        f = ln.rstrip("\n").split("\t")
        if len(f) >= 10 and f[1] in {x[0] for x in CLOSE}:
            match = [x for x in CLOSE if x[0] == f[1]][0]
            assert f[1] not in seen, "duplicate id " + f[1]
            seen.add(f[1])
            assert f[7] == "OPEN", "%s status is %s, expected OPEN" % (f[1], f[7])
            f[7] = match[1]
            f[8] = f[8].rstrip() + "  " + match[2]
            ln = "\t".join(f) + "\n"
        out.append(ln)
    assert seen == {x[0] for x in CLOSE}, "missing: %s" % ({x[0] for x in CLOSE} - seen)
    # append new rows; do not insert a blank line (progress.py counts rows)
    for r in NEW:
        assert len(r) == 10, r[1]
        assert "\t" not in "".join(r), "tab inside a field: " + r[1]
        out.append("\t".join(r) + "\n")
    io.open(P, "w", encoding="utf-8", newline="\n").write("".join(out))
    print("CLOSE", ",".join(sorted(seen)), "| NEW", ",".join(r[1] for r in NEW))


if __name__ == "__main__":
    main()
