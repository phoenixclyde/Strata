import io
import re

# 1) P444 must name R104 (audit_scope §D: every plan R id needs a ledger row)
P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
old = 'item="新候选：KV 按'
row_i = s.find("\tP444\t")
assert row_i > 0, "P444 row missing"
line_end = s.find("\n", row_i)
row = s[row_i:line_end]
if "R104" not in row:
    new_row = row.replace("\t新候选：", "\tR104 新候选：", 1)
    assert new_row != row
    s = s[:row_i] + new_row + s[line_end:]
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("P444 item now names R104")

# 2) §6.5.0 directory must list the new block
PLAN = "deploy/W832_OPT_PLAN_V2.md"
t = io.open(PLAN, encoding="utf-8").read()
anchor = "| `回写 · W1037（2026-11-07 06:4x–07:2x）"
i = t.find(anchor)
assert i >= 0, "W1037 directory row missing"
j = t.find("\n", i)
row = ("\n| `回写 · W1038（2026-11-07 08:3x）直接换 `--kv` 跑对比：int8 相对 k8v4 性能零收益，只买到质量，价钱是 240 专家槽`"
       " | 只换 `--kv` 一个参数：8K prefill +0.42%、`qsa attn` +0.36%、专家槽 −240／−0.71 GiB，速度零收益；顺带证明 KV 按 `--max-context` 全额预分配（立 R104 `--kv-grow`） |")
if "回写 · W1038（2026-11-07 08:3x）" not in t.split("### 6.5.0")[1][:6000]:
    t = t[:j] + row + t[j:]
    print("directory row inserted")

# count 26 -> 27
m = re.search(r"共 \*\*(\d+)\*\* 块", t)
if m:
    n = int(m.group(1))
    if n == 26:
        t = t.replace("共 **26** 块", "共 **27** 块", 1)
        print("directory count -> 27")

io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t)
print("plan len", len(t))
