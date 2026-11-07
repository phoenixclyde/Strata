import io, shutil, time

REG = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
shutil.copy2(REG, REG + '.bak_w791_' + time.strftime('%Y%m%d_%H%M%S'))
lines = io.open(REG, encoding='utf-8-sig').read().splitlines()
header, body = lines[0], lines[1:]
ids = {ln.split('\t')[0] for ln in body}
assert 'P101' not in ids and 'P102' not in ids, 'id collision'

rows = [
    '\t'.join([
        'P101', 'decode', 'STRATA_HIP_ROUTER_FAST / R4 路由 fp64', '无效(旁路)', 'container', 'REJECTED', '', '', '',
        ('【W791 实测 2026-10-25 14:51-14:57，单臂 M×3（丢弃 2 请求）】臂：total 47.22，`router+plan+bell` 2.80/0.95 —— '
         '与基线 45.94 / 2.82/0.95 **完全没动**。根因：`src/core/layer.cpp:420` `if (native_router_enabled() && n_expert==512 && k==10) '
         'native_router_top10(...)`，我们正是 512 专家 / top-k=10 => **不走 `router_top10()`**，`STRATA_HIP_ROUTER_FAST` 是旁路。'
         '旁证（有用但当前无用）：单独编译上游 `tests/hip/router_fast.cpp`，gfx906 上 portable 53.73 -> fast 16.63 us（3.2x）、'
         '65,536 行 **0 差异**；自写 `rw.cpp` 比"默认路径 vs fast"，512 专家 k=6 的 393,216 个输出 ids 0 差异、weights 位相同。'
         '=> **R4 关闭：前提不成立**（`native_router.cu:308` 只对 10 个元素做 expf+float 累加，无 fp64、无 512 次串行 double）。'),
        '关闭；并修正 `router+plan+bell` 的归属（大头是 plan/bell，router 本体已轻，无拆分数据前不排）',
    ]),
    '\t'.join([
        'P102', 'decode', 'STRATA_GR_SPLIT (K-split down)', '净账为负', 'container', 'REJECTED', '', '', '',
        ('【W791 源码判定 2026-10-25】`fused_gr.cu:2303` 逐字：gfx906 的 opt-in `STRATA_GR_SPLIT=1` = 「latency-hidden norm/up '
         '+ K-split down，**~3% faster per verify window**」，默认关只因它破坏"多 token 读 == T 次单 token 读"的 bit 等价契约。'
         '但入口条件同一行：`if (split_on && a[0].s_down == nullptr)` => **只支持 bf16 行（HC_Q8=0）**。'
         '而 `P100` 实测 HC_Q8=0 整体 **+3.3% 且 -169 槽** => +3% 建立在 -3.3% 之上，净账为负。'),
        ('不采用；但机制是 R5 的正解：把 K-split down 适配 Q8 行即可同时拿 HC_Q8 的 -3.2% 与 K-split 的 +3%，'
         '排在"给 gr_up_fast_kernel 加 Q8"（-1.0%）之前'),
    ]),
]
body.extend(rows)
io.open(REG, 'w', encoding='utf-8', newline='\n').write(header + '\n' + '\n'.join(body) + '\n')
print('register: P101 + P102 added, rows=%d' % (len(body) + 1))
