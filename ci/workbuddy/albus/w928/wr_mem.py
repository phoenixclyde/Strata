# -*- coding: utf-8 -*-
"""W928 记忆写入（跨日，写新文件 2026-11-04.md）"""
import io, os

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory")
M = os.path.abspath(M)
os.makedirs(M, exist_ok=True)
p = os.path.join(M, "2026-11-04.md")

sec = """
## 00:3x W928 · 「二选一」是错的：四维正交 + k8v8 的真身 + dot8 上限修正
- **机主三问**：①「你不能两个都有，要用哪个用哪个，这个是二选一？」②「那 k8v8 呢？」。两问各打中我一处错。
- **错 1：把「档位」和「指令」压成一维**。正确框架是**四维正交**：①权重格式（Q4_K/Q5_1/Q8_0/NVFP4，pack 已定死）②**激活精度**（Q8_1=int8 / int4 / FP4-E2M1，**可按张量类型分别设**）③**指令**（`v_dot4` 4MAC / `v_dot8` 8MAC-i4×i4 / fp16 FMA，**由②的位宽决定**）④**KV 格式**（fp16/int8/q4_0/k8v4，与①②③**完全正交**）。
- **硬证据：W4A4 与 W4A8 在我们树里就是两个并存的 TU** —— `src/prefill/mmq_nvfp4_w4a8.cu`(1360B，编进 `strata_mmq`，默认) 与 `mmq_nvfp4_w4a4.cu`(2612B，单独编成 `strata_mmq_w4a4`，需 sm_120a)；`CMakeLists:2169/2214`。切换只是 w4a8 那份里一句 `#undef BLACKWELL_MMA_AVAILABLE` + `#define blackwell_mma_available(cc) false`。⇒ 档位是开关，不是架构决定。
- **「要用哪个用哪个」的判据 = 权重位宽**（dot8 是 i4×i4）：Q4_K(u4) ✅（XOR+修正，W927 ALL MATCH，gate/up 47/48 层）；Q4_0/IQ4_NL ✅（PLE 表，不进 MMQ）；**Q5_1/Q5_K(5bit) ❌、Q8_0(8bit) ❌**（down 43 层 Q5_1 + 5 层 Q8_0）。⇒ **同一层里 gate/up 走 dot8、down 保持 dp4a，就是「两个都有」**；MMQ 本来就每类型一个编译实例（`DECL_MMQ_CASE`、`mmq_tab` 9 类型），加实例而非改全局。
- **错 2：Amdahl 覆盖面虚高 1.7×**。W927 用「MMQ 占 prefill 34.6%」，但那是 gate/up 20.8% + down 13.8% 的和，**dot8 只覆盖 gate/up 的 Q4_K = 20.4%**。重算：20.4% × 26.7%（dp4a 减半）× 0.81（VALU） = **4.41% of prefill → 3.22% 端到端**（原报 5.5%）。**3.22% = 噪声门 3.2%，刚好压线**；且 R51 先例是理论 4.15% 实测 −6~−10%。
- **k8v8 真身 = `--kv int8`**，不是待实现的东西：`generate.cpp:3835` 白名单只有 `fp16/int8/q4_0/k8v4`，**没有 k8v8 这个名字**；`qsa_prompt_attn.cu:89` 写明 `KV_MODE 1: int8 codes + fp16 scale per 64 values`（K 和 V 都 int8）。
- **k8v8 已有账（P04/P50/P247）**：1056 vs 816 B/cell（**+29.4%**）、省 3.8 GiB ≈ **1700 专家槽**、**decode −7.7~−16.6%**、**质量 KL 0.0416 优于 k8v4 的 0.0704**。且 `AUDIT21/C5` 已澄清：k8v4 的采纳理由是「省 3.8 GiB」**不是「质量已证」**。
- **k8v8 未核的一半 = prefill 代价（M3，W835 立、一直 OPEN）**：k8v4 的 V 是 q4_0、**gather 时反量化成 fp16**（多一次 4-bit 解包 + scale 乘）；int8 的 V 是 int8、少这一步但多读 29.4% 字节 ⇒ 净效应从未量过。**零代码，只换一个 CLI 参数** ⇒ 提级到 R74 之前。
- **W4A4 精度的先验（重要）**：上游自己在 w4a8 头注释里写 *"On sm_120 mmq.cuh compiles NVFP4 as FP4 x FP4 (W4A4) … the first token's distribution **drifts by KL 0.0004-0.03** from the exact FP16 prefill (8 prompts)"* ⇒ **跨两个数量级**，我们的门是 0.005 ⇒ **五五开，必须实测**。R74 做法改为**先离线模拟量化器算 KL，过门才动内核**（省一次编译+重启）。
- **组合矩阵**：W4A4(gate/up) + dp4a(down) + `--kv int8` + PLE mlock **全部可同时成立**（四维互不冲突）；不成立的只有「W4A4 用于 down（5bit 塞不进 i4）」和「dot8 用于 P·V（需 P 也量化成 int4）」。唯一真 trade-off 是 k8v8 的 3.8 GiB vs 1700 专家槽。
- **队列**：`~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → **M3**（k8v8 prefill，零代码） → **R74**（W4A4 精度门，上限已修为 3.22%） → R69 → R70 → R65 → R49 → R50 → R30′`。
- **方法纪律 ⑥⑦**（写进 W832）：⑥报「某优化能覆盖多少」必须逐项核对**它的作用对象**（张量类型/位宽/相位/子系统），**不能用子系统总量代替**；⑦**「档位」与「指令」是两个维度**，凡出现「A 或 B 二选一」先检查是不是把两个维度压成了一维。
- 产物：`deploy/W928_FLAG_ORTHOGONAL_DIMENSIONS.md`；`PROGRESS.tsv` R74 备注改写 + M3 提级；`W832` 队列与纪律。**零改动生产**（`/health ok`、restarts=0、engine `a97f4479`、config `51ef8837`）。
"""

with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("written", p, len(sec))
