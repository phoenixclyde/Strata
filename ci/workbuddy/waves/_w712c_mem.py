# 追加今日日志：A2 解码基准 + 文档同步
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W712c A2 解码基准（2026-10-08 21:1x，Z0=off）
- 口径与历史一致：512 token x 3，temperature 0 / top_k 1，预热 2 条，serve。
- 实测（引擎日志权威行）：**512 generated in 11194 ms = 45.7 tok/s**（drafts 208/292 = 71.2%）、
  **512 generated in 11828 ms = 43.3 tok/s**（drafts 204/285 = 71.6%）；探针口径 37.27 / 46.02 / 43.53（中位 43.53）。
- 对历史（0.1.40.1 时代 42.9 tok/s）：差 **+1% ~ +6.5%**，**落在解码分辨力 9.5-15% 内 => 记"未见差异"**，不宣称提速。
  MTP 接受 71% 高于历史 61-66%，但那是短 prompt（73 token）的 draft 动态，与 18k prompt 不可直接比，只作记录。
- 结论：0.1.40.4 在 gfx906 上**预填/温 TTFT/前缀复用/缓存命中/解码五类口径全部未见差异**，升级"中性"闭环。
  证据 `deploy/tmp/_w712_decode_bench.out.txt`；脚本 `waves/_w712_decode_bench.py`。
- 文档同步：`W712_UPGRADE.md` §3 补 A2 表；`W712_PLAN.md` A2/C2 标完成；`configs/workbuddy-strata166.md` §6.5 换成新读数。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note))
