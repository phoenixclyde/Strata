import io, re

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
REG = "deploy/params/PARAM_REGISTER.tsv"

BLOCK = '''
### 回写 · W1013（R21 被自己的开关挡住；5% 单条门改成组合门）

**1. R21 判负，理由在源码里，不在测量里。** `STRATA_GR_V3=1`（hyper-connection read 的流拆分版）挂了五轮，
本轮开工前先读它的生效条件：

- `fused_gr.cu:2899` — `split = v3 && s_down == nullptr && s_up == nullptr ? split3[dev] : -1;`
- `fused_gr.cu:2903` 注释逐字 — *"it declines Q8 weights (s_down set)"*；`:2953` — *"its K-split down reads
  bf16 rows (not STRATA_HC_REQ8)"*。
- `arch_defaults.cpp:221` — gfx906 的 tuned 集合里写死 `STRATA_HC_Q8=1`（KL 0.0011、argmax 100%），
  于是 `s_down != nullptr` 恒成立 ⇒ **v3 在我们的生产配置里永不启用**。

实测与源码一致（`cfg_apply` 冷 prompt，n=6/3，band 0.78/1.06/0.08%）：

| 臂 | prefill@2000 | @8000 | @16000 | decode |
|---|---|---|---|---|
| 基线 `w1013-base` | 513.65 tok/s | 684.62 | 767.22 | 35.82 |
| `STRATA_GR_V3=1` | 513.66 (**+0.08%**) | 684.99 (**+0.05%**) | 766.63 (**−0.08%**) | 34.40（band 13.98%） |

三个长度全在带内 ⇒ 不是"v3 没用"，是**那段代码没跑**。⇒ **R21 = DONE_NEG**；真要拿它的并行度，得先给
Q8 码写一个 int8 版 v3（`s_down` 路径），那是 R86 同类的移植，不是开关。

**2. 一次事故，和它暴露的门缺陷。** A/B 走 `ci/cfg_apply.py`（配置改动的唯一合法通道）。它在**装完候选、重启完、
测完之后**崩在判决算术：

```
UnboundLocalError: cannot access local variable 'better' where it is not associated with a value
```

`better` 只在"某个长度越过 2×CV"的分支里赋值，于是**任何没有明显收益的 A/B（也就是绝大多数）都会崩**，
而崩点在回滚之前 ⇒ **候选配置留在线上、没有记录、没有回滚**。本轮就是这样把 `GR_V3=1` 留在了生产上，
发现后用 `cp .bak_235103` 恢复，config md5 回到 `e62685e6ff21d9e2b60c1cd622fd5a67`（逐字节）。

为什么会漏看：我把命令接进了 `| tail -26`，管道的退出码是 `tail` 的（记忆里早有这一条，这次是我自己犯）。

修复（不是补一行）：

- 判决算术抽成纯函数 `compare_arms(base, dec, tt, extra)`，符号按 `prefill_at()` 的量纲（**prompt tok/s，越高越好**）。
- 装完之后整段包 `try/except BaseException`：任何异常 → `cp bak` → 重启 → 写 `*.crash` 记录 → **exit 4**，不再下落。
- `ci/test_cfg_verdict.py` 7 例，含 23:52 那次崩溃形态（`--lengths` 给了、但没有一条越过 band）与"完全没给 --lengths"，
  另含符号反向（把 2% 的 prompt 收益记成回退）。已接进 `round_gate --ci`（输出 `SELF_TEST: 7/7`）。

**3. 5% 门：单条已无可捡，改成组合门。** 这是本轮真正的结论，也是它该进方案的原因——**队列不是被物理堵住的，
是被一条判据堵住的**。逐条实测/推算（`ci/bundle_budget/BUNDLE.tsv`，份额由 `PREFILL_PHASES.tsv` 反算）：

| 条目 | 相位（2K） | 相位 delta | 折算到整条 prefill | 依据 |
|---|---|---:|---:|---|
| `R86-dn` down-only 权重 repack | gemm down 510 ms | −20% | **−3.20%** | bench（`WIDTH_SWEEP.tsv`） |
| `R95-plan` 建组计划挪 issuer | host grouping 91 ms | −100% | −2.85% | estimate |
| `R21-v3hc` v3 的 int8 版 | hc read: down+silu 117 ms | −40% | −1.47% | estimate |
| `GDN-chunk` 分块递推 | gdn recurrence 121 ms | −50% | −1.90% | estimate |
| `R98-wc` 预取深度 | wait copy 37 ms | −50% | **−0.58%** | estimate |

**没有一条单独过 −5%**；**五条合起来 −9.99%**。所以判据改成：

> 一个 **bundle** 可以按**它的和**采纳（2K prefill ≤ −5%）；其中每一条仍须各自越过 **2×CV**；
> 任何改舍入的条目由**一份**质量门（`Q:` 行）覆盖整包；`estimate` 只占队列位置，**永不计入和**。

`ci/bundle_budget/bundle.py` 把这套算术做成门：`phase_ms_2k` 必须等于 `PREFILL_PHASES.tsv` 的 2K 簇中位数（±2%，
**份额不许手打**）、`bench` 条目的 delta 必须越过 2×CV、`ADOPT` 的和不够 −5% 直接 FAIL、证据件必须存在、
改舍入的 `ADOPT` 必须有 `Q:` 行。负向 4/4 另加自测 6/6；`round_gate --ci` 输出 `BUNDLE: PASS (budget 0.00/5.0%)`。

当前预算 **0.00/5.0** —— 一条都还没采纳，这是实话；离门还差 5 个点，而桌上的全部候选值 9.99 个点。

**4. 外网核了 GDN 分块（这是"举一反三"里最该核的一条）**：分块/WY 形式的收益是真的，但**每一个公开实现都骑在矩阵核上**——

- ONNX Runtime `#32182`：chunked（WY/UT）prefill，Qwen3.8-27B 几何下 **4.5×**（T=1024），实现只用 `mma.sync.m16n8k16`（sm_80+ PTX）。
- FlashQLA（Qwen 官方）：对 FLA Triton 前向 **2–3×**，TileLang + warp specialization，Hopper。
- 同一份实现里的约束：chunk 64×64 需 **157 KB** SMEM、32×64 需 **96 KB**；gfx906 的 LDS 是 **64 KB** ⇒ chunk 只能更小，
  而 gfx906 **没有矩阵核**（只有 `v_dot*`）⇒ 收益得用 FMA 重算，不能照抄倍数。

⇒ `GDN-chunk` 保持 **BLOCKED**，复谈条件写死：**有人写出 C≤16、≤64 KB LDS 的 FMA 分块内核**，且相位实测 ≥2×CV。
`R98` 同时关：37 ms 的相位就算砍半也只有 −0.58%，低于我们任何一道门的噪声底。
'''

s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1013" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

# §0.1: the adoption rule is now a bundle rule, and the queue loses R98
s = io.open(PLAN, encoding="utf-8").read()
old_q = "| **唯一队列** | **R95（外围/host 侧）→ R94 → R91 → R89 → R46 → R49 → R50 → R98** | 本节 + `§6.5` 各回写块 |"
new_q = ("| **唯一队列** | **R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50**（`R21`/`R98` 已于 W1013 关闭） | 本节 + `§6.5` 各回写块 |\n"
         "| **采纳判据（prefill）** | **组合门**：一个 bundle 的和 ≤ −5%（2K）即采纳；每条各自 ≥2×CV；改舍入的条目一份 `Q:` 质量门覆盖整包；`estimate` 不计入和 | "
         "`ci/bundle_budget/bundle.py --check`（份额由 `PREFILL_PHASES.tsv` 反算，负向 4/4） |")
assert old_q in s, "0.1 queue row not found"
s = s.replace(old_q, new_q, 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

# PROGRESS: four new rows + two status flips
ROWS = [
 ("B6判定探针", "P321", "R21 判负：`STRATA_GR_V3=1` 在 HC_Q8=1 下永不启用（源码 + A/B 双证）", "W1013", "DONE_NEG",
  "**W1013 立**：`fused_gr.cu:2899` 的 `split` 要求 `s_down==nullptr && s_up==nullptr`，`:2903`/`:2953` 注释逐字「declines Q8 weights」「reads bf16 rows (not STRATA_HC_REQ8)」；"
  "而 `arch_defaults.cpp:221` 的 gfx906 tuned 集合写死 `STRATA_HC_Q8=1` ⇒ v3 永不启用。A/B（`cfg_apply`，n=6/3）：prefill@2000 +0.08%、@8000 +0.05%、@16000 −0.08%，三档全在带内。",
  "ci/state/cfg/w1013-v3.json"),
 ("B8工程", "P322", "`cfg_apply` 装完候选后崩在 `better` 未绑定：配置留在线上、无记录无回滚（已修 + 7 例）", "W1013", "DONE",
  "**W1013 立**：23:52 的 GR_V3 A/B 在测完之后抛 `UnboundLocalError: better`，崩点在回滚之前 ⇒ 候选留在生产（config md5 变 `6626996e…`）。恢复 `cp .bak_235103` ⇒ `e62685e6…` 逐字节。"
  "修复：判决算术抽成纯函数 `compare_arms()`（符号按 prompt tok/s）、装完整段 `try/except` 自动回滚并写 `.crash`、`ci/test_cfg_verdict.py` 7 例（含崩溃形态）接进 `round_gate --ci`（`SELF_TEST: 7/7`）。"
  "另：本轮把命令接进 `| tail` 导致崩溃被管道吞掉——记忆里已有的 `PIPESTATUS` 纪律，这次是我自己犯。",
  "ci/cfg_apply.py"),
 ("B8工程", "P323", "5% 单条门 → 组合门：`ci/bundle_budget`（当前预算 0.00/5.0，全部候选 −9.99%）", "W1013", "DONE",
  "**W1013 立**：五条候选逐条都不足 −5%（R86-dn −3.20 / R95-plan −2.85 / R21-v3hc −1.47 / GDN-chunk −1.90 / R98-wc −0.58），合起来 −9.99% ⇒ 判据改为「bundle 按和 ≤−5%，每条的相位 delta 仍须 ≥2×CV，"
  "改舍入的条目一份 `Q:` 覆盖整包，estimate 不计入和」。门校验：份额由 `PREFILL_PHASES.tsv` 反算、bench delta 必须越 2×CV、ADOPT 和不足即 FAIL、证据件必须存在；负向 4/4 + 自测 6/6。",
  "ci/bundle_budget/bundle.py"),
 ("B4上游移植", "P324", "外网核 GDN 分块：4.5×/2–3× 全部骑矩阵核，gfx906 只能 C≤16 FMA", "W1013", "DONE_NEG",
  "**W1013 立**：ONNX Runtime `#32182` chunked WY prefill Qwen3.8-27B **4.5×**（T=1024，只用 `mma.sync.m16n8k16`，sm_80+）；FlashQLA 对 FLA Triton **2–3×**（TileLang/Hopper）。"
  "同一实现的 SMEM 约束：chunk 64×64 需 157 KB、32×64 需 96 KB，gfx906 的 LDS **64 KB** 且**无矩阵核** ⇒ 收益得用 FMA 重算。复谈条件：有人写出 C≤16、≤64 KB 的 FMA 分块内核且相位 ≥2×CV。",
  "ci/bundle_budget/BUNDLE.tsv"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
ST = head.index("status")
NOTE = head.index("note")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]

# R21 -> DONE_NEG, R98 -> DONE_NEG (status flip + a note on why)
flips = {"R21": "**W1013 判负**：`HC_Q8=1`（tuned 集）使 `s_down != nullptr`，v3 的 `split` 恒为 −1 ⇒ 开关无效；A/B 三档全在带内（prefill@2000 +0.08%）。",
         "R98": "**W1013 关**：wait copy 2K 只剩 37 ms，砍半 = −0.58%，低于任何门的噪声底（2×CV ≥ 1.2%）⇒ 不值得动。"}
for i, l in enumerate(lines):
    if l.count("\t") < 9 or l.startswith("#"):
        continue
    c = l.split("\t")
    if c[ID] in flips:
        c[ST] = "DONE_NEG"
        c[NOTE] = flips[c[ID]] + " " + c[NOTE]
        lines[i] = "\t".join(c)

if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

# PARAM_REGISTER: P244 GR_V3 CANDIDATE -> REJECTED
r = io.open(REG, encoding="utf-8").read().split("\n")
n = 0
for i, l in enumerate(r):
    if l.startswith("P244\t"):
        c = l.split("\t")
        if len(c) > 5 and c[5] == "CANDIDATE":
            c[5] = "REJECTED"
            c[-1] = c[-1] + " **W1013 判负：HC_Q8=1 使 v3 的 split 恒 −1（`fused_gr.cu:2899`），A/B 三档全在带内。**"
            r[i] = "\t".join(c)
            n += 1
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(r))
print("plan block + %d rows + %d flips + register %d" % (len(add), len(flips), n))
