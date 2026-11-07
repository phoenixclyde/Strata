# -*- coding: utf-8 -*-
"""Correct the CPU-share section in today's memory log (the 8K / -26% claim was an invalid extrapolation)."""
import io

p = 'D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md'
s = io.open(p, encoding='utf-8').read()

old_head = '### CPU 分摊是两条曲线（交叉 ≈4.3K token）'
assert old_head in s, 'anchor missing'
i = s.find(old_head)
j = s.find('### 过程教训', i)
assert j > i

new = """### CPU 分摊：区间内是两条曲线，但**外推被实测推翻**（P199 CORRECTED / P200）

| 提示 tokens | 1151 | 2213 | 4345 | 7186 | 14324 |
|---|---|---|---|---|---|
| 现役 auto/3072 | **2.87 s** | **4.00 s** | 6.86 s | 11.80 / 11.26 s | 20.25 / 20.36 s |
| `CPU_SHARE=0` | 5.42 s | 5.46 s | 6.87 s | 11.68 / 11.34 s | 20.26 / 20.34 s |

- ≤4.3K：`=0` 明显慢；**≥4.3K：两者完全收敛**（差 0.1–0.5%）。
- ⇒ **`=0` 在任何长度都不赢，生产维持 `auto` / 3072**。
- **我的错**：只用 1151/2213/4345 三点拟合（auto=1.20s+1.316ms/tok、=0=4.74s+0.493ms/tok），
  按此外推 8K 得 8.69 s（−26%），实测 7.2K 是 **11.68 s**，方向反了 —— `=0` 的曲线 4K 后上弯（边际 1.69 vs auto 1.32）。
- **新硬规矩（P200）**：任何"边际速率/每 token 成本"型结论，外推前必须在取样区间的**一半与两倍**处各补一个实测点。
- 机理部分仍成立：`=0` 的固定项 4.74 s ≈ PCIe 搬 72 GB（并集 94 GB − 缓存 21.8 GiB）@ 15 GB/s。
- 附带确认：`strata_tune` **不支持** per-request `prefill_cpu_share`（server.py:1446-1468 只认 pcie_frac/spec_min_p/prefill_pipe/aux_cpus），
  所以"按长度自动切换"这条路不存在；现在连"手动切档"也不必了（没收益）。

"""
s2 = s[:i] + new + s[j:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s2)
print('ok len', len(s2))
print([l for l in s2.split('\n') if l.startswith('### ')][-3:])
