import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

# ---------- 1. PROGRESS：R87 判否 + 新候选 R96 ----------
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out = []
for l in lines:
    c = l.split("\t")
    if len(c) > 8 and c[1] == "R87":
        c[6] = "1"
        c[7] = "DONE_NEG"
        c[8] = (c[8] or "") + (
            " 【W995 判否 %s】**本机已实现激活复用**：`prefill.cpp:5010` 注释逐字 "
            "「the layer's activations as q8_1 rows in expert order ... **each token quantized once** and written to its K rows」"
            "（`mmq::quantize_scatter`）。实测 `STRATA_PREFILL_TIMING`：量化所在的 **gather 相位仅 0.2–0.7%%** "
            "（2K：9–24 ms / 3668 ms；16K：64 ms / 19543 ms），低于 R87 自定的「<1%% 则不做」判据。"
            "**外证**：llama.cpp 同样是每 chunk 量化一次、整层复用，量化开销在长 prompt 上是舍入误差；"
            "另有一份完整 Q8_1+dp4a 移植实测 **<1%%、在噪声内**（瓶颈是权重带宽非激活）。⇒ 不做。" % TS)
        l = "\t".join(c)
    out.append(l)

rows = [
    "\t".join(["B5本机缺口", "R96", "MoE gate/up + GLU 融合成一次 mul_mat_q（llama.cpp PR #31188）", "W995", "count", "1", "0",
               "OPEN", "**W995 立（%s，外网核对）**：上游 2026-10-30 合并 #31188，把 gate、up 两次 matmul 与 GLU 门控并进一次 "
               "mul_mat_q 启动，减少中间搬运与 launch。宣称「prefill 最高 +17.2%%」但**原文明确说没有对照数据、不能归因**；CUDA-only，"
               "我们是 HIP/gfx906。与 R95 的主战场（gate/up 占 20.6%%）对得上 ⇒ 值得先做源码可行性判断，再谈移植。"
               "判据：单内核 A/B ≥10%% 才动生产。" % TS]),
    "\t".join(["B7配置旋钮", "P272", "`STRATA_PREFILL_TIMING` 的 gather 相位占比（R87 判据数据）", "W995", "count", "1", "1", "DONE",
               "**W995（%s）**：2K 9–24 ms / 3668 ms（0.2–0.7%%）、16K 64 ms / 19543 ms（0.3%%）⇒ 量化总开销 <1%%。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out + rows) + "\n")
print("PROGRESS: R87→DONE_NEG, +R96/P272")

# ---------- 2. AUDIT_INDEX：回写过时结论 ----------
A = "D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md"
s = io.open(A, encoding="utf-8").read()
old = "| **`build.ninja` 不可重生成** | W863-3 | **OPEN**：`add_subdirectory(\"/llama.cpp/ggml\")` 缺挂载 + 一个 glob 不符 ⇒ `ninja` 直接不可用；重编只能取 `ninja -t commands` 的三条命令 |"
new = ("| ~~`build.ninja` 不可重生成~~ | W863-3 → **W994 更正** | **已推翻**：挂对 `/ref=llama_b12110`(ggml 0.29) + 透传 "
       "`--device=/dev/kfd --device=/dev/dri` 后，容器内 `cmake -S /src -B /out -G Ninja` 与 `ninja -j4 strata` 全通（RC=0），"
       "产物 md5 与生产逐字节相同。**保留的规矩**：单 TU 改动仍走 `ci/build.sh` 的三条逐字命令；全量重建必须以 md5 复现生产为验收门 |")
if old in s:
    s = s.replace(old, new, 1)
    io.open(A, "w", encoding="utf-8", newline="").write(s)
    print("AUDIT_INDEX: 过时行已回写")
else:
    print("AUDIT_INDEX: 锚点未找到（需手工核对）")
