import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
hit58 = hit63 = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "R58":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W924 实测 2026-11-04 00:4x｜零停服】**判据不满足（无段 >50%），不动码**。ISA 计数（`mmq-instance-q4_k.cu.o`，"
                 "54 内核，先 `--dump-section=.hip_fatbin` 再 carve——直接 `objdump -d` 只出 x86 host，是坑）："
                 "**dp4a 5,184**；解包（`v_and` 871+`v_lshr` 368+`v_lshl` 198）**1,437 = 27.7%**；"
                 "LDS（`ds_read_b32`）**1,204 = 23.2%**；缩放（`v_mul_f32` 596+`v_fma` 308+`v_mac` 96+`v_cvt` 64）**1,064 = 20.5%**；"
                 "**地址计算（`v_mul_lo_u32`）824 = 15.9%**；标量载入 338 = 6.5%。"
                 "`v_mul_lo_u32` 经反汇编上下文确认是**地址计算**（`v18, s29, v5` = SGPR 步长 × VGPR 索引），不是缩放。"
                 "最大段 27.7% < 50% ⇒ 不动码，与 R51 的实测（改 Q4_K 解包慢 6–10%）互证。"
                 "**副产品一**：用真实配比算出 **MAC/指令 = 20736/8509 = 2.44（0.41 instr/MAC，比 W904 微基准 0.75 好 45%）** ⇒ "
                 "VALU 上限 6.624T×2.44 = **16.2 TMAC/s**，生产 MMQ 相位 13.2 = **81% 占用** ⇒ **远高于 40% 门，R60 确认不做**（依据从外推升级为实测配比）。"
                 "**副产品二**：地址计算 15.9% 的形态正是 `readfirstlane` 能提到 SGPR 的那类 ⇒ **R63 有了精确靶子**，"
                 "上限 ≤15.9% VALU 指令、指令率 2.44→2.90（+19%）")
        lines[i] = "\t".join(f); hit58 = 1
    elif f[1] == "R63":
        f[8] += (" 【W924 定靶 2026-11-04 00:4x】R58 的 ISA 计数给出精确靶子：**地址计算 `v_mul_lo_u32` 824 条 = dp4a 的 15.9%**，"
                 "形态是 `v_mul_lo_u32 v18, s29, v5`（SGPR 步长 × VGPR 索引）= **用 VALU 做本可在标量单元做的事**。"
                 "这正是 `__builtin_amdgcn_readfirstlane` SGPR hoisting 的目标。"
                 "**判据改为两段**：①路径断言——改完后 ISA 里 `v_mul_lo_u32` 计数应显著下降（这是\"确实执行到了\"的硬证据，不是时间差）；"
                 "②再看 prefill `|Δ|≥2×CV`。**上限**：VALU 指令 -15.9% ⇒ 指令率 2.44→2.90 MAC/instr（+19%），"
                 "但 VALU 已 81% 占用、LDS 占 23.2% ⇒ 实际可能被 LDS 接手，别预设")
        lines[i] = "\t".join(f); hit63 = 1
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))
print("R58 DONE_NEG:", hit58, " R63 note:", hit63)

p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 01:1x 修，`W923`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → "
       "~~R61 已结（PMC 工具不可用）~~ → ~~R60 已关（算术预判 VALU 50–65%）~~ → **R58**（MMQ vec_dot 三段计数）"
       " → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 00:4x 修，`W924`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → "
       "~~R58 已结（无段 >50%，不动码；MAC/指令 2.44 ⇒ VALU 81%）~~ → **R63**（readfirstlane 提地址计算，靶子 15.9%）"
       " → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
assert old in s, "order not found"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
