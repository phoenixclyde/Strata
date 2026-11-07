import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**424 条 / 已结 337 / 79.5%**（本轮 +37：`P445`–`P481`）"
new4 = "**426 条 / 已结 339 / 79.6%**（本轮 +39：`P445`–`P483`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**25. 把 decode 拆到底：draft 只占 5.1%，真正的大项是 **CPU 专家 11.7%**（`P482`/`P483`）**

开窗前先算上限，省一次停机。`STRATA_DECODE_TIMING` 一直在产，日志里 400 条 `strata decode timing:` 行就是现成的账（`albus/w1039/decode_timing.txt`）：

| 段 | 中位 ms/窗 | 占比 |
|---|---|---|
| **verify** | **35.89** | **90.3%** |
| ├ GPU-reach wait | 27.59 | 69.4% |
| ├ per-layer host | **5.43** | **13.6%** |
| └ stage | 0.09 | 0.2% |
| **draft** | **2.04** | **5.1%** |
| adapt wait / commit / other | 0.15 | 0.4% |
| 合计 | **39.76** | 1.00 tok/窗 |

host 那 5.43 ms 内部：plan 0.17 + actq 0.18 + jobs 0.04 + **CPU 4.64** ⇒ **CPU 占 host 的 86%、占整窗 11.7%**；而且它的分布是**双峰**：p10 = **0.00**、p50 = 4.66、p90 = **17.11 ms**——一部分请求根本不碰 CPU 专家，一部分被它吃掉 40% 以上的窗口。

**三条推论，一条一条落地：**

1. **草稿流优化的天花板只有 5.1%。** 照 R9700 的外证（draft 5.8→3.5 ms，−2.3 ms）折到 39.76 ms 的窗口是 5.8%，按比例（−40%）只有 2.1%。decode 的 2×CV 常年在 5–8% ⇒ **`STRATA_MTP_HIP_PRIO` 不单独开窗**（候选 `hipk` 留着搭车）。
2. **`STRATA_HIP_QUEUE_PRIME` 降级。** 拿 18 个 arm 文件、42 组「同 target 首个 vs 其余」：偏差中位 **+0.23%**、均值 +1.41%、p90 +5.54%，>0.5% 的只占 36% ⇒ **没有可重复的首请求惩罚**，右尾是噪声。边界要说清：这些数据前面都有 warm-up，**测不到「重启那一刻的队列落位」**，所以结论是「没有可重复的首 target 惩罚」，不是「落位一定不存在」。
3. **`R104` 多了一条判据，而且是decode 侧的。** CPU 专家是「缓存装不下的专家」驱动的（decode 命中率 96.8%，仍有 0.45–0.75 个专家/层窗口走 CPU）。加槽不只不加分项，它**直接把 11.7% 这一项往下压**——所以窗口里除了 prefill 与 tok/s，还要看 `decode timing` 里的 **CPU 段**。我已经把它加进窗口脚本：每个臂跑完 `grep "strata decode timing:" | tail -1`，两臂对比 `CPU 4.64 ms/窗` 这一列。

**一个必须自我限定的地方**：这 400 条的中位是 1.00 token/窗（含 128-token 生成），所以 39.76 ms/窗 ≠ 我们平时报的 57–62 tok/s 那一档（那档多为更长生成、窗口更满）。**用它算占比可以，用它算绝对吞吐不行。**
"""
r = r.rstrip() + "\n" + section + "\n"
r = r.replace("`patchA_hip_knobs.py` / `build_hipk.sh`。",
              "`patchA_hip_knobs.py` / `build_hipk.sh` / `decode_split.py` / `decode_timing.txt`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §25 added; §四 ->", new4)

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
block = """
---

### 回写 · W1039 §十六（decode 的账：draft 5.1%，CPU 专家 11.7%）

- **实测（400 窗，`STRATA_DECODE_TIMING` 日志）**：39.76 ms/窗 = verify **35.89（90.3%）** + draft **2.04（5.1%）** + adapt/commit/other 0.15；verify 内 GPU-reach 27.59（69.4%）、per-layer host 5.43（13.6%）。
- **host 内部**：plan 0.17 + actq 0.18 + jobs 0.04 + **CPU 4.64**（host 的 86%、整窗的 11.7%）；CPU 双峰 p10 0.00 / p50 4.66 / p90 17.11 ms。
- **判决**：`STRATA_MTP_HIP_PRIO` 天花板 5.1%（现实 2–6%）⇒ **不单独开窗**（`P483`）；`STRATA_HIP_QUEUE_PRIME` 无系统首请求惩罚（中位 +0.23%，`P483`），且 warm-up 会吸掉重启落位 ⇒ 降级。
- **对 `R104` 的意义**：CPU 专家由「缓存装不下的专家」驱动，**加槽直接压这一项** ⇒ `kvg` 窗口的次要判据 = `decode timing` 的 CPU 段（脚本已加每臂抓取）。decode 的「已到地板」只能在 GPU 段（69.4%）上说，不能在整窗上说。
"""
if not p.endswith("\n"):
    p += "\n"
p += block
L = p.splitlines()
d0 = next(i for i, l in enumerate(L) if l.startswith("### 6.5.0"))
d1 = next((i for i in range(d0 + 1, len(L)) if L[i].startswith("> **【AUDIT27 更正")), len(L))
last = max(i for i in range(d0, d1) if L[i].startswith("| 回写"))
row = ("| 回写 · W1039 §十六（decode 的账：draft 5.1%，CPU 专家 11.7%） | 400 窗拆完：verify 90.3%、draft 5.1%、"
       "host 里 CPU 占 86%（整窗 11.7%，p90 17.1 ms）⇒ MTP_PRIO 不单独开窗，R104 多一条 decode 判据 |")
L.insert(last + 1, row)
io.open(PL, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("plan: 回写 §十六 + directory row")

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / 401–483（13:4x）decode 拆账：draft 只 5.1%，CPU 专家 11.7%

- 400 条 `strata decode timing` 中位：39.76 ms/窗 = verify 35.89（90.3%，其中 GPU 27.59/69.4%、per-layer host 5.43/13.6%）+ draft 2.04（5.1%）。
- host 内部 plan 0.17 + actq 0.18 + jobs 0.04 + **CPU 4.64**（host 86%、整窗 11.7%）；CPU 双峰 p10 0 / p50 4.66 / p90 17.11 ms。
- **MTP_HIP_PRIO 天花板 5.1%，现实 2–6% ⇒ 不单独开窗**；**QUEUE_PRIME 无系统首请求惩罚**（42 组，中位 +0.23%，warm-up 会吸掉重启落位）⇒ 降级。
- **R104 多一条 decode 判据**：CPU 专家由「装不下的专家」驱动，加槽直接压它；窗口脚本已加每臂抓 `decode timing`。
- 口径限定：这批样本 1.00 token/窗，只能算占比，不能算绝对吞吐。
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
