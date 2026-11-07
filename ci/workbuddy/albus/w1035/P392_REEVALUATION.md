# P392 重估 · 上游 #29953（"CUDA: fix MMQ out-of-bounds reads"）到底要不要花停机窗口去测

> 2026-11-07 02:4x，W1035。**零停机、零写生产、零引擎启动**。
> 所有结论标注：`源码核实`（逐行读镜像内 `/src` 与上游 diff）/ `本机计算`（用镜像内配置表算出来的数）/ `实测`（有运行期数字）/ `推测`。
> 证据脚本：`albus/w1035/mmq_pad_check.py` + `albus/w1035/mmq-config-gcn.cuh`（从镜像内逐字节取回，26,167 B）。

---

## 0 结论先行

1. **生产树是修复前版本**（`源码核实`）。不是「不确定」，是逐行对上：`mmq.cuh:372` 仍是 `ggml_cuda_mmq_get_J_max()`，`mmq.cu:137/206` 仍用它算 padding，`mmq_args` 末字段仍是 `ncols_opt`。
2. **这条修复不改被选中的 tile**（`源码核实` 等价性）。`J_best` 的选择循环在补丁前后**逐行相同**；`ncols_opt`、`fallback` 三条输入也都等价 ⇒ 派发到同一个 `launch_mul_mat_q<type,J,fallback>` 实例 ⇒ 浮点累加顺序不变 ⇒ **数值应当逐位相同**（此最后一句是 `推测`，未做运行期实测，理由见 §4）。
3. **我们的热路径本来就不越界**（`源码核实`）。Strata 自己的 MoE 预填不走 `ggml_cuda_mul_mat_q` 的分配：`moe_mmq.cu:407` 的 `q8_bytes()` 固定加 **128 块**（= 可能的最大 J），`gemm.cu:1282` / `prefill.cpp:1605` 都走它。
4. **因此 P392 原定的实验（`-001` vs `-010` 出 top-1/KL）测不出这条补丁**（`源码核实`）：`-010` 是「0.9.0 树 + mmq 头@4c1004c」的**混合树**，两臂之间差的是一整棵树，不只是一条修复。就算 KL 出来是 0，也不能证明「#29953 没副作用」；出来不是 0，也归因不到它。**这条实验设计从一开始就测错了对象。**

---

## 1 生产树是 pre-fix：逐行证据

上游 `ggml-org/llama.cpp#29953`（已合并，head `3070d927`，base `2e7c58c5`）的标题与正文（`官方核实`，GitHub API）：

> "CUDA: fix MMQ out-of-bounds reads" —— "On master the number of columns that are being checked for viable configs is being rounded down for the allocation but *rounded up* when selecting the actual config to run."

补丁把「选 tile」从 `mul_mat_q_switch_J` 提前到 `ggml_cuda_mul_mat_q` 里，用 `J_best` 直接算 padding，并**删除** `ggml_cuda_mmq_get_J_max`。

| 位置 | 上游 master（pre-fix） | 我们镜像内 `/src` | 判定 |
|---|---|---|---|
| `mmq.cuh:372` | `ggml_cuda_mmq_get_J_max(type,fallback,cc,ne11)`，`ret=min(ne11,512); ret-=ret%8;` 向下走 | **原样存在** | pre-fix |
| `mmq.cu:137` | `... + get_J_max(type,fallback,cc,ne11)*sizeof(block_q8_1_mmq)` | **原样存在** | pre-fix |
| `mmq.cu:206` | MoE 分支同上 | **原样存在** | pre-fix |
| `mmq_args` 末字段 | `int J_best;`（fix 后） | `int64_t ncols_max; int64_t ncols_opt;` | pre-fix |
| `mul_mat_q_case` | `if (needs_fallback(nrows)) fallback=true else false` | `if (nrows_x % 128 == 0) fallback=false else true` | 语义等价 |

---

## 2 为什么「数值不变」是源码级可证的

补丁删掉的整块（diff 的 `-` 行）与生产树里 `mmq.cuh:1479-1500` 的循环**逐字相同**：

```
for (int J = 8; J <= 128 && ntiles_J_best > 1; J += 8) {
    config = get_config(type, J, fallback, cc);          // fix 后多一个 prec_src1，gfx906 恒为默认
    if (config.type == COUNT) continue;
    if (mmq_get_nbytes_shared(config, cc) > smpbo) continue;
    ntiles_x = (ncols_opt + config.J - 1) / config.J;
    if (ntiles_x < ntiles_J_best) { J_best = J; ... }
}
```

三条输入在补丁前后等价（`源码核实`）：

| 输入 | pre-fix（生产树） | post-fix（补丁） | 等价性 |
|---|---|---|---|
| `ncols_opt`（dense） | 函数实参 `ne1`（`mmq.cu:172`：`ne1, ne1`） | 局部 `ncols_opt = ne11` | `ne1 == src1->ne[1] == ne11` ✅ |
| `ncols_opt`（MoE） | `ne12`（RDNA3/4 才做平均，gfx906 走不到） | `ne12`（`if (ids)` 分支，同样只对 RDNA3/4 平均） | ✅ |
| `fallback` | `ne01 % 128 != 0` | `ggml_cuda_mmq_needs_fallback(ne01)` = `nrows_x % 128 != 0` | ✅ |

⇒ 同一个 `J_best` ⇒ `switch(J_best)` 进入同一个 `launch_mul_mat_q<type, J, fallback>` 模板实例 ⇒ K 方向的累加顺序、tile 大小、`K_vram` 全部不变 ⇒ **只有「缓冲区多大」变了，计算本身没变**。

补丁真正改的三样，全是内存安全面：
1. `src1_q8_1` 的 padding 由 `get_J_max(ne11)` 改为「由 `J_best` 反算并向上取整到 `nthreads*4`」；
2. `ids_dst` 多分配 `J_best-1` 个 `int32_t`（注释：*Needs to be padded for unconditional memory access*）；
3. `static_assert(J <= 128)`，把越界值挡在编译期。

---

## 3 我们到底暴露多少：算出来的，不是估的

`albus/w1035/mmq_pad_check.py` 用镜像内的 `mmq-config-gcn.cuh`（250 条 CASE）复现两个函数，扫描 `ne11 = 1..512 + {1000,4096,16384}`：

```
Q4_K / Q5_K / Q6_K / Q5_1   gfx906 上最大可用 J = 64     （表里没有 >64 的 CASE）
Q8_0                        gfx906 上最大可用 J = 128
```

| 路径 | 分配方 | 余量 | 越界上界（本机计算） |
|---|---|---|---|
| **MoE 预填（我们的主战场）** | strata `moe_mmq.cu:407 q8_bytes()` | **+128 块**（≥ 任何 J） | **y 缓冲 0**；`ids` 仍是 `T*K` 精确尺寸（`prefill.cpp:1832`） ⇒ ≤ `(J-1)*4 B` ≈ **≤252 B**（J≤64） |
| **ggml dense（`ggml_cuda_mul_mat_q`）** | upstream `get_J_max(ne11)` | 向下取 8 的倍数 | `fallback=false`（我们的权重 640/1280/2560 全是 128 倍数）⇒ **16 块 = 2,304 B**；`fallback=true` ⇒ 32 块 = 4,608 B |
| 触发条件 | — | — | 仅当 `ne11 % 8 != 0`（dense）时 `J_best = J_max + 8` |

对我们真实的 prefill 形状（`ne11` = 每 ubatch 的 token 数，常见 1000 / 16384）：

```
Q4_K  ne11=1000  → J_max=64  J_best=64  Δ=0
Q4_K  ne11=16384 → J_max=64  J_best=64  Δ=0
Q5_1  ne11=1000  → J_max=64  J_best=64  Δ=0
Q8_0  ne11=1000  → J_max=128 J_best=128 Δ=0
```

⇒ **我们生产上跑的形状，dense 路径也不越界**；越界只出现在「token 数不是 8 的倍数」的边角档。

---

## 4 所以 P392 该怎么结（不靠拍脑袋，也不越纪律）

账本纪律（`W832` §6.2 前的硬规矩）：**"只有 ISA 计数、Amdahl 推算、源码阅读的，一律写 OPEN"**。
本条全部是源码阅读 ⇒ **P392 保持 OPEN**，但**必须换门**：现在的门测的是错对象（§0.4）。

三个可选项，成本从低到高：

| 选项 | 做法 | 停机 | 能证明什么 | 风险 |
|---|---|---|---|---|
| **A（建议）** | 判 P392 为 **N/A（门不适用）**：记录「#29953 数值面源码级等价 + 热路径零暴露」，把 `R51` 的 10-19 分支结为 DONE_NEG（性能侧 `P390` 已实测为 0），队列前移到 `R95` | **0** | 只证明「这条补丁不值得为它停机」；不声称「运行期实测过」 | 若日后换栈时它变相关，需重开 |
| **B** | 一次 ~2 min 窗口：`STRATA_MMQ_DEBUG_J=1` 起 `-001` 与 `-010`，只读 `pick_J: ... -> J=` 行 | 2–3 min | 实测两臂 J 相同（比 KL 直接） | 仍需停生产；且 `-010` 是混合树 |
| **C** | 原方案：`quant_quality prompt/pcompare`，两只引擎各 40 条 prompt | 12–15 min | 混合树整体差异（**归因不到 #29953**） | 最贵、最不可解释 |

**推荐 A**。理由：C 的结论无论正负都用不上（§0.4）；B 能拿到的东西，A 的 §2 已经以更强的形式（逐行等价）给出；而 A 不花一分钟停机。

---

## 5 举一反三：这次挖出来的三件通用教训

1. **「性能免费」不等于「可以拿」**。`P390` 的结论（K10 = 534.83/716.72，与 001 的 532.76/714.89 持平）是对的，但它证明的是「这段栈不掉速」，从来没证明「拿走它有收益」。一个只含安全修复、且安全修复在我们路径上被自家 padding 抵消的补丁，收益是 **0**。队列里它排第 1，是因为 `R51` 立项时以为它能提速。
2. **`q8_bytes()` 的 +128 块是个无注释的隐式不变量**（`moe_mmq.cu:407`）。它能抵消上游同类越界，但没人写下来；任何一次「顺手把 128 改成 J_max」的重构都会把上游的坑重新引入。**建议给它加一行注释锁住**（下一个动这块的人不会知道）。
3. **混合树不能做归因**。`-010` = 0.9.0 树 + 旧 mmq 头；用它去测「某一条上游补丁的数值影响」，把树差和补丁差绑在一起。这和 `P389`（ladder-5 崩溃来自混合树，不是补丁）是同一个病，第二次出现。**规则**：单补丁归因必须「同树 + 单 patch」，否则只记「这一段栈」的整体，不记单条。

---

## 6 未核 / 边界（不许当成已结）

- `mmq_get_nbytes_shared` 的 smpbo 过滤未纳入本计算：跳过一个 tile 只会让 `J_best` **更大**，所以 §3 的越界数是**下界**，结论方向不变（越界只会更多，不会更少）。
- `ids` 的 `T*K` 精确尺寸取自 `prefill.cpp:1832`，未逐条核对该 buffer 在 `p.ids` 链路上的最终尺寸；若另有对齐，残余暴露更小。
- 运行期从未实测：**没有任何一次引擎启动**用来验证 §2 的逐位等价。按纪律这仍是 `推测`，只是推断强度高到「不值得为它停机去证」。
- `-010` 的 `short-read` 空转（`P392` 原记录）**仍未定位**；本轮只是绕开了那条路径（新设计不碰 decode 窗口），并未解释它。

## 7 复现

```
python albus/w1035/mmq_pad_check.py
# 输入 mmq-config-gcn.cuh 取自（只读）：
#   docker exec strata166-407 cat /src/third_party/llama.cpp/ggml/src/ggml-cuda/mmq-config-gcn.cuh
```
