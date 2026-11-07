import io

p = 'D:/workbuddy_space/strata_ws/deploy/W776_TUNING_MASTER_PLAN.md'
s = io.open(p, encoding='utf-8').read()

old_r5 = ('- **R5（第一）** HC：**只做「加块数」**（split-K 或行切细）。`TILEV` 路径已由 `AUDIT7 P1-3` 源码级判无效'
          '（grid 恒 41 < 60 CU，减小 shared 不增块数；且 T=3.3 时两种 tile 都只有一次 launch）。'
          '判据：`decode GPU stages` 的 `hc0 down + hc1 down` 之和降 >=25%。见 `W789_R5_TILEV_VERDICT.md`')
new_r5 = ('- **R5（第一，2026-10-25 15:0x 改判）** HC 分两条，**主攻 down 的 K-split（Q8 化）**：\n'
          '  - **R5a-down**：把 `STRATA_GR_SPLIT` 的 K-split down（`fused_gr.cu:2303`，上游自称 ~3%/verify window）'
          '从"仅 bf16 行（`s_down == nullptr`）"扩展到 **Q8 行**。收益面：同时拿 HC_Q8 的 -3.2% 与 K-split 的 +3%（`P102`）。'
          '判据：`hc_down` 3.47 -> <=3.10（-10%），`hc_up`/`total` 不劣化。**注意它会破坏 bit 等价**（上游因此默认关），要过 parity+needle。\n'
          '  - **R5b-up（备选）**：给 `gr_up_fast_kernel` 补 Q8（`HC_Q8=1` 当前把它 `!q8w` 挡住）。已测余量 -14%（3.44 -> 2.96），'
          '收益 **-0.48 ms（-1.0%）**（`P100`）。\n'
          '  - **已废**：`TILEV`（`AUDIT7 P1-3`：grid 恒 41 < 60 CU，减小 shared 不增块数；T=3.3 时两种 tile 都只有一次 launch）。见 `W789`')

assert s.count(old_r5) == 1, s.count(old_r5)
s = s.replace(old_r5, new_r5, 1)

old_line = ('- **R3** 量化+dense GEMV 形状扫（decode 内 13.3%）· **R4** 路由 fp64（8.1%）· '
            '**R6** 注意力（M 7.2% / L 10.8%）· **R2** 溢出归因'
            '（`block_topk_re` 1120 B、`gr_down_v3` 956 B；先证在 dispatch 路径上）')
new_line = ('- **R3** 量化+dense GEMV 形状扫（decode 内 13.1%）· **R6** 注意力（M 7.2% / L 10.8%）· '
            '**R2** 溢出归因（`block_topk_re` 1120 B、`gr_down_v3` 956 B；先证在 dispatch 路径上）\n'
            '- **R4 关闭（`P101`）**：路由 fp64 —— 生产 `k==10` 走 `native_router_top10`（`layer.cpp:420`），'
            '该内核只对 10 个元素做 `expf`+float，**没有 fp64**；`STRATA_HIP_ROUTER_FAST` 实测无效（旁路）。')

assert s.count(old_line) == 1, s.count(old_line)
s = s.replace(old_line, new_line, 1)

# 纪律追加规则 I
anchor = '- **A/B 必须同会话交错**，并在每臂记录 governor。跨会话的 total 摆 45.7-47.5（约 4%），同会话内只 ±1.5%。'
add = anchor + ('\n- **规则 I（`W791` 第三次踩到）**：**env 生效 != 在路径上。** 开关打开却没变化时，先 `grep` 调用点，'
                '确认没有被 `if (X) native_*()` 之类的前置分派挡掉；判据看**该阶段的 ms 有没有动**，'
                '不动就是没走那条路，别再花第二次重启复测。\n'
                '- **规则 J**：动内核前先查上游有没有**已经实现但默认关**的等价路径（`STRATA_GR_SPLIT`、'
                '`STRATA_HIP_ROUTER_FAST`、`gr_up75` 都是），读它的默认关理由再决定是"打开"还是"改写"。')
assert s.count(anchor) == 1, s.count(anchor)
s = s.replace(anchor, add, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W776 queue updated: R5 split, R4 closed, rules I/J')
