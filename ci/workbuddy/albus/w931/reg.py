# -*- coding: utf-8 -*-
"""W931: R70 结项 + R75（R66 x auto:16384 组合）+ 队列 + P259"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

# ---------- PROGRESS ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "R70":
        f[6] = "1"
        f[7] = "DONE_NEG"
        f[8] += (
            " 【W931 实测 2026-11-04 01:0x-01:4x｜7 次重启，生产已恢复】扫 `--prefill` 四档："
            "**32K prompt 呈倒 U** —— 8192(4 chunk) **40.548 s** / **16384(2 chunk) 38.542 s(−4.95%)** / "
            "32768(1 chunk) 39.263 s(−3.17%)。**跨长度**：16K **20.775 → 20.233(−2.61%)**、"
            "**64K 71.130 → 76.557(+7.63%，变慢)**、6.4K 8.901 → 8.764(−1.5%，2CV 边界内≈0)。"
            "**机制（本轮最大收获）**：chunk 在抢 expert cache —— 日志 borrows **1578 / 2606 / 4667 slots** "
            "(4.62 / 7.62 / 13.64 GiB，占 7463 的 21.1 / 34.9 / **62.5%**)，`--prefill auto` 的定义就是"
            "「expert cache 能借到的最大 chunk」⇒ chunk ↑ 借得多 ⇒ 常驻专家 ↓ ⇒ 长 prompt 更多 stream。"
            "短 prompt 因减少 chunk 切换而赢，长 prompt 因 cache 变小而亏。"
            "**不采纳的理由（净值核算）**：真实负载 6517 样本 —— ≤8192 占 **60.8%**(无差异)、16–32K 占 5.8%(−5%)、"
            "**>64K 占 24.8%(+7.6%)** ⇒ 加权 **≈ +1.5% 变慢**。**顺带纠正我的先验**："
            "「主要场景是 6.4K」是我的测试 prompt，真实负载中位 4378、**p90 106301**、max 206226、39.2% >8192。"
            "`auto:32768` 借走 62.5% cache，不建议任何长度使用。**新假设已立 R75**：R66 三条 opt-in 把 borrows "
            "降 22.3%(1578→1226)，当时因 chunk=8192 不是瓶颈而 DONE_NEG；chunk=16384 时它可能正是瓶颈 ⇒ "
            "组合后 borrows 2606→约 2030，或可让 16384 在 >64K 上也不再变慢"
        )
        lines[i] = "\t".join(f)
        print("R70 -> DONE_NEG")

# 追加 R75
r75 = [
    "B3内存与缓存",
    "R75",
    "R66 三条 opt-in × `--prefill auto:16384` 组合：用 PF_GROUP_SCRATCH/PF_HC_REGION/PREFILL_ROUTED_STREAM 把 "
    "borrows 从 2606 压回约 2030，看能否让大 chunk 在 >64K 上也不再变慢",
    "W931 §4",
    "count", "1", "0", "OPEN",
    ("**W931 立（2026-11-04 01:4x，零停服）**：两条**单独都不成立**的实验组合起来逻辑成立 —— "
     "①R66（三 opt-in）单独：borrows 1578→1226(−22.3%)、prefill −0.23%（噪声内）⇒ 当时 DONE_NEG，"
     "原因是 chunk=8192 时 borrows 不是瓶颈；②`auto:16384` 单独：16–32K 赢 −5.0% 但 >64K 亏 +7.6%"
     "（>64K 占负载 24.8%）⇒ 净亏。**组合假设**：chunk=16384 时 borrows 2606(+65%) 正是长 prompt 变慢的直接原因，"
     "R66 把它压 22% ⇒ 约 2030，可能让 16384 在 64K 上不再变慢，从而白拿 16–32K 的 −5%。"
     "**做法**：用 `~/strata166/work/r66`（已含三补丁）+ `--prefill auto:16384` + 三个 env，一次编译装二进制、"
     "一次重启；测 16K/32K/64K 三档，各 2–3 rep。**判据**：①路径断言 —— borrows 必须降到 ~2030（日志 + 显存布局）；"
     "②64K 的 TTFT 不再高于 8192 基线（71.130 s）；③16–32K 保住 −2.6~−5%。三条全过才采纳，"
     "否则退回 `auto`。**风险**：R66 三补丁曾随 W921 判 DONE_NEG，若组合也不成立则彻底关闭这条线"),
]
lines_out = []
for l in lines:
    # 插到 R74 之前（R75 编号在 R74 之后，插在其后）
    pass
# 直接追加到末尾之前（保持追加顺序）
# 找到最后一个非空行位置
while lines and lines[-1] == "":
    lines.pop()
lines.append("\t".join(r75))
lines.append("")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("R75 appended")

# ---------- W832 队列 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 01:4x 修，`W931`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70"
            "（chunk 倒 U：16384 在 16–32K 赢 5%、>64K 亏 7.6%，净亏 1.5%）~~ → **R75**（R66 × auto:16384 "
            "组合：压 borrows 让大 chunk 在长 prompt 也不亏） → **R65**（只读） → **R74**（W4A4 精度门） "
            "→ R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))

# ---------- PARAM_REGISTER P259 ----------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
rows = io.open(q, encoding="utf-8").read().split("\n")
p259 = "\t".join([
    "P259", "CLI", "--prefill auto:N（chunk 上限 8192/16384/32768）", "auto（8192，保留）",
    "chunk", "REFERENCE", "P04", "-", "-", "W931",
    ("**W931 实测（2026-11-04，7 次重启）**：32K prompt 倒 U —— 8192 **40.548 s** / **16384 38.542 s(−4.95%)** / "
     "32768 39.263 s(−3.17%)；16K −2.61%、**64K +7.63%（变慢）**。**机制**：borrows 1578/2606/4667 slots "
     "(21.1/34.9/62.5% of 7463) —— chunk 与 expert cache 抢同一批槽。**净值核算（6517 样本真实负载）**："
     "≤8192 占 60.8%(0)、16–32K 5.8%(−5%)、**>64K 24.8%(+7.6%)** ⇒ 加权 +1.5% ⇒ **保持 auto**。"
     "**可操作**：若某段时间负载集中在 16–32K，可临时设 `auto:16384` 换 −2.6~−5%；**不要用 auto:32768**"
     "（借 62.5% cache）。待 R75 验证组合后可能改为采纳"),
])
# 插到 P258 之后
at = None
for i, rr in enumerate(rows):
    f = rr.split("\t")
    if f and f[0] == "P258":
        at = i + 1
        break
if at is not None:
    rows.insert(at, p259)
    print("P259 inserted")
else:
    rows.append(p259)
io.open(q, "w", encoding="utf-8").write("\n".join(rows))
print("done")
