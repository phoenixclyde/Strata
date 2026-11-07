#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_lint -- 四件套报告的机械校验。机主 2026-11-04 15:5x：「你为什么一直会丢东西，这个不能固化下来吗？」

用法:  python tools/report_lint.py <report.md>
退出码 0 = 全字段齐备；1 = 有缺项（会逐条列出）。

设计原则：只检查「能不能被后续复核」，不检查文风。
- 容器 id 必须是 12 位 hex；引擎 md5 必须是 32 位 hex（W940 的事故靠这条兜住）
- config 必须同时写 md5 / exe / args 数 / env 数（机主两次指出这里被缩水）
- 队列必须是有序的 `A → B → C` 形态，且至少 5 个 R 编号
"""
import re
import sys

REQ = [
    ("F1 容器/镜像", r"容器\s*/\s*镜像", [r"\b[0-9a-f]{12}\b", r"strata-gfx906:[0-9a-zA-Z.\-]+"]),
    ("F2 运行中引擎", r"运行中引擎", [r"\b[0-9a-f]{32}\b", r"\d{2},\d{3},\d{3}|\d{8,}", r"0\.1\.\d+"]),
    ("F3 config(md5+exe+args+env)", r"\bconfig\b", [r"\b[0-9a-f]{32}\b", r"exe\s*=\s*\S+", r"args\s*\*{0,2}\s*\d+", r"env\s*\*{0,2}\s*\d+"]),
    ("F4 健康", r"健康", [r"/health|status", r"restarts?\s*=?\s*\d+", r"StartedAt|启动时间"]),
    ("F5 资源隔离", r"资源隔离", [r"ulimit\s*-l", r"VmLck"]),
    ("F6 显存布局", r"显存", [r"expert cache", r"borrows", r"VRAM free"]),
    ("F7 回滚件", r"回滚件", [r"pre-|\.pre|strata-0\.1\.\d+", r"rollback|cp .*\.json"]),
    ("F8 本轮改动/三方一致", r"本轮改动", [r"零|无|—", r"disk.*build.*running|三方"]),
    ("M 主线", r"主线", [r"@\s*[0-9a-f]{7,}", r"mi50-0\.\d+\.\d+", r"落后|领先", r"脏\s*\d+\s*行", r"上游"]),
    ("P 落生产", r"本次落生产", [r"重启\s*\**\s*\d+\s*\**\s*次|重启次数", r"停机", r"回滚"]),
    ("Q 进度", r"进度", [r"\d+\s*条", r"已结\s*\d+", r"\d+\.\d%"]),
    ("Q2 队列", r"队列", [r"→", r"R\d+(?:[’'′])?"]),
]

# W1025: two dependency facts that a reader cannot reconstruct from anything else in the
# report -- which ROCm the container actually runs, and which llama.cpp the engine was built
# against.  These are checked PER LINE: the point is that the table has a row for them, not
# that the words appear somewhere in the prose (the older checks are whole-text and that is
# exactly how a number goes missing while the gate stays green).
LINE_REQ = [
    ("F9 ROCm 版本（容器内）", r"ROCm",
     [r"\b\d+\.\d+\.\d+(?:-\d+)?\b", r"HIP|hipconfig|\.info/version"]),
    ("F10 llama.cpp 版本（容器内）", r"llama\.cpp",
     [r"b\d{4,5}", r"\b[0-9a-f]{40}\b"]),
]


SEP_ROW = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
BODY_SPLIT = re.compile(r"\*\*二、|^\s*##\s*二、|二、主线", re.M)


def table_cells(line):
    s = line.strip().replace("\\|", "\x00")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip().replace("\x00", "\\|") for c in s.split("|")]


def check_first_table(text):
    """W1043: the four-part report's FIRST table must actually contain data.

    The owner reported 「第一张是空表」. The old lint only searched the whole
    document for keywords, so a table with an empty body, ragged rows, or
    blank value cells passed. GFM spec (checked online 2026-11-07):
      * header and delimiter rows must have equal cell counts, or the table
        is not recognised at all;
      * a body row with FEWER cells is padded with EMPTY cells (this is what
        made the 值 column blank in W1038..W1042);
      * a table with no body rows emits no <tbody>.
    """
    fails = []
    lines = text.split("\n")
    m = BODY_SPLIT.search(text)
    cut = text[:m.start()].count("\n") if m else len(lines)
    head = lines[:cut]
    st = None
    for i, line in enumerate(head):
        if line.strip().startswith("|") and i + 1 < len(head) and SEP_ROW.match(head[i + 1]):
            st = i
            break
    if st is None:
        return ["T0 表结构：四件套第一项里找不到合法表格（表头 + 分隔行）"]
    j = st
    while j < len(head) and head[j].strip().startswith("|"):
        j += 1
    blk = head[st:j]
    ncol = len(table_cells(blk[0]))
    nsep = len(table_cells(blk[1]))
    if nsep != ncol:
        fails.append("T0 表结构：表头 %d 列 / 分隔行 %d 列不相等 ⇒ GFM 根本不认这张表"
                     % (ncol, nsep))
    data = blk[2:]
    if len(data) < 10:
        fails.append("T1 表结构：第一张表只有 %d 行数据（10 字段报告要 >=10），"
                     "空表 / 缺行不许发" % len(data))
    for k, row in enumerate(data, 1):
        c = table_cells(row)
        if len(c) != ncol:
            fails.append("T2 表结构：第 %d 行是 %d 列（表头 %d 列）⇒ GFM 会补空单元格或丢弃多余列"
                         % (k, len(c), ncol))
        if len(c) < 2 or not c[-1]:
            fails.append("T3 表结构：第 %d 行的「值」单元格是空的（没数据也要写 `—`）" % k)
    if st > 0 and head[st - 1].strip():
        fails.append("T4 表结构：表格前没有空行（MD058，某些解析器会把首行并进段落）")
    if j < len(head) and head[j].strip():
        fails.append("T4 表结构：表格后没有空行（MD058）")
    return fails


def self_test():
    """Negative tests: a gate that cannot fail is not a gate (P496 lesson)."""
    good = ["| # | 字段 | 值 |", "|---|---|---|"] + [
        "| %d | 项%d | 值%d |" % (i, i, i) for i in range(1, 11)]
    prefix = "# W9999 报告\n\n**一、生产容器（10 字段）**\n\n"
    suffix = "\n**二、主线** — x\n"

    def doc(rows, blank_before=True):
        return prefix + ("" if blank_before else "| 前文 |\n") + "\n".join(rows) + suffix

    cases = [
        ("正常表", doc(good), False),
        ("空表（只有表头+分隔）", doc(good[:2]), True),
        ("少列行", doc([r.replace("| 2 | 项2 | 值2 |", "| 3a args 明细 | 一长串 |") for r in good]), True),
        ("值列空", doc([r.replace("| 5 | 项5 | 值5 |", "| 5 | 项5 |  |") for r in good]), True),
        ("表头/分隔列数不等", doc([good[0], "|---|---|"] + good[2:]), True),
        ("表前无空行", doc(good, blank_before=False), True),
    ]
    bad = 0
    for name, sample, want_fail in cases:
        got = check_first_table(sample)
        ok = bool(got) == want_fail
        if not ok:
            bad += 1
        print("  %-26s %-4s (fails=%d)" % (name, "PASS" if ok else "FAIL", len(got)))
    print("REPORT_LINT_SELF_TEST: %d/%d" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main(path):
    text = open(path, encoding="utf-8").read()
    flat = re.sub(r"[ \t]+", " ", text)
    fails = []
    for name, header, pats in REQ:
        # the field must appear inside a section whose heading/row names it
        if not re.search(header, flat):
            fails.append("%-28s 缺整个字段（找不到「%s」）" % (name, header))
            continue
        missing = [p for p in pats if not re.search(p, flat)]
        if missing:
            fails.append("%-28s 字段在，但缺: %s" % (name, " / ".join(missing)))

    # queue must be ordered and long enough — take the queue line that carries the most R ids
    cands = [l for l in flat.split("\n") if "队列" in l]
    if not cands:
        fails.append("%-28s 完全没有「队列」这一项" % "Q2 队列")
    else:
        q = max(cands, key=lambda l: len(re.findall(r"R\d+", l)))
        ids = re.findall(r"R\d+", q)
        if len(ids) < 5:
            fails.append("%-28s 队列只有 %d 个 R 编号（要 >=5，且用 → 串起来）" % ("Q2 队列", len(ids)))
        elif "→" not in q:
            fails.append("%-28s 队列没有用 → 串成有序形态" % "Q2 队列")

    # dependency facts: they belong to the container table (section 一), so the search is
    # scoped to it -- "somewhere in the prose" is what let the value go missing before.
    scope = re.split(r"\*\*二、|## 二、|二、主线", text)[0]
    for name, header, pats in LINE_REQ:
        rows = [l for l in scope.split("\n") if re.search(header, l)]
        if not any(all(re.search(p, l) for p in pats) for l in rows):
            fails.append("%-28s 生产容器表里需要一行同时含「%s」+ %s（表内 %d 行提到该词，但没写全）"
                         % (name, header, " / ".join(pats), len(rows)))

    # W1043: structural gate on the first table itself, not just keyword presence.
    fails += ["%-28s %s" % ("T 表结构", f) for f in check_first_table(text)]

    # W1039: two numbering systems in one file.  The four-part report is written as `**一、…**`; a body that
    # ALSO has `## 一、` headings makes "三" ambiguous -- and that is exactly how a superseded conclusion stayed
    # in the body while the header said something else.  One numbering, or name the body sections differently.
    for n in "一二三四":
        if re.search(r"\*\*%s、" % n, flat) and re.search(r"^##\s*%s、" % n, text, re.M):
            fails.append("%-28s 正文同时存在 `**%s、` 与 `## %s、` 两套编号（读者分不清哪个「%s」是四件套）"
                         % ("S 编号唯一", n, n, n))
            break

    # W1039: the H1 must name the round, so a report pasted into a bundle can still be dated.
    h1 = text.split("\n", 1)[0]
    if not re.search(r"\bW\d{4}\b", h1):
        fails.append("%-28s 标题里没有轮次号（W####）" % "S 标题轮次")

    if not fails:
        print("REPORT_LINT: PASS (%d fields)" % (len(REQ) + len(LINE_REQ)))
        return 0
    print("REPORT_LINT: FAIL (%d issue(s))" % len(fails))
    for f in fails:
        print("  -", f)
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        sys.exit(self_test())
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "report.md"))
