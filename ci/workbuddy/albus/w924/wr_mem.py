import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 00:4x（11-04）W924 · R58：MMQ Q4_K 三段计数 = 无段 >50%，但算出 MAC/指令 2.44（VALU 81%）
- **R58 = DONE_NEG（判据不满足，不动码）**。ISA 计数（`mmq-instance-q4_k.cu.o`，**54 个内核**）：**dp4a 5,184**；解包（`v_and` 871+`v_lshr` 368+`v_lshl` 198）**1,437 = 27.7%**；LDS（`ds_read_b32`）**1,204 = 23.2%**；缩放（`v_mul_f32` 596+`v_fma` 308+`v_mac` 96+`v_cvt` 64）**1,064 = 20.5%**；地址计算（`v_mul_lo_u32`）**824 = 15.9%**；标量载入 338 = 6.5%。最大 27.7% < 50% ⇒ 不动码，与 R51 实测（改 Q4_K 解包慢 6–10%）互证。
- **`v_mul_lo_u32` 归属必须查**：反汇编上下文是 `v_mul_lo_u32 v18, s29, v5`（SGPR 步长 × VGPR 索引）⇒ **地址计算，不是缩放**。分类错了会把缩放高估到 36%。
- **【硬结论】R60 确认不做，依据升级**：VALU 指令 = 5184+1437+1064+824 = **8,509**；MAC = 5184×4 = **20,736**；**MAC/指令 = 2.44（0.41 instr/MAC，比 W904 微基准 0.75 好 45%）** ⇒ VALU 上限 **6.624T × 2.44 = 16.2 TMAC/s**，生产 MMQ 相位 13.2 = **81% 占用** ⇒ 远高于 40% 门。比 W916 的"50–65%"硬（分子分母同出真实内核）。
- **【给 R63 定靶】地址计算 15.9%** 的形态正是 `readfirstlane` 能提到 SGPR 的那类。R63 判据改两段：①**路径断言**——改完后 ISA 里 `v_mul_lo_u32` 计数应显著下降（不是看时间差）；②再看 prefill `|Δ|≥2×CV`。上限：指令率 2.44→2.90（+19%），但 VALU 已 81%、LDS 占 23.2% ⇒ 可能被 LDS 接手，别预设。
- **坑（写进档案）**：直接 `llvm-objdump -d xxx.cu.o` **只出 x86 host 代码**（33,045 行、`endpgm` 0 个）；必须先 `llvm-objcopy --dump-section=.hip_fatbin` 再 carve（W909 的 `carve_elf.py`）。
- 进度 **91/156 = 58.3%**，主线 **91/128 = 71.1%**。队列 `~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → **R63** → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3`。
- 产物：`deploy/W924_R58_MMQ_THREE_SEGMENTS.md`；`PROGRESS.tsv` R58(DONE_NEG)+R63 备注；`W832` 队列。零停服、生产未动。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
