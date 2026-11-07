# -*- coding: utf-8 -*-
'''AUDIT24: discipline 23 + ledger notes (R61/R86/R90) + AUDIT_INDEX row.'''
import io, csv

# 1) discipline 23 in the audit doc
p = 'D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md'
s = io.open(p, encoding='utf-8').read()
anchor = '''- **㉒ 改完方案表必须跑表格体检**'''
add = '''- **㉓ 引用方案必须给「md5 + 行号」**：`W832` 是本项目的权威件，行号随每次回写漂移（本轮 R60/R63 那几条从
  651/656 漂到 655/663）。只写行号 = 下一个人按旧号去 grep 会落空。⇒ 引用格式固定为
  `W832@<md5前8位>:<行号>`，并在改动后重算 md5。
'''
if anchor in s and '㉓' not in s:
    s = s.replace(anchor, add + anchor, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)

# 2) ledger notes
P = 'D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv'
lines = io.open(P, encoding='utf-8').read().split('\n')
out, touched = [], []
for ln in lines:
    f = ln.split('\t')
    if len(f) == 10 and f[1] == 'R61' and 'AUDIT24' not in f[8]:
        f[8] += ('\n**【AUDIT24 复测 2026-11-04 17:0x】**：同形状（16 专家×1024 token、Q4_K、'
                 '`kq_bench 16 1024 3 12 1280 2560`）重跑 = **64.78 / 68.15 / 68.18 / 68.17，均值 67.3%** ⇒ 67.1% 成立；'
                 'CSV 留 `data/w952pmc/`（原 `data/w941pmc2` 已被后续 Q5_1 run 覆盖）。**形状必须标**：'
                 'M=1024 是 67.3%，生产形状（每专家≈320 行）是 **60.6%**（`W945`），两者不可互换。')
        touched.append('R61')
    elif len(f) == 10 and f[1] == 'R86' and 'AUDIT24' not in f[8]:
        f[8] += ('\n**【AUDIT24 更正】**：「88.6% 专家字节」是按 offset 列加权、且分母指 down；'
                 '按 `blob_bytes`×512 重算：Q5_1 占**专家总字节 35%**（27.05/77.0 GB）、down 内 **86%**、层数 43/48=89.6%；'
                 '「60.5 GB」应为 **77.0 GB**。端到端预期（down 占 prefill 13.8%）不变。')
        touched.append('R86')
    elif len(f) == 10 and f[1] == 'R90' and 'AUDIT24' not in f[8]:
        f[8] += ('\n**【AUDIT24 更正】**：版本序判据作废 —— `get_J_max` 在**上游 master 也是 0**（只有我们 pin 有 1 处，'
                 '是自家补丁）；`3cf03257` 只出现在别人的 bench README。⇒「三家 fork 更旧」未被源码建立；'
                 '**S1 必须先建立 pin→上游 tag 映射**（`~/strata166/llama.cpp` 不是 git 仓库）。')
        touched.append('R90')
    out.append('\t'.join(f))
io.open(P, 'w', encoding='utf-8', newline='').write('\n'.join(out))
print('ledger touched:', touched)

# 3) AUDIT_INDEX
Q = 'D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md'
t = io.open(Q, encoding='utf-8').read()
old_tot = '| **合计** | **W776–W897 + 方案本体** | **32** | **109** | **95** | **7** | — |'
new_row = ('| **AUDIT24** | **W900–W951（50 件，全部首次被审）**：2 P0（W909 专家格式误判 / W832 方案落后于账本）、'
           '15 P1、12 P2、4 需复核；**A 级复跑 3 次**（PMC 67.3%、pack 字节、生产 804 tok/s）+ 外网核对 2 次 | '
           '**2** | **15** | **12** | **0** | `AUDIT24_W900_W951.md` |')
new_tot = '| **合计** | **W776–W951 + 方案本体** | **34** | **124** | **107** | **7** | — |'
if 'AUDIT24' not in t:
    t = t.replace(old_tot, new_row + '\n' + new_tot, 1)
    t = t.replace('# 审计索引（AUDIT6 → AUDIT22）', '# 审计索引（AUDIT6 → AUDIT24）', 1)
io.open(Q, 'w', encoding='utf-8', newline='').write(t)
print('index updated:', 'AUDIT24' in t, '| 合计 row:', new_tot in t)
