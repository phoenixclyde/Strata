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

    if not fails:
        print("REPORT_LINT: PASS (%d fields)" % (len(REQ) + len(LINE_REQ)))
        return 0
    print("REPORT_LINT: FAIL (%d issue(s))" % len(fails))
    for f in fails:
        print("  -", f)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "report.md"))
