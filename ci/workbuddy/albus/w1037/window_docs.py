import io, os, shutil

# ---------------- ledger ----------------
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_w1037e")
s = io.open(P, encoding="utf-8").read()

r1 = "\t".join([
    "B4上游移植", "P434",
    "窗口三臂实测：pa1 的 ATTN_DP4A 与 DPP/LDS/ROUTE 整包对预填**零效果**（8K −0.10%/−0.02%，2×CV 0.20%/0.00%）",
    "W1037", "count", "1", "1", "DONE_NEG",
    "**W1037 实测（机主 07:21 批准，三次重启，停机合计 136 s）**：ctl = 在产 `-001`（不重启）/ b = pa1 + `ATTN_DP4A=1` / "
    "c = pa1 + `ATTN_DP4A+ATTN_DPP+ATTN_LDS_PAD+ROUTE_DPP`。每臂 2.5K×3 + 8K×2 + decode×3。"
    "**2.5K**：5372.7 / 5480.7（+2.01%）/ 5486.3（+2.11%），2×CV 5.60% / 6.40% ⇒ 不显著；"
    "**8K**：13578.0 / 13564.5（**−0.10%**）/ 13575.0（**−0.02%**），2×CV 0.20% / 0.00% ⇒ **落在噪声地板上**；"
    "**`qsa attn` 相位几乎逐毫秒相同**（578.3 / 577.3 / 576.7；2237.5 / 2241.0 / 2238.0）；"
    "decode 57.6 / 59.7 / 56.8 tok/s（CV 14.3/11.9/14.2）⇒ 噪声。安全：3 次重启 47+42+47 s，"
    "还原后 config md5 `53ac61e0…`、engines=1、`/health` ok。",
    "P425", "KW:零效果|qsa attn"])

r2 = "\t".join([
    "B4上游移植", "P435",
    "更正 B1/B2 的落点：它们改的 attn_chunk_kernel 预填根本不走——预填吃的是 qsa_prompt_attn_batch（fp32 fmaf）",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（`P434` 的零效果不是「ALU 不是瓶颈」，是打错靶）**：`prefill.cpp:4398-4426` 的派发顺序是 "
    "① `qsa_prompt_attn_batch_gated` → ② `qsa_prompt_attn_batch` → ③ `qsa_pattn_batch`（`pattn_mode()!=0`）→ "
    "④ **最后才是** 循环调 `qsa_decode_attn_batch`（源码注释：\"the decode kernel, 32 queries at a time\"）。"
    "我们的 DP4A/DPP/LDS 开关只改 ④ 的 `attn_chunk_kernel` ⇒ **预填走 ①/②，改动不在热路径上**；"
    "`qsa attn` 相位逐毫秒不变（578.3→577.3 / 2237.5→2241.0）正是这个的直接证据。"
    "**新落点**：`qsa_prompt_attn.cu` 的 fp32 `fmaf` 累加（`:353`/`:471`/`:725`/`:776`，该文件 2504 行、全无 dp4a）；"
    "分母 = `qsa attn` 占预填 **10.7%（3.4K）→ 16.5%（10.8K）**。"
    "⇒ `PORT_PLAN §4` 里「B2 真实落点=qsa_decode_attn.cu，非 qsa_pattn」这句**作废**（当时只核了 qsa_pattn 在 HIP 下的编译条件，"
    "没有核 prefill.cpp 的派发顺序）。",
    "P434", "KW:打错靶|qsa_prompt_attn"])

out = s.rstrip("\n") + "\n" + r1 + "\n" + r2 + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +2")

# ---------------- W832 ----------------
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_w1037e")
s2 = io.open(P2, encoding="utf-8").read()
a = "**375 条 / 已结 292 / 77.9%**（W1037 校正"
b = "**377 条 / 已结 294 / 77.9%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)

ADD = """
**十二、窗口已跑（机主 07:21 批准）：三臂**零效果**，但原因不是「ALU 不是瓶颈」，是**打错靶**（`P434` / `P435`）。

| 臂 | 二进制 | 开关 | 2.5K gpu | 8K gpu | 2.5K `qsa attn` | 8K `qsa attn` | decode |
|---|---|---|---|---|---|---|---|
| ctl | `-001`（不重启） | 无 | 5372.7 ms | 13578.0 ms | 578.3 | 2237.5 | 57.6 tok/s |
| b | `pa1` | `ATTN_DP4A` | 5480.7（**+2.01%**） | 13564.5（**−0.10%**） | 577.3 | 2241.0 | 59.7 |
| c | `pa1` | `+DPP +LDS_PAD +ROUTE_DPP` | 5486.3（**+2.11%**） | 13575.0（**−0.02%**） | 576.7 | 2238.0 | 56.8 |

判据是**当次 2×CV**：2.5K 为 5.60% / 6.40%（+2% 不显著，且首条请求是冷启动），8K 为 **0.20% / 0.00%** ⇒ 8K 的两臂差异
**落在噪声地板上**。停机合计 **136 s**（三次重启 47 + 42 + 47），还原后 `config md5 53ac61e0…`、engines=1、`/health` ok。

**关键在于相位不变**：`qsa attn` 从 578.3 → 577.3 / 2237.5 → 2241.0，**逐毫秒相同**。如果改的代码真在跑，
哪怕相位是访存受限，也不可能一丝不动。查 `prefill.cpp:4398-4426` 的派发顺序：

1. `qsa_prompt_attn_batch_gated`（融合门）
2. `qsa_prompt_attn_batch`
3. `qsa_pattn_batch`（`pattn_mode()!=0`）
4. **最后才是** 循环调 `qsa_decode_attn_batch` —— 源码注释写着 "the decode kernel, 32 queries at a time"

我们的 DP4A / DPP / LDS 开关**只改第 4 条的 `attn_chunk_kernel`**。预填实际走 1/2 ⇒ **改动根本不在热路径上**。
⇒ `PORT_PLAN §4` 里那句「B2 真实落点=`qsa_decode_attn.cu`，非 `qsa_pattn`」**作废**：当时只核了 `qsa_pattn` 在 HIP 下的编译条件，
没核 `prefill.cpp` 的派发顺序。

**真正的 B2 落点是 `qsa_prompt_attn.cu`**：2504 行、全文件 **0 处 dp4a**，分数与 V 累加是 fp32 `fmaf`
（`:353` `fmaf(tg[0], s0, sc[0])`、`:471-474` `acc[j][k]=fmaf(acc[j][k], a, tmp*vdown)`、`:725`/`:776` 同构）。
分母 = `qsa attn` 占预填 **10.7%（3.4K）→ 16.5%（10.8K）**。这是下一个该改的文件，且**必须先确认它走 gated 还是 plain**。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十二")

# ---------------- reply ----------------
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**375 条 / 已结 292 / 77.9%**（W1037 校正；本轮 +9：`P425`–`P433`）。"
b3 = "**377 条 / 已结 294 / 77.9%**（W1037 校正；本轮 +11：`P425`–`P435`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**13. 窗口已跑：三臂零效果，但原因是打错靶（`P434` / `P435`）。**

| 臂 | 2.5K gpu | 8K gpu | 2.5K `qsa attn` | 8K `qsa attn` | decode |
|---|---|---|---|---|---|
| ctl（`-001`，不重启） | 5372.7 ms | 13578.0 ms | 578.3 | 2237.5 | 57.6 tok/s |
| b（`ATTN_DP4A`） | 5480.7（+2.01%） | 13564.5（**−0.10%**） | 577.3 | 2241.0 | 59.7 |
| c（`+DPP +LDS_PAD +ROUTE_DPP`） | 5486.3（+2.11%） | 13575.0（**−0.02%**） | 576.7 | 2238.0 | 56.8 |

判据用当次 2×CV：2.5K 是 5.60%/6.40%（不显著，且首条是冷启动），8K 是 **0.20%/0.00%** ⇒ 8K 两臂差异在噪声地板上。
停机合计 **136 s**（三次重启 47/42/47），还原后 config md5 `53ac61e0…`、engines=1、`/health` ok。

**相位不动才是关键证据**：`qsa attn` 578.3 → 577.3、2237.5 → 2241.0，逐毫秒相同。改的代码若真在跑，
哪怕相位是访存受限也不会一丝不动。查 `prefill.cpp` 派发顺序：① `qsa_prompt_attn_batch_gated` → ② `qsa_prompt_attn_batch`
→ ③ `qsa_pattn_batch` → ④ 最后才循环调 `qsa_decode_attn_batch`（源码注释 "the decode kernel, 32 queries at a time"）。
**我们的开关只改第 ④ 条的 `attn_chunk_kernel`，而预填走 ①/②** ⇒ 改动不在热路径上。

⇒ `PORT_PLAN §4` 的「B2 真实落点 = `qsa_decode_attn.cu`，非 `qsa_pattn`」**作废**（当时只核了 `qsa_pattn` 在 HIP 下的编译条件，
没核 `prefill.cpp` 的派发顺序）。**真落点是 `qsa_prompt_attn.cu`**：2504 行、0 处 dp4a，分数与 V 累加是 fp32 `fmaf`
（`:353`/`:471-474`/`:725`/`:776`），分母 10.7%→16.5%。
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +13")
