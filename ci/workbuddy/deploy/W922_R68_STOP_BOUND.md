# W922 · R68：`#4677` serve stop bound 的移植尝试与判定

> **【AUDIT24 P1 · 2026-11-04】§71 的措辞错**：99.72% **低于**上游打补丁后的 99.74%，不是"高于"。
> 正确表述：**与补丁后基本持平（−0.02pp）、远高于补丁前的 98.36%**。结论（没有 6% 可修、不移植）不受影响。

日期：2026-11-04 00:4x
状态：**部分 DONE_NEG**（补丁可移植、编译通过，但**本场景不复现该 bug，无收益空间**）；同时产出一条高价值的移植规则

---

## 1 一个必须先说的发现：上游所有 "HIP only" 的补丁，在我们 gfx906 上是**死代码**

`243fdb21` 的三处改动全部包在 `#if defined(STRATA_USE_HIP)` 里。而我们的构建**不定义这个宏**：

```
CMakeLists.txt:702  # [W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp
                    # keys its ... a global STRATA_USE_HIP would switch CUDA-only paths elsewhere
                    # (W717/P23 measured that).
CMakeLists.txt:706    set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS "STRATA_USE_HIP=1")
cmake/hip_backend.cmake:98  target_compile_definitions(strata_hip_runtime INTERFACE STRATA_USE_HIP=1)
```

实测：编译命令里**没有** `-DSTRATA_USE_HIP`（只有 `-DSTRATA_HIP_GFX906=1`），预处理验证计数 **0**。

⇒ 第一次编译出来的 `.o` 里 `strings | grep STRATA_SERVE_STOP_BOUND` = **0**，补丁完全没进二进制。

**正确做法**：把补丁那 4 处改成 `#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)` ——
这是本仓库对 gfx906 的既有写法（`generate.cpp:1583/2978/4163` 原本就是这个形式）。

## 2 但我自己踩了一个更危险的坑，必须记下来

第一版我用 `sed` 把**文件里所有**单独成行的 `#if defined(STRATA_USE_HIP)` 都加了 `|| defined(STRATA_HIP_GFX906)`
——**20 处**。这等于全局打开 `STRATA_USE_HIP`，正是 `CMakeLists.txt:702` 明确警告过的、`W717/P23` 实测会出问题的事。

已回退：从原树 `cp` 回 `generate.cpp`（md5 `c920756a`），`git apply --include=src/program/generate.cpp` 重打补丁，
再用**上下文精确匹配**只改补丁的 4 处：

```
30    #if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)   ← 补丁：include
16137 #if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)   ← 补丁：stop_bound 变量
16684 #if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)   ← 补丁：应用点 1
17113 #if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)   ← 补丁：应用点 2
1583/2978/4163  ← 原文本来就是复合条件，未动
其余 16 处      ← 保持 #if defined(STRATA_USE_HIP) 原样
```

**规则（写进方法）**：移植上游 HIP-only 代码，宏只能**按补丁范围**加，绝不能全局替换。

产物：`9d9cbe17`（40,784,832 B），`strings` 有 `STRATA_SERVE_STOP_BOUND`，`nm` 有 `serve_stop_bound` 符号 **2 个**（对应两个应用点）。

---

## 3 判定：本场景不复现 bug，补丁无收益空间

上游 `#4677` 的症状（提交自述）：

> *"a request's last window could park a snapshot with **tokens the client never received** … the snapshot was refused
> and the older checkpoint was used (**about 6% of a 12K-token prompt read again**)"*
> 实测 4×R9700、2 replicas×2 cards、`--batch 8 --batch-groups 2`：**4/16 续接回退 → 0/16**，复用 98.36% → 99.74%。

我们的形状完全不同：**单卡、单流、`--spec 4`、无 batch**。按同一思路构造多轮测试
（4 段 ~6.7K token 对话，每段第 1 轮 + 第 2 轮追问），读服务端 `strata serve: prompt N tokens = M reused + K read in`：

| 段 | turn2 prompt | reused | 复用率 |
|---|---|---|---|
| conv1 | 6716 | 6697 | **99.72%** |
| conv2 | 6681 | 6662 | **99.72%** |
| conv3 | 6674 | 6655 | **99.72%** |
| conv4 | 6723 | 6704 | **99.72%** |

**4/4 全部 99.72%，`<99%` 的段数 0/4**。只重读 19 token（0.28%），且这 19 token 基本就是追问句本身。

⇒ **没有"少复用 6%"可修**。补丁最多再省那 0.28%，远低于 2×CV，**无意义**。
⇒ 而且我们的 99.72% 与上游"打了补丁后"的 99.74% **基本持平（−0.02pp，同一量级）**，远高于其"没打补丁"的 98.36%。

**判定：R68 = DONE_NEG（无收益空间，不采纳）**。补丁本身已验证可移植、编译通过、符号正确，
若将来改多流 / `--batch`（机主已定"只做单流"），这条要重测。

---

## 4 测试方法上的三次失败（记下来，避免下次重犯）

1. **第一次**（`max_tokens=768`）：模型回答自然结束，没有截断 ⇒ 不满足 bug 的触发条件，4/4 都是 99.69%。
2. **第二次**（`max_tokens=48` 强制截断）：`answer1` 长度 **0** —— 思考内容占满了预算、`content` 为空，
   turn2 只比 turn1 多 14 token，等于没插入回答。
3. **第三次**（取 `reasoning_content`、`max_tokens=200`）：仍为 **0 chars**。

**根因**：本模型的响应里 `message.content` 与 `message.reasoning_content` 都可能是空（非流式形态），
我没先把结构 dump 出来就写了解析——这违反"先看数据再说"的纪律。
**正确做法**：先用一次 `curl` 打印 `list(d.keys())` 与 `message` 的字段，再写测试。

不过三次都收敛到同一结论（复用率 ≈99.7%，无回退），因为**前缀匹配的是 turn1 的 prompt**，
与 assistant 内容长短无关——这也说明该 bug 需要"服务端 park 的 token 与客户端收到的 token 不一致"才会触发，
而我们的单流路径没有产生这种不一致。

---

## 5 复现命令

```bash
# 1) 打补丁（只取 generate.cpp + 新头）
cd ~/strata166/pr/strata-fork
git show 243fdb21 -- src/program/generate.cpp include/strata/core/serve_stop_bound.hpp > /tmp/r68.patch
cd ~/strata166/work/r66
cp ~/strata166/pr/strata-fork/src/program/generate.cpp src/program/generate.cpp
git apply --include=src/program/generate.cpp /tmp/r68.patch

# 2) 只改补丁的 4 处宏（不要 sed 全局替换！）
#    见 §2 的行号

# 3) 编译 + 链接（必须 grep 取链接行，末尾是 POST_BUILD 的 ":"）
docker run --rm -v ~/strata166/work/r66:/src -v ~/strata166/gfx029-build:/out \
  -v ~/routeB/ML-gfx906/llama.cpp:/llama.cpp -w /out strata-gfx906:0.2.9-101 bash -lc '
    ninja -t commands CMakeFiles/strata.dir/src/program/generate.cpp.o | tail -1 > /tmp/g1.sh
    ninja -t commands strata | grep -E " -o strata( |$)" | tail -1 > /tmp/g2.sh
    bash -e /tmp/g1.sh && bash -e /tmp/g2.sh'

# 4) 多轮复用率
python3 /tmp/multiturn2.py A-基线
```
