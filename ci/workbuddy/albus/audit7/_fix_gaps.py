import io

D = 'D:/workbuddy_space/strata_ws/deploy/'

# ---------- 1) W784 §2 补勘误（AUDIT6 P2-8 的承诺，之前没执行） ----------
p = D + 'W784_GFX906_FULL_SWEEP.md'
s = io.open(p, encoding='utf-8').read()
old = '## 2 E0 实测：先量上限，再谈移植\n'
new = ('## 2 E0 实测：先量上限，再谈移植\n\n'
       '> **[2026-10-25 06:2x 补勘误，`AUDIT7` 发现 `AUDIT6 P2-8` 承诺的这条整改从未执行] 本节有三处要改：**\n'
       '> 1. **`74.76 ms/window` 是墙钟，不是 GPU stages 的总和。** 本节同一段里又写 `GPU stages total 55.65 ms/window`，\n'
       '>    而下面的阶段占比是按 **55.65** 算的。两个数不能混着用（`74.76` 与 `55.65` 差 19.11 ms，是主机侧开销）。\n'
       '> 2. **本节所属的 `P87` 已作废**（`P91` 取代），但作废理由不是"表不自洽"——见 `AUDIT6 P2-7` 的撤回banner。\n'
       '> 3. **"预填期 GPU 0%"这个前提是错的**（`AUDIT6 P2-8`）：`rocm-smi` 每 1 s 直读 49 样本为 `100 x42 / 99 x4 / 98 x1 / 68 x1 / 0 x1`，\n'
       '>    中位 100、零值 2%。本节据此提出的"把专家算力搬到 GPU"方向不成立。\n'
       '> => 本节的**数字**可作历史对照，**结论**一率以 `P91` / `W786 §2.1` 为准。\n')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W784 §2 errata added')

# ---------- 2) AUDIT6 P2-7 标题与正文加行内撤回标记 ----------
p = D + 'AUDIT6_W776_W785.md'
s = io.open(p, encoding='utf-8').read()

old_h = '## P2-7 `P87` 的 74.76 ms 与分项和 63.45 ms 差 11.31 ms（15%），三轮审计没人做这个加法'
new_h = '## P2-7 【已撤回】`P87` 的 74.76 ms 与分项和 63.45 ms 差 11.31 ms（15%），三轮审计没人做这个加法'
assert s.count(old_h) == 1
s = s.replace(old_h, new_h, 1)

old_b = '- **性质**：表格内部不自洽。第一轮审计逐条比对了数字与出处，但没有做"分项和 = 总数"这个机械校验。'
new_b = ('- **性质**（**本条已撤回**，见上方 banner）：当时写的是"表格内部不自洽"，实际上那一行的差额来自同行末尾的 '
         '`adapt wait + join`；真正的缺陷是**口径混用**（GPU stages 的 55.65 当作墙钟 74.76 的分子）。')
if s.count(old_b) == 1:
    s = s.replace(old_b, new_b, 1)
    print('AUDIT6 P2-7 body marked')
else:
    print('AUDIT6 P2-7 body NOT found, count=%d' % s.count(old_b))

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# ---------- 3) W786 §4 表内联标记（0.2-0.4% 那两行） ----------
p = D + 'W786_TARGET_CORRECTION.md'
s = io.open(p, encoding='utf-8').read()
old_t = '| 3 | R3 | 量化 + dense GEMV 按形状扫'
new_t = '| 3 | R3 | 【**AUDIT7 P2-4**：本列"端到端 0.2-0.4%"只在单轮成立，多轮下应按 decode 内部占比读，见 §4.1 修正】量化 + dense GEMV 按形状扫'
if s.count(old_t) == 1:
    s = s.replace(old_t, new_t, 1)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('W786 §4 inline marked')
else:
    print('W786 §4 target count=%d' % s.count(old_t))
