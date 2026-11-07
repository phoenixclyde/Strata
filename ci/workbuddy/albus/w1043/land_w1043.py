#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Land W1043: ledger rows, plan write-back, snapshot, daily memory."""
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
HAND = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")

ROWS = [
    ["B8工程", "P506",
     "四项报告**第一张表连续五轮是 RAGGED**：`3a`/`3b` 从三列写成两列，GFM 补出空的「值」单元格，超长第二列把表撑出视口",
     "W1043", "count", "1", "1", "DONE",
     "**W1043 实测（机主「第一张是空表」）**：`albus/w1043/audit_tables.py` 普查 w1000–w1042 —— "
     "**w1000–w1037 全 OK，w1038/w1039/w1040/w1041/w1042 连续五轮 RAGGED**（表头 3 列、数据行 2,3 混）。"
     "装 python-markdown 3.11.3 真实渲染（`render_check.py`）：四轮第一张表 `<tbody>` 都有 12 行，"
     "但**第 9/10 行的第三个 `<td>` 为空**、该行文本 272–434 字符 ⇒ 机主看到的「空表」是「值列空 + 表格超宽」，"
     "不是文件真的没有数据（这点如实写，不夸大）。**根因**：W1037 的正常形态是 "
     "`| 3a | args（19 flag） | … |` 三列，W1038 起被写成 `| 3a args 明细 | … |` 两列。"
     "**外证（上网核）**：GFM spec「表头与分隔行列数不等则整段不识别为表；数据行少列补空单元格；无数据行不生成 `<tbody>`」、"
     "markdownlint MD056/MD058。**修法**：`fix_tables.py` 把五轮共 10 行修回三列，复验 `survey_fourpart.py` 全 OK、"
     "渲染后无空单元格；`tools/report_lint.py` 新增 T0–T4 结构门（表头/分隔列数、≥10 数据行、逐行列数、值非空、前后空行），"
     "`--self-test` **6/6**（空表/少列/空值/列数不等/无空行/正常）。**同族第五次**：门只查「全文有没有关键词」，"
     "不查表里有没有内容 —— 与 P493 取样面、P496 验错件、P500 读死文件同源。",
     "P493;P496;P500", "KW:RAGGED|W1038|6/6"],

    ["B8工程", "P507",
     "四件套的两份权威模板仍写「8 字段」，实际报告早已是 10 字段（+ROCm / llama.cpp）",
     "W1043", "count", "1", "1", "DONE",
     "**W1043 源码核实**：`deploy/REPORT_TEMPLATE.md:9` 与 `deploy/REPORT_STANDARD.md:8` 都写「固定 8 项」，"
     "而 W1025 起报告表里有 9 ROCm / 10 llama.cpp 两行、另有 3a/3b 明细 —— **权威件与实际格式漂移了 18 轮没人管**。"
     "本轮把两份模板同步为「10 项 + 3a/3b」，补上 W1043 表格结构铁律（三列、空行、没数据写 `—`、T0–T4 拦截），"
     "自检清单加 `--self-test`。`tools/report_depth.py` 的口径文字仍是历史下限（≥9 行），本轮不动阈值，"
     "只把结构判定集中到 `report_lint.py` 的 T 门，避免重复设卡。**判据**：`plan_lint` / `report_lint` / `report_depth` 全 PASS。",
     "P506", "KW:10 字段|REPORT_TEMPLATE|REPORT_STANDARD"],

    ["B5本机缺口", "P508",
     "装机门 D3 的两条判据**方向都反了**：显著变慢会被当成「真收益」，大幅变快会被「不劣化」判 REFUSE",
     "W1043", "count", "1", "1", "DONE",
     "**W1043 实测**：拿 `albus/w1043/ab_attn.json` 跑 `deploy_gate.py --live`，"
     "D3c 报 `prefill_16000_gpu Δ=-1.72% vs 带宽 0.36% ⇒ REFUSE` —— **变快 1.72% 被判成劣化**。"
     "根因：护栏写的是 `abs(gd) <= gb`（双向），而语义是「不许变慢」；"
     "同时 D3b 目标写的是 `abs(delta) >= band`，**显著变慢 2.72% 也会算真收益**。"
     "W1040 的 kvg 装机没暴露，是因为那次护栏 Δ 都小于 2×CV。**修法**：抽出 `latency_target_ok(delta, band)` "
     "（要求 `delta <= -band`）与 `guard_ok(gd, gb)`（要求 `gd <= gb`，变快不限），"
     "`--self-test` **11/11** 含「D3b 显著变慢」「D3c 大幅变快」「D3c 变慢超带宽」六个方向用例。"
     "重跑装机门：8K Δ −2.72% vs −2×CV 1.34% PASS、16K 护栏 PASS。",
     "P491", "KW:D3c|大幅变快|11/11"],

    ["B5本机缺口", "P509",
     "装机门 D4 只认「bitident / 绝对 KL 0.0139」，对 W1041 的锚式取样面会误杀；且 D5/D6 SKIP 时横幅仍写「可以装」",
     "W1043", "count", "1", "1", "DONE",
     "**W1043 修两处**：① `numeric_verdict()` 新增 `mode=anchor` —— 要求 ≥4 个长度每个 "
     "`KL(C) <= KL(D 锚)` 且 `build_floor_bitident=True`；**0.0139 属于已退役的 LOGPOS 取样面**，"
     "W1041 同一对臂两把尺差一个量级（0.04 vs 0.00345），跨仪器引用是错的。锚 D = `--kv fp16`，"
     "即我们为省显存主动放弃的那一档。四长度实测 `0.00037/0.00345/0.01429/0.18750` vs "
     "`0.00155/0.01113/0.01699/0.38387` 全在预算内。② 有 SKIP 就 fail-closed：旧横幅"
     "「PASS — 六条判据全部有证据，可以装」在 D5/D6 都是 SKIP 时照样打印；现在输出 "
     "**`INCOMPLETE — 2 条判据是 SKIP（D5 配置面、D6 证据链），不能据此装机`** 并返回 1。"
     "W1040 历史复验也随之变成 INCOMPLETE（那次 D6 确实 SKIP）⇒ **那次装机的门不是全绿的**，如实记账。"
     "`--self-test` 11/11。",
     "P491;P498", "KW:mode=anchor|INCOMPLETE|D5/D6"],

    ["B6判定探针", "P510",
     "自查纠错：本轮初稿把 W1041「四臂去掉 `--kv-grow`」的旧信息套到 W1042，误判「`attn`+DP4A+`--kv-grow` 组合未测」",
     "W1043", "count", "1", "1", "DONE",
     "**W1043 源码+配置双证（不是推测）**：166 上 `tmp/w1042/cfgP_{kvg,attn}.json` 都是 **38 args 且 `--kv-grow` 为 True**；"
     "`qq_r103.py` 的 `DROP_VALUE`/`DROP_FLAG` **不含** `--kv-grow`，故 P1 数值臂的引擎 argv 保留它；"
     "P2/P3 的 `serve/server.py --config cfgP_attn.json` 用同一份 config。"
     "⇒ **A/B build floor、C 的 logits、2.5K/8K/16K 计时、16K/28K needle 全在带 `--kv-grow` 的形态下跑过**。"
     "初稿已写进 `ab_attn.json` 的 caveat 与 `LONGCTX_GATE.md §0`，发现矛盾（窗口脚本注释写 production-shaped incl. kv-grow）后"
     "逐层核到 argv 才纠正：G1 从「首测组合」降级为**跨窗口复验**，装机窗口不必重跑 1K–20K 四点，停机估算相应下调。"
     "**同族**：与 P500 一样，是「凭上一轮印象代替本轮源码核实」；区别是这次在落权威件**之前**抓到了。",
     "P500", "KW:kv-grow|W1041|组合未测"],

    ["B5本机缺口", "P511",
     "R103 装机前置：长上下文任务级门 G1–G5 预注册 + 可执行网格/判据/窗口脚本；**等停机批准，未执行**",
     "W1043", "count", "1", "0", "OPEN",
     "**W1043 立**。**真缺口（两个）**：① W1042 的任务级门只跑了 16K/28K 各一个深度的 needle（4/4），"
     "而 20K 点两臂都翻 argmax（参考分布 p=0.683/熵 0.83 近掷硬币）；"
     "② `PARAM_REGISTER.tsv` 里没有 `STRATA_GFX906_ATTN_DP4A` 的 ADOPTED 行，**装引擎不加这个 env 等于没装**，D5 会 REFUSE。"
     "**预注册（跑之前写死，`LONGCTX_GATE.md`）**：四臂 A/B/C/D 全部带 `--kv-grow`；"
     "长度 1K–64K 的 fp32 全词表 logits（补 D 锚与 32K/64K）、16K/32K/64K × 深度 0/50/100% × A/C 的 needle 网格、"
     "生成逐 token diff、8K/16K 墙钟；**G1** B≡A 逐位、**G2** 每长度 KL(C)≤KL(D)、**G3** `KL(C)/KL(D)`@64K 不比 20K 恶化 2×、"
     "**G4** C 命中数≥A 且无缓存点、**G5** 不比 A 慢超当次 2×CV；任一不过就原样还原。"
     "**外证（上网核）**：NeurIPS 2026《Length, Not Bit Width》190 runs / 5 深度 × 7 长度 4K–128K，"
     "KV 量化把检索悬崖从 96K 推到 32K、int8 与 int4 失败模式几乎相同；vLLM 128K needle FP8 KV 91%→13% 而短上下文全绿；"
     "RULER/NoLiMa/HELMET 指出只报 vanilla NIAH 是常见错误。**不能直接套的地方**：那些改的是 KV 条目，"
     "R103 改的是 **query 侧点积算术**，KV 一个字节没动 ⇒ 本门用「相对锚的比值随长度是否稳定」证伪该推断，"
     "而不是照搬别人的失败模式。**脚本（零停机自测）**：`longctx_needle.py --self-test` **9/9**、"
     "`judge.py --self-test` **7/7**、`window_install_attn.sh` fail-closed（必须 `APPROVED=1 DRY_RUN=0` 才停生产，"
     "trap 无条件还原，缺 `verdict.json` 就拒装）、`ab_attn.json` 装机门预检 = **INCOMPLETE**（D5/D6 SKIP，按设计）。"
     "**停机**：估 20–30 min（**推测**，由 W1042 28K needle 39.0 s 线性外推，未实测）；**装机 0 / 重启 0 / 停机 0**（本轮）。"
     "**仍缺**：G2/G3 的 logits 接线需先造 `set32k/set64k` ids 集并跑 D 锚；"
     "窗口脚本里该段标 `TODO-BEFORE-RUN`，**不假装一键可装**。",
     "P498;P499;P509;P510", "KW:LONGCTX_GATE|G1–G5|停机批准"],
]


def main():
    lines = io.open(P, encoding="utf-8").read().splitlines()
    have = {l.split("\t")[1] for l in lines if l.count("\t") >= 9 and not l.startswith("#")}
    for r in ROWS:
        assert len(r) == 11 and all("\t" not in x for x in r), r[1]
        whole = " ".join(r)
        for kw in r[10].replace("KW:", "").split("|"):
            assert kw in whole, "%s KW %r missing" % (r[1], kw)
    todo = [r for r in ROWS if r[1] not in have]   # idempotent: the first run wrote the ledger before failing
    # AUDIT29 round count: W1043 is one more unaudited round
    n107 = 0
    for i, l in enumerate(lines):
        f = l.split("\t")
        if len(f) >= 11 and f[1] == "R107":
            f[2] = f[2].replace("11 轮连续未审", "12 轮连续未审")
            f[8] = f[8].replace("`11 unaudited rounds in a row (> 8)`（W1032–W1042",
                                "`12 unaudited rounds in a row (> 8)`（W1032–W1043")
            f[8] = f[8].replace("W1040 W1041 W1042", "W1040 W1041 W1042 W1043")
            f[10] = "KW:AUDIT29|12 轮连续未审|audit_scope"
            lines[i] = "\t".join(f)
            n107 += 1
    assert n107 == 1, n107
    lines += ["\t".join(r) for r in todo]
    io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("ledger: +%d rows (already present: %d)" % (len(todo), len(ROWS) - len(todo)))

    tot = done = 0
    for l in io.open(P, encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
            try:
                tot += int(f[5]); done += int(f[6])
            except ValueError:
                pass
    pct = 100.0 * done / tot
    print("TOTALS %d / %d / %.1f%%" % (tot, done, pct))

    # ---- plan §0.1 denominator + unique queue + audit note
    s = io.open(PLAN, encoding="utf-8").read()
    s = re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1042；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1043；" % (tot, done, pct), s, count=1)
    oldq = "**R103 重开并结、已移植且过任务级门、待装机（W1041"
    newq = ("**R103 重开并结、已移植且过任务级门、待装机（W1043：四件套结构门补上、装机门 D3/D4 方向纠错、"
            "`ab_attn.json` 预检 INCOMPLETE；长上下文 G1–G5 预注册于 `albus/w1043/LONGCTX_GATE.md`，"
            "**等停机批准**；W1041")
    if oldq in s:
        s = s.replace(oldq, newq, 1)

    # ---- write-back block + directory row
    title = "### 回写 · W1043（2026-11-07 16:1x–16:3x）四项报告结构门 + R103 装机前置（零停机）"
    block = """__TITLE__

- **生产零变更**：`strata-0.1.57-kvg`（`a85743d7…`）+ config `ee69ebc2…`；**重启 0 / 停机 0 / 装机 0 / 回滚 0**。
- **机主指出的「第一张是空表」查清了**（`P506`）：w1038–w1042 连续五轮把 `3a`/`3b` 写成两列，GFM 补出**空的「值」单元格**且超长第二列把表撑出视口；真实渲染（python-markdown 3.11.3）`<tbody>` 12 行、第 9/10 行第三 `<td>` 为空。w1000–w1037 全 OK ⇒ 是 W1038 引入的回归。已修回三列并加 `report_lint.py` 的 T0–T4 结构门，`--self-test` **6/6**。
- **权威模板同步**（`P507`）：`REPORT_TEMPLATE.md` / `REPORT_STANDARD.md` 从「8 字段」改为「10 字段 + 3a/3b」，补表格结构铁律。
- **装机门又挖出两条方向错误**（`P508`/`P509`）：D3c 把 **16K 变快 −1.72%** 判成 REFUSE（`abs` 用错方向）、D3b 会把显著变慢算成收益；D4 只认旧仪器的 0.0139，对 W1041 的锚式取样面会误杀；D5/D6 SKIP 时横幅仍写「可以装」。三处全修，`deploy_gate.py --self-test` **11/11**，SKIP 现在 fail-closed 输出 `INCOMPLETE`。**W1040 历史复验也变 INCOMPLETE**（那次 D6 确实 SKIP）——如实记。
- **自查纠错**（`P510`）：初稿把 W1041「四臂去掉 `--kv-grow`」套到 W1042，误判组合未测；核到 `cfgP_*.json` 38 args 含 `--kv-grow`、`qq_r103.py` 的 DROP 表不含它、临时服务用同一 config ⇒ **组合已测**，G1 降级为跨窗口复验，停机估算下调。这次在落权威件**之前**抓到。
- **R103 装机前置**（`P511`，OPEN）：`LONGCTX_GATE.md` 预注册 G1–G5；`longctx_needle.py` 9/9、`judge.py` 7/7、`window_install_attn.sh` fail-closed；`ab_attn.json` 门预检 **INCOMPLETE（D5/D6 SKIP，按设计）**。外证：NeurIPS 2026 长度悬崖（190 runs）、vLLM 128K needle 91%→13%、RULER/NoLiMa；**但那些改的是 KV 条目，R103 改的是 query 侧算术**，本门用相对锚比值证伪推断而非照搬。
- **仍未做 / 不冒充完成**：G2/G3 的 32K/64K logits 需先造 ids 集并跑 D 锚（窗口脚本标 `TODO-BEFORE-RUN`）；`PARAM_REGISTER.tsv` 尚无 `STRATA_GFX906_ATTN_DP4A` 的 ADOPTED 行；停机窗口估 **20–30 min（推测）**，**等机主单独批准**。
- **审计债继续变重**：`audit_scope §A` 现为 **12 轮连续未审**（W1032–W1043，阈值 8），`R107 / AUDIT29` 已同步轮数。本轮四个门缺陷全是**跑门时撞出来的**，不是审计查出来的。
""".replace("__TITLE__", title)
    if title not in s:
        s = s.rstrip("\n") + "\n\n" + block
        # directory row: insert right after the last `| `回写 ·` row of the §6.5.0 table
        t0 = s.index("| 小节 |")
        last = s.rfind("| `回写 ·", t0, s.index("> **【AUDIT27", t0) if "> **【AUDIT27" in s[t0:] else t0 + 60000)
        assert last > 0
        eol = s.index("\n", last) + 1
        row = ("| `回写 · W1043（2026-11-07）四项报告结构门 + R103 装机前置` | "
               "第一张空表查清并固化 T0–T4；装机门 D3/D4/SKIP 三处纠错；G1–G5 预注册待停机 | W1043 |\n")
        s = s[:eol] + row + s[eol:]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("plan written (denominator %d/%d, queue, write-back)" % (tot, done))

    # ---- snapshot
    h = io.open(HAND, encoding="utf-8").read()
    h2, n = re.subn(r"(> SNAPSHOT: round=)W\d{4}", r"\g<1>W1043", h, count=1)
    assert n == 1, n
    io.open(HAND, "w", encoding="utf-8", newline="\n").write(h2)
    print("snapshot -> W1043")

    # ---- daily memory
    m = io.open(MEM, encoding="utf-8").read()
    add = """
### W1043（16:15–16:3x）四项报告「第一张空表」查清并固化 + R103 装机前置（全程零停机）

- **生产零变更**：`kvg`（`a85743d7`）+ config `ee69ebc2`；**重启 0 / 停机 0 / 装机 0 / 回滚 0**。
- **空表根因（P506）**：w1038–w1042 把 `3a`/`3b` 从三列写成两列 ⇒ GFM 补空「值」单元格 + 超长第二列撑爆表；python-markdown 3.11.3 真渲染实证 `<tbody>` 12 行、第 9/10 行第三 `<td>` 空。w1000–w1037 全 OK。修回三列；`report_lint.py` 加 T0–T4 结构门 + `--self-test` 6/6；模板/标准 8→10 字段（P507）。**外证**：GFM spec + markdownlint MD056/MD058。
- **装机门三处纠错**：`P508` D3c `abs(gd)<=gb` 把 16K 变快 −1.72% 判 REFUSE、D3b `abs(delta)>=band` 会把变慢算收益 ⇒ 改单向判据；`P509` D4 加 `anchor` 模式（≥4 长度 KL(C)≤KL(D 锚) + build floor 逐位），SKIP 现在 fail-closed 输出 `INCOMPLETE`（旧横幅在 D5/D6 SKIP 时仍写「可以装」，W1040 复验也中招）。`deploy_gate.py --self-test` 11/11。
- **自查纠错（P510）**：初稿误判「`attn`+DP4A+`--kv-grow` 组合未测」，核 `cfgP_*.json` 38 args 含 `--kv-grow`、`qq_r103.py` DROP 表不含、srv 用同一 config ⇒ **组合已测**；G1 降级为复验。落权威件**之前**抓到。
- **P511（OPEN）**：`LONGCTX_GATE.md` 预注册 G1–G5（长度×深度网格 + 锚比值悬崖判据）；`longctx_needle.py` 9/9、`judge.py` 7/7、`window_install_attn.sh` fail-closed（`APPROVED=1 DRY_RUN=0` 才停，缺 verdict 拒装）；`ab_attn.json` 预检 **INCOMPLETE**（D5/D6 SKIP）。**外证**：NeurIPS 2026 长度悬崖 190 runs、vLLM 128K FP8 needle 91%→13%、RULER/NoLiMa；**不适用于照搬**——那些改 KV 条目，R103 改 query 侧算术。
- **待批**：停机 20–30 min（**推测**，28K needle 39 s 线性外推）；仍缺 32K/64K ids 集 + D 锚 logits、register 的 `STRATA_GFX906_ATTN_DP4A` ADOPTED 行。
- 进度 **__TOT__ 条 / 已结 __DONE__ / __PCT__%**；`audit_scope §A` = **12 轮连续未审**（W1032–W1043），R107 已同步。
""".replace("__TOT__", str(tot)).replace("__DONE__", str(done)).replace("__PCT__", "%.1f" % pct)
    if "### W1043（" not in m:
        io.open(MEM, "w", encoding="utf-8", newline="\n").write(m.rstrip("\n") + "\n" + add)
        print("memory appended")
    else:
        print("memory already present")


if __name__ == "__main__":
    main()
