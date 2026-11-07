import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

# R73：v_dot8 for Q4_K 技术验证（已做，DONE）
r73 = ["B5本机缺口", "R73",
       "v_dot8_i32_i4 用于 Q4_K：验证 u4 权重能否零改格式喂进 dot8（`^0x88888888` + 修正项），并测吞吐",
       "W927 §3-§5", "count", "1", "1", "DONE",
       "**W927 实测（2026-11-04 01:3x，零停服，gfx906 上跑）**：**推翻 W909 的「不立移植项」**——那只在 **W4A8** 前提下成立；"
       "**W4A4 下 8 个 i4 只需 1 条 dot8，dp4a 要 2 条 ⇒ 指令减半**。"
       "**关键技术验证**：`v_dot8_i32_i4` 吃 i4(−8..7)，Q4_K 是 u4(0..15)，但 4-bit 补码里 `a_u4 ^ 0x88888888` 正好等于 u4−8，"
       "所以 `sum(a_u4*b) = dot8(a^0x88888888, b) + 8*sum(b)`，**权重侧零改格式**（1 条 XOR + 1 个可预计算修正项，或用 dot8(0x11111111,b) 一条算出）。"
       "**实测三路互证 ALL MATCH**：`a(u4)=[1,12,7,11,15,8,8,1]`、`b(i4)=[-5,-3,7,-1,-4,-4,-7,-2]` ⇒ 精确手算 / dp4a×2 / dot8+fix **全部 −153**。"
       "（踩坑：掩码先写成 `0x08080808`（按字节）得 −105，**nibble 级位运算必须按 nibble 写掩码**；`__builtin_amdgcn_sdot8` 要 **4 个参数**含 clamp。）"
       "**同架构先例（上网核）**：`Hong-agent/K100LC-RT4`（gfx926，无 MFMA/WMMA）实测 dot8 **75.5 TMAC/s = fp16 的 4.5×**、dot4 2.25×；"
       "其 `docs/FLASH-ATTN.md` 用全 int4（连 P 都存 int4）做到 **25.49 TMAC/s = dot8 上限 33.8%**、128k 精度 **4.2e-6**，"
       "并指出天花板来自 **dot8 只占指令槽 ~50%**。**⇒ 真门槛不是指令，是激活 int4 的精度**（立 R74）",
       "W927;W909;W924"]
with io.open("PROGRESS.tsv", "a", encoding="utf-8", newline="") as f:
    assert len(r73) == 10
    f.write("\t".join(r73) + "\n")
print("R73 appended")

# R74：W4A4 精度实验
r74 = ["B6判定探针", "R74",
       "W4A4 精度实验：把 MMQ 的 Q8_1 激活量化到 int4，用 W913 全词表 logits 仪器量 KL / top-1（这是 v_dot8 的真正门槛）",
       "W927 §4-§6", "count", "1", "0", "OPEN",
       "**W927 立（2026-11-04 01:3x，零停服）**：dot8 是 **i4×i4**，权重侧已验证零改格式（R73），"
       "但我们的激活是 **Q8_1(int8)** ⇒ 必须降到 **int4** 才用得上 dot8。这是**精度决策不是指令问题**。"
       "**A/B**：同一批 prompt，激活 int8（现状）vs int4，用 `STRATA_DUMP_FIRST_LOGITS`（`generate.cpp:18784`）取 248,320 维全词表 logits 算 KL / argmax。"
       "**判据沿用 W913**：KL ≤ 0.005、top-1 ≥ 99%，**分辨率 0.0032**（跨进程噪声底，同进程内为 0）。"
       "**上限（W924 ISA 计数 + W925 Amdahl）**：dp4a 5,184→2,592、总指令 9,713→7,121（−26.7%）⇒ "
       "**prefill +7.5%、端到端 +5.5%**，**过 3.2% 噪声门** ⇒ 精度若过门就值得动码。"
       "**参考**：K100LC 的 int4 attention 精度 4.2e-6（内核 vs 量化精确参考），说明 int4 激活在注意力量级可接受；"
       "但 MMQ 的激活是 gate/up 的中间结果，尾部更重，必须实测。"
       "**先做只读**：不改进生产，用实验 worktree 编一版 W4A4 的 vec_dot，跑 36 题 KL"
       "；**若 KL 超门**，退到「混合」：只把 down 的激活降 int4、gate/up 保持 int8（down 占 13.8%、gate/up 20.8%）",
       "W927;W913;W924"]

lines = io.open("PROGRESS.tsv", encoding="utf-8").read().rstrip("\n").split("\n")
lines.append("\t".join(r74))
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("R74 appended")

# W832：队列 + R64 重开支线说明
p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 01:3x 修，`W926`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → "
       "~~R64 已结（attention 实测不是 O(L²)、占 15% 稳定；k8v4 挡住 dp4a；上限 3.4–4.3% 压门，不做）~~ → **R69**（`#4590` penalty 窗口）"
       " → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 01:3x 修，`W927`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73 已结（Q4_K 的 u4 可直接喂 dot8，ALL MATCH）~~ → "
       "**R74（W4A4 精度实验——v_dot8 的真正门槛，上限 prefill +7.5%/端到端 +5.5%）** → R69 → R70 → R65 → R49 → R50 → R30′ → M3**\n"
       "> **`W927` 说明**：`W909` 的「v_dot8 不立移植项」**作废**（那只在 W4A8 前提下成立）；"
       "W4A4 下指令减半、端到端上限 5.5% 过 3.2% 门。**R64（attention）重开一条支线**但排在 R74 之后："
       "V 是 4-bit 恰好匹配 dot8、K100LC 证明 P 存 int4 可行（4.2e-6），但我们的 `qsa attn` 只占 15% 且远未到算力极限")
assert old in s, "order not found"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
