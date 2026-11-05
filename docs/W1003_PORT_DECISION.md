# W1003 · 「完整生产移植」的定界与执行方案

> 机主追问「完整移植，我问的是这个」。上一轮我给的是五通道表 + `NOT_STARTED`，
> 那是**清单**不是**答案**。这一版回答三件事：完整移植在我们这套引擎里到底由
> 哪几段代码构成（带 file:line）、每段的验收是什么、以及**它还值不值得做**。
> 全部数字来自本轮实测（`ci/repack_ab/WIDTH_SWEEP.tsv`）。

## 1 先把「完整」定义成可执行的东西

一个有资格叫「完整生产移植」的改动，必须同时满足六条。少一条就是半成品，
而半成品在生产上比不做更危险（布局混用会静默算错，不报错）：

> **子号（W1003-c）**：下表的 C1…C6 在方案与账本里记为 **R86-C1 … R86-C6**（`PROGRESS.tsv` 各一行）；
> C4 记 NA、C6 记 WITHDRAWN（计 0），其余为 OPEN/PARTIAL。

| 通道 | 承担什么 | 我们的落点 | 判据 |
|---|---|---|---|
| C1 权重上传 | 磁盘上的 canonical 字节变成常驻的 repacked 字节 | host arena 装载（`tools/iq_pack.py` 产物 → 引擎 mmap）+ `copy16_group_kernel` | 每个专家一次，不进入热路径 |
| C2 调度分派 | 谁走 repacked、谁留 canonical、tile 多宽 | `src/prefill/moe_mmq.cu:498 Context::run` | `expert_stride` 与布局一致 |
| C3 激活对齐 | src1 的 grouped MMQ 布局与 kernel 期望逐字节一致 | `src/prefill/moe_mmq.cu:460 quantize` → `block_q8_1_mmq_h` | 3 条 static_assert 的等价测试 |
| C4 融合 | gate/up + GLU 合并 | 已经是 `prefill.cpp:5300` 的单次 1280 行调用 | — |
| C5 验收 | 正确性 + 性能 + 回滚 | `--lengths` 六档、2×CV、KL/top-1、env 开关、镜像回滚 | 见 §4 |
| C6 分派混合 | 小段/大段走不同宽度 | **解散**，见 §3 | — |

## 2 每段的具体改法（真到函数级）

### C1 权重上传

生产专家的常驻形态是 host arena（71.7 GiB，7463 槽 / 21.79 GiB 在卡上，
2606 次借槽）。**repack 只能发生在「装进 arena 的那一次」**，不能发生在借槽时
（2606 次 × 每专家 1.2 MB 的转换 = 纯浪费），也不能在 copy kernel 里做（那是热路径）。

- 位置：`tools/iq_pack.py` 之后的 arena 装载（canonical 字节 → 内存），或首次 mmap 时原地重写。
- 关键实测（W1003，`WIDTH_SWEEP.tsv` 头部）：
  - **Q5_1 down：尺寸中性**，canonical 1 228 800 B = repacked 1 228 800 B
    ⇒ `ga.d_stride`、零尾、借槽账本**全都不动**，只换字节顺序。
  - **Q8_0 down：+2.3%**，1 740 800 → 1 781 760 B
    ⇒ `d_stride`、`copy16_group_kernel` 的 `nz` 尾部清零、arena 的 per-expert d offset
    必须跟着改；漏一处就是布局错位（不报错、算错）。
- **gu 一律不动**：Q4_K/Q5_K 的 repacked 布局反而膨胀（Q4_K dn 942 080 vs
  737 280 canonical，+28%），因为 K-quant 要拆成 4 个平面并 de-alias。

### C2 调度分派

- `Context::run` 里 `expert_stride = p.expert_bytes / type_bytes(t)`（`moe_mmq.cu:505`）
  是 canonical 的算法；repacked 必须换成 `repack_gcn_nbytes(type, ne0, ne1)`，否则
  `expert * expert_stride` 直接指错专家。
- 需要一个 `Product.layout`（canonical / repacked），因为**同一层里 gu 是 canonical、
  down 是 repacked**，不能靠全局开关。
- 宽度规则（W1003 实测，不猜）：
  - Q5_1 down：`w32`，全行数档（32/128/320/512/1024）都是 0.79–0.81。
  - Q8_0 down：≤320 行 `w32`（0.54–0.58），≥512 行 `w64`（0.60–0.61）。
  - 任何 gu：canonical。
- 注意 mx 的 `use_w32` 阈值是为它自己的形状写的，**不能照抄**（§3）。

### C3 激活对齐

`quantize()` 已经产出 grouped MMQ 布局（128 值/块、`d4[4]` 为 f32），mx 侧用
`block_q8_1_mmq_h` 重解释同一块内存，并有三条 `static_assert` 钉住尺寸与字段偏移。
缺的是**我们自己的等价断言**：把 `sizeof(block_q8_1_mmq)`、`offsetof(d4)` 与
`QK8_1_MMQ` 写进一个编译期测试，避免哪天上游改布局而我们静默错位。

### C4 融合

上游 2026 年的两笔（#29948 稠密、#31188 MoE，DGX Spark +17.2% / 5090 +5.7%）收益
来自「gate、up 两次 `mul_mat_q` 合成一次」。**我们的 gu 本来就是一次 1280 行调用**
（`prefill.cpp:5300`），权重在同一个 blob 里相邻（`copy16_group_kernel` 的
`ga.up_off`）。剩下的只有「GLU 写回进 epilogue」——省 1280 行写 + 640 行读，
按 320 行算约 800 KB，~3 µs，相对 1.04 ms 是 0.3%。⇒ **不做，且有理由，不是没看。**

### C6 为什么解散

R97 原计划「按 `expert_bounds` 每段行数混合分派（小段 repacked / 大段 canonical）」。
W1003 证明这个设计建立在错误前提上：320 行的 1.183 是 **64 宽臂**的数，
32 宽臂同点是 0.955。既然 w32 在 down 的所有行数档都赢，就没有「需要留给 canonical 的大段」；
而 gu 因为 Q4_K 永远不会 repack，也不需要按段分。⇒ 只剩一条**按类型的宽度规则**（§2 C2），
一个 `if`，不是分派器。

## 3 mx 的 `use_w32` 阈值不能照抄

`mul-mat-id.cu` 的规则是 `use_w32 = n_assign < 2 * BN_ID * ne02`（16 专家 = 4096 行）。
W1003 在 640×2560 Q5_1 上的三臂数据说明这条线对我们是错的：从 32 行到 1024 行，
w32 全部优于或等于 w64（320 行 0.955 vs 1.183；1024 行 0.939 vs 1.002）。
所以移植时**要么按我们的形状重新标定阈值，要么直接固定 w32**；
照抄阈值 = 把上游为别的形状调的参数搬进我们的瓶颈。

## 4 C5 验收清单（缺一项不算移植完成）

1. **逐位等价**：同一批激活、同一批权重，repacked 与 canonical 的输出 `memcmp` 为 0
   （Q5_1 的 dp4a 累加顺序相同；若不等，先查 scale 的 f16→f32 读取路径）。
2. **六长度档**：`--lengths` 2K/8K/16K/32K/64K/128K，每档 ≥10 次、同重启基线、
   与相邻档比较（`P38`：自比同形状）。
3. **2×CV**：当次 run 的 CV 两倍以内；相位只用于定位，不做判据（`W809`）。
4. **质量门**：KL / top-1（R94 欠账）——布局换了但数值应逐位相同，KL 必须为 0；
   不为 0 就是移植错了，不是「量化噪声」。
5. **开关与回滚**：`STRATA_REPACK_D=1` 灰度，默认 0；镜像保留 `0.2.10-101`，
   引擎 md5 `eea5ea3749ad54b124330386605a18bc` 必须可回。
6. **记账**：`PRODUCTION_PORT` 只有在 1–5 全绿后才允许从 `NOT_DONE` 改写。

## 5 判定

- 全量移植（专家全部 repack）：**NO-GO**。gu 会慢 0.2–1.9 倍。
- 定向移植（只 down）：down 占 prefill 13%，−20% ⇒ 端到端 **−2.6%**；
  Q8_0 层 −40% 但层数少 ⇒ **−2.6% ~ −3.3%**，低于 5% 门。
- 因此**不建议现在开这一轮工程**。队列里比它大的两块是 `dequant` 8–18% 与
  `wait copy` 7–15%（W853 §5 已排序），先把那两块做完或判否，再来收 down 的 ~3%。
- 若机主仍要移植 down：按 §2 C1/C2 + §4 执行，工作量集中在
  Q8_0 那条 `d_stride` 与零尾（唯一会改借槽账本的地方）。
