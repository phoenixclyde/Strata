import io

p = "albus/w1039/deep_dive.md"
s = io.open(p, encoding="utf-8").read()
i = s.find("## 五、这一轮学到的判据")
assert i > 0
new_tail = """## 五、这一轮学到的判据（写进方案）

> **在 gfx906 上把 dot4 引进热路径之前，先算净节省：每 8 个 MAC 只省 3 条指令。**
> 8 MAC = 2 条 `v_dot4` + 3 条收尾（`cvt` + 2 个 `mul`，把 int32 累加和两个 scale 乘回 float）＝ 5 条；
> 基线是 8 条 `fma`。**4× 的算术密度，被"每头一次收尾"吃回到 1.6×。**
> 再把量化成本摊进去：一个 cell 只省 36 条（12 头 × 3），而每块 448 条的量化摊到 8 个 cell 上是 **56 条/cell** ⇒ 净 **+20 条/cell**，
> 与实测 +6.8% 同量级。
>
> 两条推论，下次直接套：
> ① **收尾能不能省**？`dot8_dp4a` 里 `(float) acc * (qs * ks)` 是每头每 cell 一次；若把 12 个头的 acc 先加总再乘（数学上不等价，
> 因为每头 qs 不同）或把 qs 融进 k scale（可行：qs 是每 64 值一个的常数），就能把这 36 条压到 ~3 条。
> ② **量化摊销比**：量化一次要能被 ≥4 个"用到它的 cell"共享才划算（skyne98：摊薄 1.67×，热路径 0.34×）。
> 我们每块量化一次、每块只 64 个 cell、且**每个 query 有 64 个块各做一遍** ⇒ 摊销没发生。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s[:i] + new_tail)
print("section 5 rewritten; len", len(s[:i] + new_tail))
