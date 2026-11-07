import io

# ---------- 1) W787 P2-4 ----------
p1 = 'D:/workbuddy_space/strata_ws/deploy/W787_R1_FAILURE_REVIEW.md'
s1 = io.open(p1, encoding='utf-8').read()
old1 = ('所以 `W786 §4` 把 GEMV（13.3%）/ router（8.1%）/ HC（16.1%）降到「端到端 0.2-0.4%」是**错的**'
        '——对多轮对话，它们在端到端里就是 13.3% / 8.1% / 16.1%。')
new1 = ('所以 `W786 §4` 把 GEMV（13.3%）/ router（8.1%）/ HC（16.1%）降到「端到端 0.2-0.4%」是**错的**。\n'
        '**但要写准（`AUDIT7 P2-4`）**：13.3% / 8.1% / 16.1% 是 **decode 内部**占比。只有当 decode 占端到端约 99%'
        '（输出 >=300 token）时，它们才近似等于端到端占比；48 token 输出时 decode 只占 1.0/1.69 = 59%，'
        '对应端到端约 **7.9% / 4.8% / 9.5%**。结论不变（比 0.2-0.4% 高一个数量级），但引用时必须带条件。')
if s1.count(old1) == 1:
    s1 = s1.replace(old1, new1, 1)
    io.open(p1, 'w', encoding='utf-8', newline='\n').write(s1)
    print('W787 patched')
else:
    print('W787 target not found, count=%d' % s1.count(old1))

# ---------- 2) W776 §12 队列去重并更新 R5 ----------
p2 = 'D:/workbuddy_space/strata_ws/deploy/W776_TUNING_MASTER_PLAN.md'
s2 = io.open(p2, encoding='utf-8').read()

old2 = ('- **R5（新第一）** HC 归因（16.1%，多轮场景下最大单项）· **R3** 量化+dense GEMV（13.3%）· '
        '**R4** 路由 fp64（8.1%）\n'
        '- **R2** 溢出归因（`block_topk_re` 1120 B、`gr_down_v3` 956 B；但先证在 dispatch 路径上）\n'
        '- **R3** 量化+dense GEMV 形状扫（13.3%）· **R4** 路由 fp64（8.1%）· **R5** HC 归因（16.1%，机理未明）· '
        '**R6** 注意力（M 7.2% / L 10.8%）')
new2 = ('- **R5（第一）** HC：**只做「加块数」**（split-K 或行切细）。`TILEV` 路径已由 `AUDIT7 P1-3` 源码级判无效'
        '（grid 恒 41 < 60 CU，减小 shared 不增块数；且 T=3.3 时两种 tile 都只有一次 launch）。'
        '判据：`decode GPU stages` 的 `hc0 down + hc1 down` 之和降 >=25%。见 `W789_R5_TILEV_VERDICT.md`\n'
        '- **R3** 量化+dense GEMV 形状扫（decode 内 13.3%）· **R4** 路由 fp64（8.1%）· '
        '**R6** 注意力（M 7.2% / L 10.8%）· **R2** 溢出归因（`block_topk_re` 1120 B、`gr_down_v3` 956 B；先证在 dispatch 路径上）')
if s2.count(old2) == 1:
    s2 = s2.replace(old2, new2, 1)
    print('W776 queue deduped')
else:
    print('W776 queue target count=%d' % s2.count(old2))

# 追加基线口径提醒
old3 = '§5/§9/§10/§11 与 `W785` 的 Q1-Q9 都不再执行；两代编号到 R 批的映射见 W786 §6。'
new3 = ('**基线口径（`AUDIT7 P1-4` / `P97`）**：现存 decode 基线全部测于 `governor=performance`（10-22 至 10-25 06:0x），'
        '生产现为 `schedutil`。任何 A/B 必须当场记录 governor 并前后一致；跨 governor 的数字不可直接相减。\n\n'
        '§5/§9/§10/§11 与 `W785` 的 Q1-Q9 都不再执行；两代编号到 R 批的映射见 W786 §6。')
if s2.count(old3) == 1:
    s2 = s2.replace(old3, new3, 1)
    print('W776 governor note added')

io.open(p2, 'w', encoding='utf-8', newline='\n').write(s2)

# ---------- 3) W785 banner 补充 ----------
p3 = 'D:/workbuddy_space/strata_ws/deploy/W785_MASTER_QUEUE.md'
s3 = io.open(p3, encoding='utf-8').read()
old3b = '> 本文件 §2（三处白跑风险）与 §6（纪律）仍然有效，继续引用。'
new3b = ('> 本文件 §2（三处白跑风险）与 §6（纪律）仍然有效，继续引用。\n'
         '> **[2026-10-25 06:3x 追加] `AUDIT7` 又抓到第三类白跑：`W788` 的「路径 A（TILEV 2560->1280）」源码级无效** ——'
         '`DOWN_BLOCKS` 与 TILEV 无关（grid 恒 41 < 60 CU），且我们的 T=3.3 时两种 tile 都只有一次 launch。'
         'R5 已按此路径做过一半，裁定见 `W789_R5_TILEV_VERDICT.md`；要治 HC 只能加块数。')
if s3.count(old3b) == 1:
    s3 = s3.replace(old3b, new3b, 1)
    io.open(p3, 'w', encoding='utf-8', newline='\n').write(s3)
    print('W785 banner extended')
else:
    print('W785 banner target count=%d' % s3.count(old3b))
