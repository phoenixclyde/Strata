import io
import re

# report denominators
R = "albus/w1039/reply.md"
s = io.open(R, encoding="utf-8").read()
s = s.replace("**396 条 / 已结 311 / 78.5%**（本轮 +9：`P445`–`P453`）",
              "**398 条 / 已结 312 / 78.4%**（本轮 +11：`P445`–`P455`）", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(s)

PL = "deploy/W832_OPT_PLAN_V2.md"
t = io.open(PL, encoding="utf-8").read()
ADD = """
**九、6.45% 的真身与下一条路（`P454` / `P455`）。** 逐点对齐两臂 4995 个位置：argmax 变了 **322 个（6.45%）**，
其中 **234（72.7%）** 是「第一名掉到第二名」；改动处的参考间隔（top1−top2）**p50 0.191 nat**、<0.5 nat 占 75%，
|Δlogp(target)| 中位 0.018。**int8 查询的步长 = amax/127 ≈ 1.3%×σ_q ⇒ 0.01–0.13 nat，正好压在这个分岔口上** ——
不是实现缺陷，是位宽与"判决间隔"同量级。
下一条路（`P455`，未实施）：**fp16 点积 `v_dot2_f32_f16`**，每 8 MAC 仍 5 条指令（与 int8 同）、q 误差降到 0.03%（小 40 倍），
预计 KL <0.001。工具链已验证可编（`__builtin_amdgcn_fdot2`，gfx906，CLANG=0）。
**纪律**：先编 → **先过数值门** → 再测速度；`P453` 的教训就是先测速度再补数值，白烧一个窗口。
"""
anchor = "**代价**：本回合停机累计 10 次 / 1089 s，最长单次 683 s。"
i = t.find(anchor)
if i > 0 and "**九、6.45% 的真身" not in t:
    j = t.find("\n---", i)
    t = t[:j] + "\n" + ADD + t[j:]
    print("plan §九 appended")
t = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1039 校正", "**398 条 / 已结 312 / 78.4%**（W1039 校正", t, count=1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(t)

M = ".workbuddy/memory/2026-11-07.md"
ADD2 = """
### W1039 T8/T9（10:38–11:0x）6.45% 的真身：误差压在 0.19 nat 的分岔口；下一条路 = fp16 点积

- **逐点对齐 4995 位**：argmax 变 322（6.45%），其中 **234（72.7%）是第一名掉到第二名**；改动处 top1−top2 间隔 p10 0.025 / **p50 0.191** / p90 1.06 / p99 3.96 nat；<0.1 nat 占改动 32%，<0.5 占 75%；|Δlogp| 中位 0.018。
- **机制**：int8 查询步长 = amax/127 ⇒ RMS ≈1.3%·σ_q ⇒ 0.01–0.13 nat，正落在 0.19 的分岔口上 ⇒ **不是实现错，是位宽**。KL 要 ≤0.0139 等于噪声再小 3 倍，单档 int8 做不到。
- **下一条路（P455，未实施）**：`v_dot2_f32_f16`（2 MAC/指令），8 MAC 仍 5 条（4 dot2 + 1 mul），k 侧 int8→f16 精确、scale 最后乘 ⇒ q 误差 0.03%（比 int8 小 40 倍），预计 KL <0.001、attn 仍 −8~−11%。工具链已验证 `__builtin_amdgcn_fdot2` 在 gfx906 编译通过。
- **纪律**：先编 → 数值门 → 速度窗。`P453` 就是顺序错（先速度后数值）白烧一个窗口。
- **报告**：新增 T8/T9 两节；`report_consistency` 已加「四、进度 分母 = 账本派生」硬门（负例自测通过）。
"""
with io.open(M, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD2)
print("memory appended")
