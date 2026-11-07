import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

# R68 -> DONE_NEG
lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R68":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W922 实测 2026-11-04 00:4x｜零停服】【W922 实测 2026-11-04 00:4x｜零停服】"
                 "**① 决定性发现：上游所有 HIP-only 补丁在我们 gfx906 上是死代码**——`CMakeLists.txt:702` 本地注释写明 "
                 "**gfx906 不定义 `STRATA_USE_HIP`**（全局定义会切 CUDA-only 路径，W717/P23 实测过），"
                 "编译命令里只有 `-DSTRATA_HIP_GFX906=1`，预处理计数 **0**；首编 `.o` 里 `STRATA_SERVE_STOP_BOUND` 字符串 = **0**。"
                 "正解：补丁那 4 处改成 `#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)`（仓库对 gfx906 的既有写法）。"
                 "**② 我踩的坑**：第一版 sed 全局改了 **20 处**宏 = 全局打开 STRATA_USE_HIP，正是 CMakeLists 警告的事；"
                 "已从原树 cp 回（md5 `c920756a`）重打补丁、只精确改 4 处（30/16137/16684/17113），原有 3 处复合条件未动。"
                 "**③ 判定**：产物 `9d9cbe17`（40,784,832 B）、`strings` 有开关、`nm` 有 `serve_stop_bound` **2 个**符号 ⇒ 补丁可移植且编对。"
                 "但**本场景不复现 bug**：单卡单流 spec4 下，4 段 6.7K 对话的第 2 轮复用率 **99.71–99.72%（4/4，`<99%` 段数 0/4）**，"
                 "只重读 **19 token（0.28%）**；上游症状是重读约 **6%**（无补丁 98.36% → 有补丁 99.74%）⇒ **我们已在其「有补丁后」的水平，无收益空间**。"
                 "**④ 测试三次失败都是同一个原因**：模型的 `message.content`/`reasoning_content` 在非流式下可能为空，"
                 "我未先 dump 结构就写解析（违反先看数据纪律）；不过三次都收敛到 99.7%，因为前缀匹配的是 turn1 的 prompt，与 assistant 长短无关。"
                 "**不采纳**；若将来改多流/--batch 须重测")
        lines[i] = "\t".join(f)
        print("R68 -> DONE_NEG")
        break
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))

# P257: STRATA_USE_HIP 死代码规则
prow = ["P257", "BUILD", "gfx906 构建不定义 STRATA_USE_HIP ⇒ 上游 HIP-only 代码在本项目是死代码",
        "移植时按补丁范围加 || defined(STRATA_HIP_GFX906)", "build", "ADOPTED", "-", "-", "P23",
        "W922 §1-§2",
        "【W922 立 2026-11-04 00:4x】`CMakeLists.txt:702` 本地注释：gfx906 (STRATA_HIP_GFX906) **does not define STRATA_USE_HIP**，"
        "因为 a global STRATA_USE_HIP would switch CUDA-only paths elsewhere（W717/P23 实测过）；只有 dflash2.cpp 被单独设 "
        "`COMPILE_DEFINITIONS STRATA_USE_HIP=1`。实测编译命令只有 `-DSTRATA_HIP_GFX906=1`，预处理计数 0。"
        "**后果**：所有上游标 \"HIP only (STRATA_USE_HIP)\" 的修复（如 #4677）移植后是死代码，"
        "首编 `.o` 里 `STRATA_SERVE_STOP_BOUND` 字符串 = 0。**正解**：把补丁那几处改成 "
        "`#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)`（仓库既有写法，见 generate.cpp:1583/2978/4163）。"
        "**禁令**：**绝不能 sed 全局替换**——实测全局改 20 处 = 全局打开 STRATA_USE_HIP = 正是 P23 警告的路径；"
        "必须从原树 cp 回、重打补丁、按上下文只改补丁范围内那几处"]
plines = [l for l in io.open("params/PARAM_REGISTER.tsv", encoding="utf-8").read().split("\n") if l.strip()]
plines.append("\t".join(prow))
io.open("params/PARAM_REGISTER.tsv", "w", encoding="utf-8").write("\n".join(plines) + "\n")
print("P257 appended, cols =", len(prow))

# W832 顺序
p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 00:3x 修，`W921`）：~~R59 已结~~ → ~~R67 已结（零收益，机主决定保留 → P256）~~ → "
       "~~R66 已结（三条生效、prefill −0.23% 噪声内，不采纳）~~ → **R68**（stop bound）→ **R72**（用省下的 1.03 GiB 扩 cache）"
       " → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 00:5x 修，`W922`）：~~R59~~ → ~~R67~~ → ~~R66~~ → "
       "~~R68 已结（不复现 bug，无收益空间；产出 P257 宏规则）~~ → **R72**（用省下的 1.03 GiB 扩 cache）"
       " → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
assert old in s, "order not found"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
