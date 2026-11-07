import io

P = "tools/report_consistency.py"
s = io.open(P, encoding="utf-8").read()

# 1) new helper: the report's 四、进度 denominator must equal what PROGRESS.tsv derives right now
HELPER = '''
def denom_from_ledger():
    """(rows, done) derived the same way tools/progress.py does: every `count` row adds its count/done."""
    tot = done = 0
    for ln in io.open(PROG, encoding="utf-8"):
        if ln.startswith("#") or ln.count("\\t") < 8:
            continue
        f = ln.rstrip("\\n").split("\\t")
        if f[4] != "count":
            continue
        try:
            tot += int(f[5])
            done += int(f[6])
        except ValueError:
            pass
    return tot, done


def section4(text):
    i = text.find("四、进度")
    if i < 0:
        return ""
    j = text.find("---", i)
    return text[i:j if j > 0 else len(text)]


'''
anchor = "def main():"
assert anchor in s
s = s.replace(anchor, HELPER + anchor, 1)

# 2) the check itself, appended to the existing fail accumulation
OLD = """    if fails:
        for x in fails:"""
NEW = """    # W1039: the four-part report's denominator drifted 386 -> 391 -> 393 -> 395 across one round while every
    # other gate stayed green (report_lint only wants "N 条 / 已结 M / P%", report_depth only counts R ids).
    # Tie it to the ledger, which is the only place the denominator may come from.
    sec4 = section4(text)
    if not sec4:
        fails.append("没有「四、进度」段")
    else:
        tot, done = denom_from_ledger()
        got = re.findall(r"(\\d+)\\s*条\\s*/\\s*已结\\s*(\\d+)", sec4)
        if not got:
            fails.append("四、进度 里没有「N 条 / 已结 M」")
        elif (int(got[-1][0]), int(got[-1][1])) != (tot, done):
            fails.append("四、进度 写 %s 条 / 已结 %s，账本派生的是 %d / %d"
                         % (got[-1][0], got[-1][1], tot, done))

    if fails:
        for x in fails:"""
assert OLD in s
s = s.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("report_consistency: denominator rule added")
