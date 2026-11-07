# W918 · 上游 708 条逐条读后的结论：生产不用改，方案要加三条（两条可零冲突落地）

> **【AUDIT24 P2 · 2026-11-04】§69 的冲突判断已被 `W921` 推翻**：`3cc47f02` 的「需手解 1 处冲突」
> 来自**提交顺序**（先上了别的补丁），先上前置提交后 5 个 hunk **全部干净应用**。R66 的最终判定以 `W921` 的 A/B 为准。

> 2026-11-03 22:2x。零停服（只读 git + 在 `/tmp/w920` 建了临时 worktree 做 cherry-pick 试算，已可丢弃）。
> 对象：`upstream/main = ffa80d73`（2026-11-02，tag `v0.2.10`）相对我们 `d963c791`（`mi50-0.2.9-r27`）的 **708 条**。

---

## 0 三句话结论

1. **生产参数不需要因为上游而改**：708 条里**没有一条动 gfx906 的默认值**——`arch_defaults.cpp` 的 11 条改动全部是
   gfx12 / gfx1151 / gfx1010 / gfx1030。我们的 `STRATA_GFX906_TUNED` 表是自己加的，上游同文件改的是别的架构。
2. **调优方案要加三条**：上游 0.2.10 里有三个 **opt-in 且 bitwise** 的 prefill 开关，正好打在我们的痛点（MMQ 缓冲、HC 读、专家流），
   且**两个可以零冲突 cherry-pick 到我们分支**（实测）。
3. **顺带发现上游已经做了我昨天提的"路径断言"**：`af6ba4c6 Dispatch counters: which kernel path a run really took`。

---

## 1 冲突面（先算这个，才知道 708 条里真正要碰的有多少）

我们 37 条领先改了 **42 个文件**；其中被上游也动过的只有 **10 个**：

| 上游改动数 | 文件 |
|---|---|
| 99 | `src/program/generate.cpp` |
| 49 | `CMakeLists.txt` |
| 22 | `src/kernels/cuda/fused_gr.cu` |
| 17 | `src/core/arch_defaults_test.cpp` |
| 11 | `src/core/arch_defaults.cpp` |
| 5 | `include/strata/core/arch_defaults.hpp` |
| 4 | `src/kernels/cuda/native_mmvq.cu` |
| 3 | `src/kernels/cuda/qsa_select.cu` |
| 1 | `serve/web/app.js`、`serve/telemetry.py` |

⇒ "708 条"听起来吓人，**真正的语义冲突面只有 10 个文件**，其余 32 个文件上游根本没碰。

---

## 2 `arch_defaults.cpp` 的 11 条逐条读：没有一条是 gfx906

| 提交 | 内容 | 与我们 |
|---|---|---|
| `95597c2d` | Windows gfx1151 用 helper 线程发起 verify 图（修 Q4_K_XL 首窗卡住） | 无关（Windows/gfx1151） |
| `e5354698` | gfx12：matrix-core QSA scorer 的启动行在 `STRATA_SELECT_WMMA=0` 时不打印 | 无关 |
| `c24a6836` / `c31f1fa3` | gfx12：>28,672 token 默认开 matrix-core QSA scorer | 无关（gfx906 无 WMMA） |
| `9d642d1f` / `1b282571` | gfx12 的 share limit、`mmvf_fast` 合并 | 无关 |
| `82eaeb42` | gfx12：`STRATA_HEAD_MIX_MULTI=1` 默认开 | 无关 |
| `3eb91676` | gfx1010 SDWA dot4 + 两张 gfx1030 rocBLAS 表 | 无关（RDNA1/2） |
| `d2068bde` | **gfx12 单卡** CPU prefill share 默认开（R9700 +18.3%/+30.6%） | 口径参考；gfx906 仍默认关 |
| `09982fff` | gfx12 decode 表三项 | 无关 |
| `8becec7d` | gfx1151 Windows 并行请求默认 | 无关 |

**⇒ 我们的 args/env 一个都不用改。** 唯一值得记的是 `d2068bde` 的度量方式（500/1K/2K/8K 四档 + KL 0.022 + top-1 29/29），
可以当作我们评估 CPU share 的模板；它明确写了 "gfx11、其他 AMD 家族、多卡 AMD 保持关闭直到测过"，**gfx906 属于"其他"**。

---

## 3 三个可直接用的 opt-in（预填阶段，全是 bitwise）

| 提交 | 开关 | 做什么 | 我们能不能吃 |
|---|---|---|---|
| `fbf6e1c7` | `STRATA_PF_GROUP_SCRATCH=1` | **MMQ 路径的 GU / H / Hq 只保留一个专家组的行**（减小 scratch，改缓冲布局） | **能**：我们的专家正是 MMQ（Q4_K/Q5_1），且该提交的条件是"每层都走 MMQ、无 fused 专家/FP16 回退" |
| `3cc47f02` | `STRATA_PF_HC_REGION=1` | 超连接读的 scratch（xn16/lo/lo16/gated）放进共享区 | **能**：我们 `HC_Q8=1`，HC 是常走路径 |
| `5273fb66` | `STRATA_PREFILL_ROUTED_STREAM=1` | 流式 prompt walk **不再拷贝"本 chunk 没有任何 token 路由到"的专家**，可调预取深度（默认 16） | **能且对症**：我们的 prompt 正是 `--pcie-frac 0.20` 从主机流式拉专家 |

**cherry-pick 实测**（`/tmp/w920`，detached at `d963c791`）：

```
fbf6e1c7  rc=0  conflicts=0     ← 零冲突
3cc47f02  rc=1  conflicts=1     ← 一处冲突（它按 fbf6e1c7 的 bounds_ints 改 bytes_needed，必须先上 fbf6e1c7）
5273fb66  rc=0  conflicts=0     ← 零冲突（新增 routed_stream.hpp + prefill.cpp + 测试，665 行）
```

⇒ **两个零冲突、一个按顺序手解一处**。三条都不改数值（bitwise），所以不需要过 KL 门，只需要过性能门（2×CV）。

---

## 4 kernels 77 条里另外三条值得记的

| 提交 | 内容 | 判断 |
|---|---|---|
| `686c0d42` / `4ab81c79` / `7d4feb2e` | **HC read v3 的 up/down 改成 register-blocked dot**（`STRATA_GR_V3_PF` bit6/7/8，T=5 时 down 两行一波） | **想吃但要付冲突代价**：都在 `fused_gr.cu`，而这个文件上游改了 22 次、我们也改过 → 冲突面最大 |
| `2970fe74` | QSA prompt attention（**matrix-core 内核**）减少 LDS + 预读下一 chunk 的 ids，"same output bits" | gfx906 没有 matrix-core（WMMA/MFMA），**用不上** |
| `5c55046d` | **移除 dense_tc**：Q6_K 的 INT8 tensor-core 投影比引擎 MMVQ 慢 1.4–2.3×（T 1–4） | **反向印证**我们的 MMVQ 方向；也提醒：别在 gfx906 上幻想矩阵核 |
| `af6ba4c6` | **Dispatch counters：一次运行到底走了哪条内核路径**（dense MMVQ 按类型/形状/行数、专家 group、gate/up 形态） | **正是我昨天提的"路径断言"**，上游已实现 → 以后做实验直接用它，不必自己埋点 |

---

## 5 对"生产"和"方案"的实际影响

### 生产：**不改**

- 参数/env 与上游零冲突（§2）；
- 上游没有 gfx906 的性能修复或回归，我们 0.2.9 的行为在 0.2.10 下预期相同；
- 唯一需要注意的是**将来 rebase 时** `generate.cpp`（99 条）与 `CMakeLists.txt`（49 条）会是主要工作量。

### 方案：**加一条，调整两条的判据**

| 条目 | 变化 |
|---|---|
| **新增 R66**（OPEN） | 三条 opt-in 的 cherry-pick + A/B：先 `fbf6e1c7`（零冲突）→ `5273fb66`（零冲突）→ `3cc47f02`（一处手解）。判据：prefill TTFT `|Δ|≥2×CV`、输出逐位相同（三条都自述 bitwise，用 `STRID`/哈希核对）、decode 不劣化 |
| **R61（PMC）** | 不变，但优先级下调：`fbf6e1c7` 直接改 MMQ 的缓冲布局，可能比"stream-k"更对症；先看它能不能把 21% 拉起来，再决定要不要花 9 分钟做 PMC |
| **R58（三段计数）** | 判据不变；上游的 `af6ba4c6` 给了现成的路径计数，实现它比自己埋点便宜 |
| **R65（rebase 评估）** | 已由本文回答了一半（冲突面 10 个文件）；剩下的问题是"要不要整体 rebase 到 0.2.10"，建议：**先 cherry-pick 这三条**，rebase 等有硬理由再做 |

---

## 6 复现

```bash
cd ~/strata166/pr/strata-fork
git fetch upstream && git log -1 --format="%h %ad" upstream/main
MB=$(git merge-base HEAD upstream/main)
for f in $(git diff --name-only $MB..HEAD); do
  n=$(git log --oneline HEAD..upstream/main -- "$f" | wc -l); [ "$n" -gt 0 ] && echo "$n $f"; done | sort -rn

# cherry-pick 试算（不影响工作树）
git worktree add -f /tmp/w920 HEAD && cd /tmp/w920
for c in fbf6e1c7 3cc47f02 5273fb66; do git cherry-pick -n $c && echo "$c OK" ; git reset --hard -q; done
```
