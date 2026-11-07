# -*- coding: utf-8 -*-
'''Count fix: the W927 banner is a 16th P1.'''
import io

doc = 'D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md'
s = io.open(doc, encoding='utf-8').read()
s = s.replace('**P0 = 2，P1 = 15，P2 = 12，需复核 = 4', '**P0 = 2，P1 = 16，P2 = 12，需复核 = 4')
s = s.replace('## 1 P1 清单（15 条，已全部回写）', '## 1 P1 清单（16 条，已全部回写）')
anchor = '| A24-17 | `PROGRESS.tsv` R53/R54 |'
row = ('| A24-18 | `W927 §79-91` | 端到端 5.5% 同样按「dot 占 53.3%」（模块分母）推；真 kernel 是 30.0% ⇒ 改判 −2.05%。'
       '另 §24-36 引的 `K100LC-RT4`/`gfx926` 无 URL/sha，`gfx926` 非标准架构名 | 横幅（方向保留、数字作废） |\n')
if 'A24-18' not in s:
    s = s.replace(anchor, row + anchor, 1)
io.open(doc, 'w', encoding='utf-8', newline='').write(s)

idx = 'D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md'
t = io.open(idx, encoding='utf-8').read()
t = t.replace('2 P0（W909 专家格式误判 / W832 方案落后于账本）、15 P1、12 P2、4 需复核',
              '2 P0（W909 专家格式误判 / W832 方案落后于账本）、16 P1、12 P2、4 需复核')
t = t.replace('| **34** | **124** | **107** |', '| **34** | **125** | **107** |')
io.open(idx, 'w', encoding='utf-8', newline='').write(t)

rep = 'D:/workbuddy_space/strata_ws/albus/w952/reply.md'
r = io.open(rep, encoding='utf-8').read()
r = r.replace('**P0 2 / P1 15 / P2 12 / 需复核 4**', '**P0 2 / P1 16 / P2 12 / 需复核 4**')
io.open(rep, 'w', encoding='utf-8', newline='').write(r)
print('counts updated')
