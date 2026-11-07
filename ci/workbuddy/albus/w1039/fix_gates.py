import io

# 1) ledger KW tokens: unique, >= 3 chars, present in the row
p = "deploy/PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
pairs = [
    ("\tKW:DP4A|DONE_NEG", "\tKW:2387|5074"),
    ("\tKW:组合|静默", "\tKW:静默正确性|一个内核都不发"),
]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1)
        print("kw", a, "->", b)
    else:
        print("kw MISS", a)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)

# 2) report: borrows + file:line refs
r = "albus/w1039/reply.md"
t = io.open(r, encoding="utf-8").read()
a = "prompt 借 2606 槽（7.62 GiB）"
b = "the prompt path borrows 2606 槽（7.62 GiB）"
if a in t:
    t = t.replace(a, b, 1)
    print("F6 borrows fixed")

old = "`STRATA_ATTN_OPT_DISPATCH` 只有 `case 1/2/4`"
new = ("`STRATA_ATTN_OPT_DISPATCH`（`qsa_decode_attn.cu:1077`）只有 `case 1/2/4`")
if old in t:
    t = t.replace(old, new, 1)

old2 = "而 W1037 接的那段条件是 `opt != 0 && !lane_cell && !use_query_swizzle` ⇒ 永不成立"
new2 = ("而 W1037 接的那段条件（`qsa_decode_attn.cu:1143-1152`）是 "
        "`opt != 0 && !lane_cell && !use_query_swizzle` ⇒ 永不成立")
if old2 in t:
    t = t.replace(old2, new2, 1)

old3 = "pa4 把 OPT 派发放进 `if (use_query_swizzle)` 内"
new3 = "pa4 把 OPT 派发放进 `if (use_query_swizzle)` 内（`qsa_decode_attn.cu:1172`）"
if old3 in t:
    t = t.replace(old3, new3, 1)

old4 = "只换内层）。"
new4 = "只换内层，宏在 `qsa_decode_attn.cu:1091`）。"
if old4 in t:
    t = t.replace(old4, new4, 1)

io.open(r, "w", encoding="utf-8", newline="\n").write(t)
print("report patched")
