import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R72":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W923 计算 2026-11-04 00:0x｜零停服｜用计算替代盲目测试】**前提被证伪：省下的 1.03 GiB 是 borrow 减少（prompt 期间临时占用），不是常驻显存**，"
                 "能动的只有 `--vram-reserve-mib` 下调那部分。实测每槽 **2.990 MiB**（21.79 GiB / 7463 槽）；"
                 "reserve 832→700/600/500/400/300 分别只多 **45/78/112/145/178 槽（+0.6%~+2.4%）**，"
                 "且 reserve 越低 VRAM free 越接近 256 MiB 红线。"
                 "**decode 命中率实测 91.0–95.7%（稳态 ~93%）**，容量 +1.9% ⇒ miss 7%→6.87% ⇒ 命中率 **+0.13pp** ⇒ decode **<0.2%**，"
                 "**远低于 2×CV（2–3%）⇒ 不做**。"
                 "**顺带查清一个易误判的历史点**：日志里有 218 次 `expert cache 9901 slots, 22.31 GiB`，"
                 "但那是 **旧 pack `huihui-ud-iq4_xs` 时期**（每槽 2.31 MiB）的，与当前 `ud-q4_k_xl`（每槽 2.99 MiB）不可比，"
                 "**不能当作『曾经有过 9901 槽』的目标**。**方法论**：上限 < 2×CV 的条目应在**计算阶段**判死，不占用重启窗口——"
                 "本条省下约 20 分钟（2 次重启 + 测试）")
        lines[i] = "\t".join(f)
        print("R72 -> DONE_NEG")
        break
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))

p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 00:5x 修，`W922`）：~~R59~~ → ~~R67~~ → ~~R66~~ → "
       "~~R68 已结（不复现 bug，无收益空间；产出 P257 宏规则）~~ → **R72**（用省下的 1.03 GiB 扩 cache）"
       " → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 00:1x 修，`W923`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → "
       "~~R72 已结（上限 <0.2%，计算阶段判死）~~ → **R61（PMC 定 R60 生死）** → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
