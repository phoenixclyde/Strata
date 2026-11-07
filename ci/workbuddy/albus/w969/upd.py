# -*- coding: utf-8 -*-
"""W969: R90 note + closure row V-10; plan note on the 1.7 s fixed cost."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W969" not in r[8]:
        r[8] += (" **【W969 · 22:2x】口径统一**：600/800/500 是三个 regime，不是三个结论 —— 冷读长档 804@60K（昨天 803.7，"
                 "同一权重）、冷读短档 ~525@2.35K、`W863` 的 946–1404 是**长度阶梯带前缀复用**（分母只算读入 token，"
                 "`1910 reused + 5 read`）。拟合：**t ≈ 1.7 s + n/822**（2.35K/15.8K/60K/130K 全部命中）⇒ **每段冷读约 1.7 s 固定成本**，"
                 "2.3K 时占 38%、60K 时占 2%。已排除：chunk、引擎版本（503 vs 506）、0.8.0（497，内核逐字节等价）、GPU 降频（sclk 1725）、"
                 "`--resident-budget-gib`（10-11 就没了）。⇒ 靶心是那 1.7 s（R88），不是换基线。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-10",  "P0", "W969_UNIFIED_PREFILL_REGIMES.md",      "1.7 s",                               "RESOLVED", "冷读 t≈1.7s+n/822; 600/800/500 是三口径"),\n')
if "V-10" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")

# memory block
mem = """## W969 · 口径统一：600/800/500 是三个 regime（21:2x–22:2x）

- **冷读长档**：804.1@60,330（今天）、803.7@61,246（昨天 11-03 23:53）、789.6@130K、711@15.8K —— 同一权重，**没有退步**。
- **冷读短档**：2,353 token ≈ **525**（现场发 3 条不同 prompt：516/546/519；冷启动 generate 2,047→604）。
- **热读**：同一 prompt 第二次 `cached_tokens 2348` → 0.2 s。
- **`W863` 的 946/1231/1404 是长度阶梯带前缀复用**：引擎 tok/s = 读入 token/时间，`1910 reused + 5 read` 只算那 5 个 ⇒ 不能当冷读速率。
- **拟合**：`t ≈ 1.7 s + n/822`（2.35K→4.6s 实测 4.4；15.8K→20.9 实测 22.2；60K→75.1 实测 75.0；130K→160 实测 164.8）。
  ⇒ **每段冷读 ≈1.7 s 固定成本**，2.3K 占 38%、60K 占 2%。靶心是这 1.7 s（R88），不是换基线。
- **已排除**：chunk（auto 524 vs 16384 503@2K）、引擎版本（0.1.56 503 vs 0.1.55w 506）、0.8.0（497，内核 23,164 vs 23,168 B 逐字节等价）、
  GPU 降频（sclk 1725 MHz）、`--resident-budget-gib`（10-11 就移除）。
- 台账 42/42；账本 176/101。本轮零重启（全部用在线服务或 wrapper 容器）。
"""
io.open("D:/workbuddy_space/strata_ws/albus/w969/mem_block.md", "w", encoding="utf-8", newline="").write(mem)
print("mem block written")
