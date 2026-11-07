import io

P = ".workbuddy/memory/2026-11-07.md"
ADD = """
### W1039 救法（09:52–10:05）warp-per-group 把 DP4A 从 +6.8% 翻到 −11%

- **改一处**：`qsa_decode_attn.cu` 的 `if constexpr (OPT & 2)`，量化从「48 线程各串行 64 元素两遍」改成 warp 轮转（48 组 ÷ 8 warp、每 lane 2 值、5 级 `__shfl_xor` 求 amax、各转自己 2 值）。形状抄 llama.cpp `quantize_q8_1`。
- **实测**（ctl b12180 vs pa5+ATTN_DP4A，同窗口 n=4）：`qsa attn` 575→510（−11.22%）/ 2234→1982（−11.29%）/ 4714→4212（−10.65%）；整条 prefill −0.66%（2×CV 5.07 不显著）/ **−1.78%**（2×CV 0.50）/ **−1.61%**（2×CV 0.11）。
- **位相同**：`max` 与顺序无关、`d` 与码字逐元素同一表达式 ⇒ 收益全来自调度（旧 48/256 线程、448 条/线程；新 256/256、≈84 条），数值面没被掺进来。
- **状态 OPEN 不是 DONE**：D4 数值门（KL ≤0.0139 / top-1 ≥99%）未开 ⇒ pa5（`c639b60c`/43,475,584）**未装机**，在产仍 `b12180`。
- **顺序固定**：数值门 → 装机；数值不过直接回滚，不为 −1.8% 破质量线。
- 分支 `gfx906/port-all` @ `62d10e25`；窗口重跑本 2 次、停机 90 s，config 已还原 `5e9b81e2…`。
"""
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD)
print("mem appended", len(ADD))
