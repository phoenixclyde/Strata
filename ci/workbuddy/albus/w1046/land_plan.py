import io
import re

P = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
PORT = "albus/gfx906_survey/PORT_PLAN.md"
RECIPE = "deploy/REBUILD_RECIPE.tsv"

rows = [
    ["B5本机缺口", "P523",
     "更正 R103 的 B2 落点：HIP/gfx906 不编译 qsa_pattn；prompt 在 qsa_prompt_attn 拒绝后回退 qsa_decode_attn_batch，W1044 的 DP4A 已覆盖它",
     "W1046", "count", "1", "1", "DONE",
     "**源码核实**：`qsa_pattn.cu` 在 `__HIPCC__` 下 `STRATA_PATTN_BUILT=0`，`pattn_mode()` 恒 0；`prefill.cpp` 先尝试 `qsa_prompt_attn_batch`，HIP 拒绝后走 `qsa_pattn`（仍不可用）或既有 `qsa_decode_attn_batch`。W1042/W1044 的 C 臂已在生产形状 prefill 上实测 attn −10.5…−11.8%，证明 B1/B2 的数学已覆盖真实路径。⇒ **旧方案「下一步 B2 可再拿 prompt 2–4%」作废**，不得拿 `qsa_pattn.cu` 的死代码另开候选；`P435` 也只说对了一半（qsa_prompt_attn 被调用，但在 gfx906 上不执行其 CUDA 内核）。",
     "P435;P499;P513", "KW:STRATA_PATTN_BUILT|qsa_decode_attn_batch|B2 落点"],
    ["B5本机缺口", "P524",
     "R103-B3 候选：Q8_0 HC down 的 FP32 激活在 staging 时按 32 值量化成 int8，权重×激活走硬件 DP4A；默认 off，独立内核保留原 off 臂",
     "W1046", "count", "1", "1", "DONE",
     "**已实现/未装机**：分支 `gfx906/hc-dp4a @ 179bd6b5`，只改 `src/kernels/cuda/fused_gr.cu`，新增 `STRATA_HC_DOWN_DP4A=1` 与 `gr_down_q8_dp4a_kernel`；候选 `strata-0.1.57-hc4` md5 `df33d3a60eb4c8515b6f34e090af7e40` / 43,675,416 B。**零停机实测**：`gr_parity` 0 failures；`fused_gr_bench` off/on 均 0 differing（非 Q8 对照 hash 不变）；Q8 vs BF16 的 mixed rel-RMS 从约 0.0009→0.0012，确认新增激活量化不是 free/bitwise。拆单个 TU 的 fatbin 后 `fused_gr` **v_dot4_i32_i8=720、v_dot8_i32_i4=0、v_mad_i32_i24=87**。探索性 cold 子模式两臂都 timeout/dumped core，未取得干净计时，**不作性能结论**。**下一步必须**：同 exe off floor + on 的全词表 logits/锚、decode 长生成与任务门；停生产后交错 isolated HC bench + 引擎 A/B，收益 ≥ 当次 2×CV 才谈装机。",
     "P517;P500", "KW:hc-dp4a|179bd6b5|720"],
    ["B5本机缺口", "R109",
     "R103 后续移植面的唯一执行线：先判 B3 候选，再做 A1 exact DPP；A5 先解除死派发，A2/A3 诊断位只单开关复测，不把 bundle 当单变量",
     "W1046", "count", "1", "0", "OPEN",
     "**W1046 立并已开始执行**。顺序：① **B3**（`P524` 的 `hc4`，已建/未装）：off≡生产地板 + on 数值/任务门 + 隔离 HC 与引擎 A/B；任一失败即 DONE_NEG，不装。② **A1 native_router DPP**：独立分支、bitwise parity + ISA `v_mov_b32_dpp`、decode A/B；只在 B3 有结论后开窗。③ **A5 Q8_GATHER8**：`P425` 已证旧实现包在 `STRATA_EXPERIMENTAL_SM60` 里且字符串未进二进制，先证明生产 k8v4 真会调用再移植，否则保持关闭。④ A2/A3 不与 DP4A 同臂叠加，各自由同一地板单开关判。⑤ A4 编译 flag 必须逐 TU、最后做。**共同门**：默认 off；每臂一个变量；报告 attn/HC 相位与整条 2×CV；数值用 R104/W1044 的 fp32 logits + 锚 + 任务级门，decode 另补长生成。**停机**：当前零；B3 的计时/数值窗口需另报。",
     "P523;P524;P425", "KW:R109|B3|A1|A5"],
    ["B6判定探针", "R110",
     "k8v4 的 V 侧 dot8 可行性 spike：P 按 8-cell 组量化 int4，Q4_0 V 的 8 个 nibble 减 8 打包成 signed int4，做独立 P(int4)×V(int4) 原型；不是 dot8q，也不是 R91 的 Q4_K MMQ",
     "W1046", "count", "1", "0", "OPEN",
     "**源码核实**：k8v4 = int8 K + rotated Q4_0 V；`block_q4_0` 每 32 值为 fp16 scale + 16B nibble，8 个连续 V 值来自 8 字节的低或高 nibble，减 8 即 signed int4，硬件格式匹配。现 PV 循环是一线程一输出维、逐 cell FP32 FMA；首选原型沿 **8 个 cell** 打包 V，P 按 8-cell 组量化一次并被 256 个输出维复用，避免先重写 wave 布局。**QK-dot8 不作为首选**：Q 必须从 int8 再降 int4，误差更大。**验收顺序**：standalone 合成/真实 dump 对照（max/rel error）→ 微基准（与现 FP32 PV 同访问面）→ 只有微基准 >1.3× 且离线误差有预算才接入 OPT 新位 → fp32 logits/锚 + 16K/32K/64K needle + decode 长生成 + A/B。int32 累加按 8-cell 分组立即转 fp32，禁止跨 64 cell 裸累加。**与 `dot8q()` 无关**：后者是 8×fp32 FMA 函数名；本项 ISA 必须出现 `v_dot8_i32_i4`。零停机原型先行，不进生产。",
     "P501;R108", "KW:k8v4|P(int4)|V(int4)|dot8q"],
]

lines = io.open(P, encoding="utf-8").read().splitlines()
have = {l.split("\t")[1] for l in lines if l.count("\t") >= 9 and not l.startswith("#")}
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r), r[1]
    assert r[1] not in have, "duplicate " + r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)

n108 = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "R108":
        f[6] = "1"
        f[7] = "DONE"
        f[8] += " **W1046 去重**：与既有 R91（Q4_K MMQ dot8 六阶段）重复，R108 关闭并并入 R91；k8v4 PV 是不同落点，另由 R110 跟踪，禁止再把 dot8q 当硬件 dot8。"
        lines[i] = "\t".join(f)
        n108 += 1
assert n108 == 1
lines += ["\t".join(r) for r in rows]
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

tot = done = 0
for l in io.open(P, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
pct = 100.0 * done / tot
print("TOTALS", tot, done, round(pct, 1))

s = io.open(PLAN, encoding="utf-8").read()
s, n = re.subn(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1045；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1046；" % (tot, done, pct), s, count=1)
assert n == 1
oldq = "| **唯一队列** | ~~**R103 已装机（W1044：G1–G5 全过、冷启动复验）**~~"
newq = ("| **唯一队列** | **R109（W1046 置顶，R103 后续移植面：B3 `hc4` 已建未装，先过 off floor + 数值/任务 + 停机 A/B；随后 A1；A5 先解死派发）** → "
        "**R110（W1046 新立，k8v4 PV-dot8 独立原型：P(int4)×V(int4)，与 dot8q/R91 均不同）** → "
        "~~**R103 已装机（W1044：G1–G5 全过、冷启动复验）**~~")
assert s.count(oldq) == 1
s = s.replace(oldq, newq, 1)
s = s.replace("**R108（新立，`P501`：dot8 核心已移植并自检通过，但 `v_dot8_i32_i4` 还是 0 个调用点，接入需 `p→int4` + 数值门 + max-context 任务级门）**",
              "~~**R108 已并入 R91（W1046 去重；k8v4 PV-dot8 由 R110 单独立项）**~~", 1)

title = "### 回写 · W1046（2026-11-07 19:1x–19:3x）R103 后续方案入权威 + B3 候选 + k8v4 dot8 可行性（零停机）"
block = title + """

- **先纠正靶点（`P523`）**：`qsa_pattn.cu` 在 HIP 下 `STRATA_PATTN_BUILT=0`，不是 gfx906 的 prompt 热路径；真实回退是 `qsa_decode_attn_batch`，W1044 已装的 DP4A 已覆盖 B1/B2 的数学。旧 PORT_PLAN 的「B2 还可再拿 prompt 2–4%」作废，不能对死文件再移植一次。
- **R109 已置顶并开工**：B3 候选 `gfx906/hc-dp4a @ 179bd6b5` / `strata-0.1.57-hc4`（`df33d3a6…` / 43,675,416 B），默认 off 的 `STRATA_HC_DOWN_DP4A`。staging 时每 32 个 FP32 激活量化一次，Q8_0 int8 权重 × int8 激活走 `v_dot4_i32_i8`；原内核保留。`gr_parity` 0 failures、bench 0 differing；TU ISA `dot4=720 / dot8=0`。Q8 mixed rel-RMS 0.0009→0.0012 ⇒ 数值门不可省；cold 子模式两臂 timeout，无性能结论。**未装机，停机窗口另批**。
- **R110（k8v4 dot8）**：V 的 Q4_0 nibble 减 8 可匹配 signed int4；首选 `P(int4)×V(int4)` 沿 8-cell 原型，QK 侧需 Q 降 int4、暂不首选。与 `dot8q()`（8 次 fp32 FMA）和 R91（Q4_K MMQ）都分开。R108 与 R91 重复，已合并。
- **外证只用于设计**：MI50/vLLM 的 gfx906 FA 实测 Q 量化 Q8_0 + dot4 可达 4.45 TFLOPS，且 FP32 scale/accumulator 是精度关键；wiki-gfx906 实测 on-the-fly QDQ 若不复用反而慢（2.00 vs FP32 5.95 TOPS），摊销后 dot4 21.7 TOPS。故 B3 把量化放在 staging 并复用，R110 也先摊销 P 量化；均不替代本机数值门。
- **生产零变更**：引擎仍 `attn` / config `3dde8801`；本轮重启 0 / 停机 0 / 装机 0 / 回滚 0。quant_quality 技能的旧三臂设计稿未跑，不冒充实测。
""" 
assert title not in s
s = s.rstrip("\n") + "\n\n" + block + "\n"
dir_anchor = "| `回写 · W1045（2026-11-07 18:1x–18:5x）五问审计：移植面 / dot4 / dot8 / mmq / CI-CD` |"
pos = s.index(dir_anchor)
eol = s.index("\n", pos) + 1
dirrow = "| `回写 · W1046（2026-11-07 19:1x–19:3x）R103 后续方案入权威 + B3 候选 + k8v4 dot8 可行性（零停机）` | B2 死路径纠正；hc4 已建未装；R109/R110 预注册；dot8q≠dot8 | W1046 |\n"
s = s[:eol] + dirrow + s[eol:]
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

port = io.open(PORT, encoding="utf-8").read().rstrip("\n")
add = """

---

## W1046 执行更正与新增候选（2026-11-07；并入 W832 §0.1 的 R109/R110）

1. **B2 不再是独立待移植项**：`qsa_pattn.cu` 在 HIP 下不编译，gfx906 prompt 实际回退 `qsa_decode_attn_batch`；W1044 的 DP4A 已覆盖该数学。此前「B2 > B3、B2 还可再拿 2–4%」排序作废。
2. **B3 已进入实现**：`gfx906/hc-dp4a @ 179bd6b5` / `hc4`，默认 off；Q8_0 down 权重与 staging 量化的 int8 激活做 DP4A，原内核保留。ISA `v_dot4=720`，parity/bench 功能门过；激活量化导致 mixed rel-RMS 约 0.0009→0.0012，必须再过节拍内数值/任务/A-B 门，未装机。
3. **A1/A5 不再笼统排队**：A1 在 B3 后独立 bitwise + decode A/B；A5 受 `P425` 的死派发约束，未证明生产调用点前不投入。A2/A3 每个位单独测，A4 最后逐 TU。
4. **k8v4 dot8 = R110**：不是 `dot8q()`；首选 PV 的 `P(int4)×V(int4)` 8-cell 原型，QK 的 Q→int4 暂缓。原型先过误差与微基准，未过不接 OPT、不占生产窗口。
"""
io.open(PORT, "w", encoding="utf-8", newline="\n").write(port + add + "\n")

rec = io.open(RECIPE, encoding="utf-8-sig").read().splitlines()
assert not any(l.startswith("strata-0.1.57-hc4\t") for l in rec)
rec.append("\t".join([
    "strata-0.1.57-hc4", "df33d3a60eb4c8515b6f34e090af7e40", "43675416",
    "gfx906/hc-dp4a @ 179bd6b5", "b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5",
    "4c1004c49221b07c3b8108977e3d1991fc9f45cc",
    "build-masterp（/src=pr/k10, /llama.cpp=tmp/w1037/llama-master）",
    "W1046/R109 B3 候选，默认 off 的 STRATA_HC_DOWN_DP4A；gr_parity 0 failures、fused_gr ISA dot4=720/dot8=0。**未装机**，数值与停机 A/B 待做（P524）"
]))
io.open(RECIPE, "w", encoding="utf-8", newline="\n").write("\n".join(rec) + "\n")
print("plan, PORT_PLAN, recipe written")
