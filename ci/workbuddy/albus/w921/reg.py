import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

# 1) R66 -> DONE_NEG
lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R66":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W921 实测 2026-11-04 00:2x｜3 次重启，生产已恢复】**三条全部生效但 prefill 无收益**。"
                 "移植：`fbf6e1c7` 12 hunk 全成功、`5273fb66` 6 hunk 全成功、`3cc47f02` 在 p1 之后 5 hunk 全成功"
                 "（W918 说的 1 处手解实际不需要）。编译用 `ninja -t commands` 抽单条编译+归档+链接行逐条执行，"
                 "**不能跑全量 ninja**（cmake 会重跑，而 `STRATA_GGML_DIR=/llama.cpp` 在镜像内不存在 ⇒ add_subdirectory 失败）。"
                 "产物 `2fa104e5`（40,782,104 B）。**路径断言**：日志有 ROUTED_STREAM 的完整提示；"
                 "**决定性证据 = `prompt path borrows 1578 slots (4.62 GiB)` → `1226 slots (3.59 GiB)`，少借 352 slots / 1.03 GiB（−22.3%）**。"
                 "**A/B**（同脚本、去冷启、rep2-9 median）：prefill **8.819 → 8.799 s = −0.23%**（CV 1.6/1.0%）、"
                 "decode 79.24 → 78.19（−1.3%，cache 槽数与 VRAM free 均相同 ⇒ 噪声）⇒ **够不到 2×CV，无收益**。"
                 "**副产物 1**：三开关关掉时 borrows 回到 1578 slots，与基线逐字相同 ⇒ **补丁关闭时 bitwise 等价**（自述获实测印证）。"
                 "**副产物 2**：省下 1.03 GiB 借用 ⇒ 立 R72。**生产已恢复**：二进制用 `mv` 换 inode 回 `a97f4479`"
                 "（`cp` 报 Text file busy）、config 回 `51ef8837`（env 9）、health ok、restarts=0、ulimits 保留 memlock=-1")
        lines[i] = "\t".join(f)
        print("R66 -> DONE_NEG")
        break
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))

# 2) R72 新条
r72 = ["B4上游移植", "R72",
       "用 R66 三开关省下的 1.03 GiB 把 GPU expert cache 从 7463 槽扩到 ~7800（配合降 --vram-reserve-mib 832→~600），看 decode 命中率与速度",
       "W921 §4", "count", "1", "0", "OPEN",
       "**W921 立（2026-11-04 00:2x，零停服）**：R66 实测三条 opt-in 生效后 `prompt path borrows` 从 1578 slots(4.62 GiB) "
       "降到 1226 slots(3.59 GiB)，**少借 1.03 GiB**；但 `expert cache 7463 slots / 21.79 GiB`、`VRAM free 920 MiB` 都被 "
       "`--vram-reserve-mib 832` 卡住，这 1 GiB 没被利用。1.03 GiB ÷ 3 MiB/槽 ≈ **+350 槽（+4.7%）**。"
       "**做法**：保留 R66 三条补丁（实验分支）+ `--vram-reserve-mib` 832→~600，量 `expert cache N slots`、"
       "`decode expert cache hit rate`、decode tok/s。**判据**：`|Δ|≥2×CV` 且命中率不降；不达标就关。"
       "**风险**：reserve 降低后 `VRAM free` 可能逼近 256 MiB 的红线（源码注释：低于 256 MiB 时后续分配会让驱动 page、"
       "verify 图自旋不返回）⇒ 必须保证最终 `VRAM free ≥ 300 MiB`",
       "W921;W920"]
with io.open("PROGRESS.tsv", "a", encoding="utf-8", newline="") as f:
    assert len(r72) == 10
    f.write("\t".join(r72) + "\n")
print("R72 appended")

# 3) W832：队列 + 表格行
p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = "> **执行顺序（2026-11-03 22:4x 修，`W919`）：~~R59 已结~~ → **R67（PLE mlock，待机主确认重建容器）** → **R66**（三条 opt-in cherry-pick） → **R68**（stop bound）→ R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**"
new = ("> **执行顺序（2026-11-04 00:3x 修，`W921`）：~~R59 已结~~ → ~~R67 已结（零收益，机主决定保留 → P256）~~ → "
       "~~R66 已结（三条生效、prefill −0.23% 噪声内，不采纳）~~ → **R68**（stop bound）→ **R72**（用省下的 1.03 GiB 扩 cache）"
       " → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
assert old in s, "order line not found"
s = s.replace(old, new, 1)
anchor = "| **新15** | **R67** |"
row = ("| **新19** | **R72** | 用 R66 省下的 **1.03 GiB** 把 GPU expert cache 从 7463 槽扩到 ~7800（配 `--vram-reserve-mib` 832→~600）"
       " | `|Δ|≥2×CV` 且 `decode expert cache hit rate` 不降；结束时 `VRAM free ≥ 300 MiB` | 需保留 R66 三条补丁（实验分支）；零停服先量 |\n")
assert anchor in s
s = s.replace(anchor, row + anchor, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
