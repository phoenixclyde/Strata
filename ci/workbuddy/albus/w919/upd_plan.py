import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")
p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()

# 1) 修执行顺序行（W918 只加了表行，没改这一行；W919 一并补 R66/R65 与新增四条）
old_order = "> **执行顺序（2026-11-03 20:4x 修）：~~R59 已结~~ → R61 → R60 → R58 → R63 → R64 → R49 → R50 → R30′ → M3**（R51/R52/R54/R55/**R62** 均已结）"
new_order = (
 "> **执行顺序（2026-11-03 22:4x 修，`W919`）：~~R59 已结~~ → **R67（PLE mlock，待机主确认重建容器）** → **R66**（三条 opt-in cherry-pick）"
 " → **R68**（stop bound）→ R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**"
 "（R51/R52/R54/R55/R62 均已结）\n"
 "> **`W919` 说明**：R67 是**现成的损失**（PLE 26.8 GiB 一直没锁进 RAM，上游实测 decode 最多 −6%），不需改一行代码；"
 "R66/R68 是 0.2.10 里与架构无关的三条修复中命中我们形状的两条（R66 的三条 opt-in 仍在前）。"
 "R61 被排到它们之后：`W916` 的算术预判已指向「VALU 50–65%，R60 大概率不该做」，"
 "而 R66 的 `PF_GROUP_SCRATCH` 直接改 MMQ 缓冲布局，可能比 stream-k 更对症。"
)
assert old_order in s, "order line not found"
s = s.replace(old_order, new_order, 1)

# 2) 表格加 R67-R70（插在 新14/R66 之前，编号 新15..新18）
anchor = "| **新14** | **R66** |"
assert anchor in s

new_rows = (
"| **新15** | **R67** | PLE 表 26.8 GiB 的 mlock：容器 memlock 只有 8 MiB，表一直以**可回收**方式驻留（`VmLck 0`）"
" | 改容器 `--ulimit memlock=-1` 后重建，判据 `VmLck ≈ 26.8 GiB`、日志无 mlock failed、TTFT 不劣化、decode `|Δ|≥2×CV`"
" | **需重建容器（破坏性，待确认）**；已用临时容器验证 mlock 可成功 |\n"
"| **新16** | **R68** | `#4677` serve stop bound（`243fdb21`）：**HIP only**，单请求投机 + park 的末窗口快照被截断，避免快照被拒后回退旧 checkpoint"
" | 输出逐位相同 + 多轮第 2 轮 prompt 重读量下降；**不需 KL 门**（自述与旧标量循环一致，2736 例测试）"
" | 只动实验 worktree；上游实测 4/16→0/16、复用 98.36→99.74% |\n"
"| **新17** | **R69** | `#4590` penalty 窗口（`ed76b12f`）：惩罚改按回复自身 token 计，不再吃 prompt 尾部（我们是 Qwen，症状=新任务重复旧 JSON）"
" | **会改输出** ⇒ 先过 `W913` 精度门（KL ≤0.005 / top-1 ≥99%，分辨率 0.0032）"
" | 不影响 prefill/decode 主战场，排在 R64 之后 |\n"
"| **新18** | **R70** | 借 0.2.9「gfx12 chunked 从 64 token 起」的**调参维度**：在 gfx906 上扫 prefill chunk 阈值（现 auto=8192 / CPU share 1024）"
" | 1K/3K/6K 三档 TTFT，每组 ≥3 rep，`|Δ|≥2×CV`；不改代码"
" | 只读扫描，零停服 |\n"
)
s = s.replace(anchor, new_rows + anchor, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("plan updated; order+4 rows")
