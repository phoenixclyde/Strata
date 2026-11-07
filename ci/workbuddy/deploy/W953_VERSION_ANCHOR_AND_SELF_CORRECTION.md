# W953 · 版本锚点：我们的 llama.cpp 到底是哪一版（并纠正 `AUDIT24` 自己写错的一条）

- 日期：2026-11-04 16:4x–17:0x
- 触发：机主「审计输出全面整改，并优化调优方案」。整改第一条就撞上 `A24-12`——
  我在那里采纳了 `W948` 的「版本号不是可比锚点」，本轮复核发现**这个更正是错的**。

---

## 1 三条硬证据（都可复现）

| # | 证据 | 命令 / 结果 |
|---|---|---|
| 1 | 我们自己声明是 **0.4.1** | `grep LLAMA_VERSION_ /home/albus/strata166/llama.cpp/CMakeLists.txt` → MAJOR 0 / MINOR 4 / PATCH 1；`GGML_VERSION` = 0.24.0 |
| 2 | 我们的 `ggml-cuda` **就是 upstream `e6ab7c1a4`** | 取 `e6ab7c1a4/ggml/src/ggml-cuda/mmq.cuh`（71,851 B）与我们那份 `diff` ⇒ **0 行差异**（去掉 CR 后逐字节相同） |
| 3 | 各 tag 的 `LLAMA_VERSION` 是一个**单调递增的自家字段** | e6ab7c1a4 = **0.4.1**；b11553 = **0.6.0**；b12099 = **0.8.0**；master = **0.8.0** |

⇒ **我们 = upstream `e6ab7c1a4`（2026-09-22，LLAMA_VERSION 0.4.1）**，一字不差。
`W948` 当时说「`LLAMA_VERSION 0.4.1` 不能和 fork 的 release 名比先后」——**前半句对（fork 的 release 名不是这个字段），
后半句错（这个字段本身就能比）**。我把它当结论抄进了 `AUDIT24 A24-12`，现更正。

## 2 `get_J_max` 那件事，我判反了

`W948` 的原推理：「furnace / exabit / mx 都没有 `get_J_max`，我们有 ⇒ 它们基于更旧的树」。本轮实测：

| 树 | `grep -c get_J_max` |
|---|---:|
| 我们（= e6ab7c1a4） | **1**（`mmq.cuh:372`，`ggml_cuda_mmq_get_J_max`） |
| upstream master / b12099（0.8.0） | **0** |
| mx（0.6.0） | **0** |
| furnace（0.4.1 基座） | **0**（它的 MMQ 被自己的 retune 重写） |

⇒ 这个符号是 **0.4.1 时代的上游代码，后来被上游删掉了**，不是我们的补丁、更不是"新"的标志。
**「有它 = 更旧」**（furnace 是例外：同基座但重写了 MMQ）。我上一轮写成"上游也是 0 ⇒ 那是我们自己的补丁"，
**两个判断都错**，现一并作废。

## 3 五棵树的正确定位

| 树 | LLAMA_VERSION | 与我们 | 备注 |
|---|---|---|---|
| **我们（pin）** | **0.4.1** | — | = `e6ab7c1a4`，2026-09-22 |
| **furnace** | 0.4.1 基座 | **同基座** | README 自述 rebase 到 `e6ab7c1a4`；它的 +41%/+80%/+126% 是**在我们这条基线上**打补丁打出来的 |
| **mx（mxxm-t）** | 0.6.0（`b11553`） | 新 2 个 minor | repack 的数字在更新的基座上 |
| **exabit（merge-v0.7.0）** | 0.7.0 | 新 3 个 minor | mx + 九补丁 |
| **upstream b12099 / master** | **0.8.0** | **新 4 个 minor** | 2026-11-04T05:47:21Z 发布 |

⇒ 三个直接后果：

1. **`W948` 的「三家 fork 都比我们旧」方向反了**：mx / exabit 都比我们新，只有 furnace 与我们同基座。
2. **`R90` 从"方向成立、判据无效"升级为硬事实**：我们落后 **4 个 minor**（0.4.1 → 0.8.0），
   而这 4 个 minor 覆盖的正是 qwen4exp / GDN / QSA —— 也就是我们 prefill 的三个大头。
3. **furnace 的证据等级上升一档**：它不是在"更新的上游"上跑出来的，而是**在我们的基线上**加补丁跑出
   prefill 8K 887→1251 / 32K 867→1561 / pp8192 877→1978。⇒ 它的补丁集可以当**参考实现**直接对照移植，
   不必赌版本差异；同时也说明 **0.8.0 未必自动带来这些收益**（上游没有那两个异步拷贝开关，见 `W954`）。

## 4 「换基线」的收益因此要重新估计

| 项 | 旧表述（`W948`/`AUDIT24`） | 现在（有锚点） |
|---|---|---|
| 我们落后多少 | 「与 master 差 587 行」（行数，不是版本） | **0.4.1 vs 0.8.0 = 4 个 minor**；587 行是同一天 master 的文本差 |
| 三家 fork | 「都比我们旧」 | mx 0.6.0 / exabit 0.7.0 **比我们新**；furnace **同基座** |
| 升级能拿到什么 | 不确定 | 4 个 minor 的上游修正（含 qwen4exp/GDN/QSA），**但不含** furnace 的异步拷贝（已验证上游无该开关） |

## 5 纪律新增

> **㉕ 版本先后必须用"正确 tag 上的来源文件"证明，不能用符号的有无推断。**
> 本轮两个方向各错一次：`W948` 判「无 `get_J_max` ⇒ 更旧」（反了），`AUDIT24` 判「上游也无 ⇒ 是我们的补丁」（也反了）。
> 正确做法：①先读对方 `CMakeLists` 的 `LLAMA_VERSION`；②再拿**一个文件**做逐字节比对；③符号只在同版本内比较。

## 6 复现

```bash
# 1 我们的版本
grep -E "LLAMA_VERSION_(MAJOR|MINOR|PATCH)" ~/strata166/llama.cpp/CMakeLists.txt
# 2 与 e6ab7c1a4 逐字节比
curl -sL -o /tmp/mmq_e6ab.cuh https://raw.githubusercontent.com/ggml-org/llama.cpp/e6ab7c1a4/ggml/src/ggml-cuda/mmq.cuh
diff <(tr -d '\r' </tmp/mmq_e6ab.cuh) <(tr -d '\r' <~/strata166/llama.cpp/ggml/src/ggml-cuda/mmq.cuh) | wc -l   # 0
# 3 各 tag 的版本字段
for r in e6ab7c1a4 b11553 b12099 master; do
  printf "%-12s " $r; curl -sL https://raw.githubusercontent.com/ggml-org/llama.cpp/$r/CMakeLists.txt | grep -m3 LLAMA_VERSION_ | tr '\n' ' '; echo
done
```
