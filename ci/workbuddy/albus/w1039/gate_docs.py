import io

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()

# 1) P451 -> DONE_NEG (numeric gate failed); keep its note, append the outcome
i = s.find("\tP451\t")
assert i > 0
j = s.find("\n", i)
row = s[i:j]
if "\tDONE_NEG\t" not in row:
    row2 = row.replace("\tOPEN\t", "\tDONE_NEG\t", 1)
    row2 += " **W1041 数值门判否（P453）**：KL 0.04130（阈值 0.0139，3.0×）、top-1 93.55%（阈值 99%）⇒ 速度收益不成立，不装机。"
    s = s[:i] + row2 + s[j:]
    print("P451 -> DONE_NEG")

ROWS = [dict(
    block="B6判定探针", id="P453",
    item=("数值门（三臂，k8v4）判 **FAIL**：地板臂 KL 0.00000 / top-1 100%，开关臂 KL **0.04130**（阈值 0.0139）、"
          "top-1 **93.55%**（阈值 99%）⇒ DP4A 的 1.8% 是用 6.45 个百分点的 top-1 换的"),
    source="W1039", kind="count", count="1", done="1", status="DONE_NEG",
    note=("**W1039 数值门（机主 10:10「按你的来」；工具 `tools/quant_quality.py` 的 `run`/`compare`；5 段 × 999 位 = 4995 点）**。"
          "三臂：A=pa5+`ATTN_DP4A=0`（参照）、Ab=同 argv 第二个容器（**自一致地板**）、B=pa5+`ATTN_DP4A=1`（开关）。"
          "**地板臂 A vs Ab：top-1 100.00% / KL 0.00000 / KL p99 0.0000 / PPL 4.048 vs 4.048** ⇒ 环境完全确定，0.0413 不是噪声。"
          "**开关臂 A vs B：top-1 93.55% / KL 0.04130 / KL p99 0.6109 / PPL 4.057 vs 4.048** ⇒ 两条都破线（KL 3.0×、top-1 差 6.45 点）。"
          "**偏差（必须写清，否则读者会当生产值）**：工具 FIXED 强制 `--expert-cache 1500`、`--pcie-frac 0`、`--adapt-every 100000`、"
          "`STRATA_PREFILL_CPU_SHARE=0`、`STRATA_ROUTE_TAIL_SKIP=0`；**`--kv` 从工具默认的 fp16 改成 k8v4** —— "
          "否则 `kv_mode=0`、dp4a 派发条件（`kv_mode==3||kv_mode==1`，`qsa_decode_attn.cu:1146`）永远不成立，这一门会测出「零差异」的假通过。"
          "**归因边界（技能 §6）**：A 与 B 同 exe、只差一个 env ⇒ 这一门归因到 `ATTN_DP4A` 这一个开关，不是整栈。"
          "两次停机：试跑 52 s（首跑缺 `--ids` 立刻失败）+ 正式 683 s，合计 735 s；容器已恢复，在产仍 `b12180`。"
          "**判决：pa5 不装机**；代码留分支、开关默认关，`deploy_gate` D4 保持红。"),
    ref="P451;P452", kw="KW:0.04130|93.55"),
]
add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"]); continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    print("ledger +", [a.split("\t")[1] for a in add])

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
