import io
import re

P = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
PORT = "albus/gfx906_survey/PORT_PLAN.md"

lines = io.open(P, encoding="utf-8").read().splitlines()
n = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "R110":
        f[2] = "k8v4 的 V 侧 dot8 原型：P*Vscale 按 8-cell 组量化 int4，Q4_0 V 的 nibble 减 8 打包 signed int4，做 P(int4)×V(int4)；不是 dot8q，也不是 R91 的 Q4_K MMQ"
        f[8] += " **W1046 原型实测 + 规格纠错**：ROCm/LLVM 明确 `v_dot8_i32_i4 = i4x8 × i4x8`，不是 int4×int8；初版 P(int8) 打包移位越界，结果全部作废。修正后 CPU/GPU 逐点一致；预打包上限 6.511→4.391 µs（1.483×），但合成 rel_rms=6.23%、max_abs=0.1004，且不含量化/打包 ⇒ 只支持继续做真实模型数值门，不支持装机。QK 的 K 是 int8，不能直接走 dot8，除非 K 也降 4-bit。"
        f[10] = "KW:k8v4|P(int4)|V(int4)|dot8q"
        lines[i] = "\t".join(f); n += 1
assert n == 1
row = ["B6判定探针", "P525",
       "k8v4 PV-dot8 首个有效原型：CPU/GPU 对齐，预打包性能上限 1.483×，合成 rel-rms 6.23%；只过可行性，不过质量门",
       "W1046", "count", "1", "1", "DONE",
       "**实测**：`k8v4_pv_dot8_proto.cu`，生产 Q4_0 V 布局，P*Vscale 按 head×8-cell×32-dim block 量化 signed int4；CPU 与 GPU dot8 对照一致（样例 -0.11233953→-0.11295335 两侧相同）。2000 reps：ref 6.511 µs、dot8 4.391 µs、**1.483×**；rel_rms **0.0622626**、max_abs 0.100429。**边界**：P 量化/打包在计时外，是上限；合成数据不是模型 KL；不能装。**规格纠错**：ROCm/LLVM `v_dot8_i32_i4` 两个操作数都是 i4x8；此前 P(int8) 的说法与初版数据作废。",
       "R110;P501", "KW:1.483|0.0622626|i4x8"]
assert len(row) == 11 and all("\t" not in x for x in row)
assert not any(l.split("\t")[1] == "P525" for l in lines if l.count("\t") >= 9)
for kw in row[10].replace("KW:", "").split("|"):
    assert kw in " ".join(row), kw
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

tot = done = 0
for l in lines:
    f = l.split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try: tot += int(f[5]); done += int(f[6])
        except ValueError: pass
pct = 100.0 * done / tot
print("TOTALS", tot, done, round(pct, 1))

s = io.open(PLAN, encoding="utf-8").read()
s = s.replace("P(int8)×V(int4)", "P(int4)×V(int4)")
s = s.replace("P 按 8-cell 组量化 int8", "P 按 8-cell 组量化 int4")
s, n = re.subn(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1046；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1046；" % (tot, done, pct), s, count=1)
assert n == 1
anchor = "- **生产零变更**：引擎仍 `attn` / config `3dde8801`；本轮重启 0 / 停机 0 / 装机 0 / 回滚 0。quant_quality 技能的旧三臂设计稿未跑，不冒充实测。"
add = ("- **R110 原型已有数据（`P525`）**：先纠正规格，`v_dot8_i32_i4` 是 **i4x8×i4x8**；初版 P(int8) 的结果作废。修正后 CPU/GPU 对齐，预打包 PV 上限 **1.483×**（6.511→4.391 µs），但合成 rel-rms **6.23%** 且量化/打包未计时 ⇒ 继续真实模型数值门，不接生产。k8v4 的 QK 不能直接用 dot8（K 是 int8）。\n"
       + anchor)
assert s.count(anchor) == 1
s = s.replace(anchor, add, 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

p = io.open(PORT, encoding="utf-8").read()
p = p.replace("P(int8)×V(int4)", "P(int4)×V(int4)")
p = p.replace("P 按 8-cell 组量化 int8", "P 按 8-cell 组量化 int4")
p += "\n**W1046/P525 原型**：ROCm/LLVM 规格为 i4x8×i4x8；CPU/GPU 对齐，预打包 1.483×，合成 rel-rms 6.23%。仅证明可行性与上限，未过模型质量门。\n"
io.open(PORT, "w", encoding="utf-8", newline="\n").write(p)
print("prototype verdict landed")
