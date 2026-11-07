import io

P = "tools/report_consistency.py"
s = io.open(P, encoding="utf-8").read()

OLD = '''def round_id():
    s = io.open(HANDOFF, encoding="utf-8").read()
    m = re.search(r"SNAPSHOT:.*?\\bround=(W\\d+)", s)
    return m.group(1) if m else None
'''
NEW = '''def round_id(report=None):
    """W1039: the round must come from the REPORT when it names one.

    It used to come only from HANDOFF's SNAPSHOT, so re-auditing an older report compared its numbers against
    the *current* round's ledger rows -- every report older than the snapshot failed, which made the gate useless
    for the one thing you want it for after the fact (did this round's report match this round's ledger?).
    """
    if report:
        head = io.open(report, encoding="utf-8").read(4000)
        for m in re.finditer(r"\\bW(\\d{4})\\b", head):
            cand = "W" + m.group(1)
            if any(ln.count("\\t") >= 9 and ln.split("\\t")[3] == cand
                   for ln in io.open(PROG, encoding="utf-8")):
                return cand
    s = io.open(HANDOFF, encoding="utf-8").read()
    m = re.search(r"SNAPSHOT:.*?\\bround=(W\\d+)", s)
    return m.group(1) if m else None
'''
assert OLD in s, "round_id anchor missing"
s = s.replace(OLD, NEW, 1)

OLD2 = """    rnd = round_id()
    if not rnd:"""
NEW2 = """    rnd = round_id(sys.argv[1])
    if not rnd:"""
assert OLD2 in s
s = s.replace(OLD2, NEW2, 1)

# the denominator check is round-agnostic (it compares against the ledger as it stands now), so on an OLD report
# it would always fail; only apply it to the current round.
OLD3 = """    sec4 = section4(text)
    if not sec4:"""
NEW3 = """    cur = round_id()
    sec4 = section4(text) if rnd == cur else "skip"
    if sec4 == "skip":
        pass
    elif not sec4:"""
assert OLD3 in s
s = s.replace(OLD3, NEW3, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("round_id now report-scoped; denominator only enforced for the current round")
