import io

P = "tools/report_lint.py"
s = io.open(P, encoding="utf-8").read()

OLD = """    if not fails:
        print("REPORT_LINT: PASS (%d fields)" % (len(REQ) + len(LINE_REQ)))"""
NEW = """    # W1039: two numbering systems in one file.  The four-part report is written as `**一、…**`; a body that
    # ALSO has `## 一、` headings makes "三" ambiguous -- and that is exactly how a superseded conclusion stayed
    # in the body while the header said something else.  One numbering, or name the body sections differently.
    for n in "一二三四":
        if re.search(r"\\*\\*%s、" % n, flat) and re.search(r"^##\\s*%s、" % n, text, re.M):
            fails.append("%-28s 正文同时存在 `**%s、` 与 `## %s、` 两套编号（读者分不清哪个「%s」是四件套）"
                         % ("S 编号唯一", n, n, n))
            break

    # W1039: the H1 must name the round, so a report pasted into a bundle can still be dated.
    h1 = text.split("\\n", 1)[0]
    if not re.search(r"\\bW\\d{4}\\b", h1):
        fails.append("%-28s 标题里没有轮次号（W####）" % "S 标题轮次")

    if not fails:
        print("REPORT_LINT: PASS (%d fields)" % (len(REQ) + len(LINE_REQ)))"""
assert OLD in s
s = s.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("report_lint: +S 编号唯一 +S 标题轮次")
