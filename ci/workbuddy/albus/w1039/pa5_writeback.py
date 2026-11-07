import io
import re

R = "albus/w1039/reply.md"
s = io.open(R, encoding="utf-8").read()

# 1) section 三: keep the old numbers AND add the new window
old3 = ("**三、本次落生产** — **重启 6 次 / 停机 264 s（129 + 135）/ 回滚 0 次 / 装机 0 次**。")
new3 = ("**三、本次落生产** — 前三窗口**重启 6 次 / 停机 264 s（129 + 135）**，救法窗口再**重启 2 次 / 停机 90 s**"
        " ⇒ 累计 **重启 8 次 / 停机 354 s / 回滚 0 次 / 装机 0 次**。")
if old3 in s:
    s = s.replace(old3, new3, 1)
    print("§三 updated")

# 2) denominator
s = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（本轮 \+6：`P445`–`P450`）",
           "**395 条 / 已结 310 / 78.5%**（本轮 +8：`P445`–`P452`）", s, count=1)

# 3) new section 七 before the footer
SEC = """## 七、救回来了：warp-per-group 把 DP4A 从 +6.8% 翻到 −11%（`P451` / `P452`）

只改一处（`qsa_decode_attn.cu` 的 `if constexpr (OPT & 2)`）：量化从「48 个线程各串行 64 元素跑两遍」改成
`for (grp = warp; grp < G*NSC; grp += WARPS)` —— 48 个组按 warp 轮转（每 warp 6 组），每 lane 2 个值，
`__shfl_xor` 五级求 amax，再各转自己那 2 个值。形状直接抄 llama.cpp 的 `quantize_q8_1`（一个 warp 一个块、每 lane 自己那一个元素）。

| 形状 | ctl `qsa attn` | pa5+DP4A | Δ | ctl 整条 | pa5+DP4A | Δ | 2×CV |
|---|---|---|---|---|---|---|---|
| 2.5K | 575 ms | **510** | **−11.22%** | 1584.4 µs/tok | 1573.9 | −0.66% | 5.07%（不显著） |
| 8K | 2234 ms | **1982** | **−11.29%** | 1253.6 | **1231.2** | **−1.78%** | 0.50% |
| 16K | 4714 ms | **4212** | **−10.65%** | 1278.7 | **1258.1** | **−1.61%** | 0.11% |

decode 59.00 → 61.45 tok/s（CV 8–10%，不可分）。

**为什么这次是纯收益**：`amax = max(|x|)` 对同一集合与顺序无关，`d = amax/127`、`round(x/d)` 逐元素同一表达式
⇒ **码字逐字节相同**，−11% 全部来自调度（旧 48/256 线程、每线程 448 条；新 256/256 线程、每线程 ~84 条）。
数值面因此**没有和性能面混在一起**——这是它能先测速度、后补数值门的前提。

**仍然缺的一半**：`deploy_gate` D4 要数值面（KL ≤0.0139 / top-1 ≥99%，或与 fp32 路径逐位相同）。本轮只做速度，
所以 `P451` 标 OPEN 不是 DONE，pa5 也**没有装机**（在产仍是 `b12180`）。

---

"""
anchor = "**产物**：`albus/w1039/reply.md`（本件）"
i = s.find(anchor)
assert i > 0
if "## 七、救回来了" not in s:
    s = s[:i] + SEC + s[i:]
    print("§七 inserted")

io.open(R, "w", encoding="utf-8", newline="\n").write(s)

# 4) plan: append §七 to the W1039 block
PL = "deploy/W832_OPT_PLAN_V2.md"
t = io.open(PL, encoding="utf-8").read()
ADD = """
**七、救回来了（`P451` / `P452`）。** 量化改 **warp-per-group**（48 组 ÷ 8 warp、每 lane 2 值、5 级 `__shfl_xor` 求 amax），
形状抄 llama.cpp `quantize_q8_1`。实测（同窗口、每臂 2 轮、n=4）：`qsa attn` **−11.22% / −11.29% / −10.65%**
（2.5K/8K/16K），整条 prefill **−0.66%（不显著）/ −1.78% / −1.61%**（2×CV 5.07/0.50/0.11）。
**位相同**：max 与顺序无关、d 与码字逐元素同一表达式 ⇒ 收益全来自调度，不掺数值变化。
**未结的一半**：D4 数值门（KL ≤0.0139 / top-1 ≥99%）没开 ⇒ `P451` 保持 OPEN、pa5 未装机。
下一步顺序固定：**数值门 → 装机**；数值不过就直接回滚到 `b12180`，不因为 −1.8% 破质量线。
"""
anchor2 = "判据（可复用）：引入 int8 dot 前先算「每 8 MAC 的净节省 − 每 cell 摊到的量化成本」，为负就别上。"
j = t.find(anchor2)
if j > 0 and "**七、救回来了" not in t:
    k = t.find("\n---", j)
    t = t[:k] + "\n" + ADD + t[k:]
    io.open(PL, "w", encoding="utf-8", newline="\n").write(t)
    print("plan §七 appended")

t2 = io.open(PL, encoding="utf-8").read()
t2 = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1039 校正", "**395 条 / 已结 310 / 78.5%**（W1039 校正", t2, count=1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(t2)
print("plan denominator -> 395/310")
