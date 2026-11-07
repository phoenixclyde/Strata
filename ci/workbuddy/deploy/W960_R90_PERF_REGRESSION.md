# W960 · R90-S4 性能：0.8.0 的 prefill 慢 **6%**（3 vs 3，区间不重叠）⇒ R90 降级

- 日期：2026-11-04 19:0x–19:3x
- 方法：同一 prompt（2048 合成 id）、同一 args、同一镜像、每次全新容器；A = 生产件（0.4.1）×3，B = 移植版（0.8.0）×3。
- 一句话：**prefill 602 → 566 tok/s（−6.0%），decode 持平（19.0 tok/s）**。
  两个可能的"我们自己的错"都已排除（见 §2、§3）⇒ 这是 0.8.0 内核本身在这条路径上的退步。

---

## 1 数字

| 臂 | 二进制 | prefill（tok/s） | 三次 | 均值 | SD | decode |
|---|---|---|---:|---:|---:|---|
| **A** | `strata-0.1.56`（0.4.1） | 601.74 / 604.28 / 599.17 | 3 | **601.7** | **2.6**（0.4%） | 18.94 / 19.10 / 40.36 |
| **B** | `build-080c/strata`（0.8.0） | 568.41 / 552.15 / 576.82 | 3 | **565.8** | **12.5**（2.2%） | 19.01 / 19.03 / 19.07 |

- **区间不重叠**：B 的最大值 576.8 < A 的最小值 599.2。
- Welch t ≈ **4.9**（df ≈ 2.3，p ≈ 0.02）。
- prefill 口径：2047 token，`--prefill auto:16384`、`0 reused`。
- decode 有个异常：A 的第三次 **40.36 tok/s**（其余两次 19.0）——专家驻留状态不同导致 2× 抖动，这同时解释了 `W958` 的不可复现。

## 2 先排除"J 选错"

我加了一句 `STRATA_MMQ_DEBUG_J` 打印，B 臂实测：

```
pick_J: type=7  ncols=412 fallback=0 -> J=64      (Q5_1)
pick_J: type=12 ncols=412 fallback=0 -> J=64      (Q4_K)
```

`type=7`=Q5_1、`type=12`=Q4_K，**两种主格式都落在 J=64**，与 0.4.1 内部那段
`for (J = 8; J <= 128 && ntiles>1; J += 8)`（同样的"tiles 最少且放得下"规则，`ncols_opt` 同样等于 max_rows）**同解**。
⇒ −6% 不是我们选错了 tile。

## 3 再排除"精度参数选错"

0.8.0 的 `ggml_cuda_mmq_get_prec_src1()` 结尾是：

```cpp
const bool can_use_q4 = (src0->type == GGML_TYPE_NVFP4 || src0->type == GGML_TYPE_MXFP4) && blackwell_mma_available(cc);
if (prec == GGML_PREC_Q8 || !can_use_q4) { return GGML_PREC_Q8; }
```

我们的类型是 Q4_K/Q5_1（非 FP4），cc=gfx906（无 Blackwell MMA）⇒ **上游自己也会选 `GGML_PREC_Q8`**，
与我们 27 处调用点写的一致 ⇒ 不是精度参数选错。

## 4 构建开关对比（唯一剩下的混淆项）

两棵树的 `CMakeCache` 逐项 diff，只有三处不同：

| 键 | build-r28（A） | build-080c（B） |
|---|---|---|
| `STRATA_GGML_DIR` | `/llama.cpp` | `/ref`（0.8.0） |
| `STRATA_MMQ_TQ_OVERLAY` | **ON** | **OFF**（trellis 段未适配，见 `W956 §5.1`） |
| `CMAKE_HIP_ARCHITECTURES` | `STRING=gfx906` | `UNINITIALIZED=gfx906`（同值，标记差异） |

其余 `STRATA_*` 全同。⇒ **唯一剩下的可能是 overlay 开/关**。要排除它，得把 trellis 的 `ggml_cuda_mmq_util_funcs(..., prec)`
也适配掉（约 6 处），再用 overlay=ON 重测。这件事**下一步第一优先**，因为它是"我们的构建"与"上游的退步"之间最后的分界。
（不过 trellis 只是多几个模板实例，理论上不该改 Q4_K 内核的寄存器分配——所以概率上我更倾向"上游退步"。）

## 5 对方案的直接影响（`W954` 要改排序）

`R90` 升到第一位的前提是"4 个 minor 的修正能换来收益"。现在：

- **收益未被看到**：`mmq-config-gcn.cuh` 与 0.4.1 逐字节相同（`W955`），tile 层没有变化；
- **代价是实测的**：prefill −6.0%，而 prefill 正是我们的大头。

⇒ **R90 从"第一位"降为"参考实现 / 按需摘取"**：

1. 不做整树升级上线；
2. 若要拿 0.8.0 的东西，只**摘**（cherry-pick）具体修复，逐条 A/B；
3. 队列第一位回到 **R88（异步分阶段拷贝）** —— furnace 在我们这条基线上做的，外证 pp8192 877→1978，
   且 `W955` 已验证上游 0.8.0 **没有**这两个开关（`INPUT_STAGE`/`ASYNC_INPUT_MIN` 零命中）⇒ 它不会因为升级白拿，必须自己写。

## 6 还没做

| # | 事 | 为什么重要 |
|---|---|---|
| 1 | overlay=ON 的 B 复测 | 排除最后一个混淆项 |
| 2 | 六长度档 prefill（2K/8K/32K/64K/130K） | 2048 token 只是单点；长档才代表生产（600-1200 ms 窗口） |
| 3 | decode 侧 A/B（含 spec on/off） | 本轮 decode 只测了 64 token，且 A 有一次 2× 异常，样本不够 |
| 4 | 若 6% 稳定：把 0.8.0 的 `mmq.cuh` 与我们 0.4.1 的差异按 hunk 定位 | 也许能摘回一两个"上游修好了但我们没有"的点 |

## 7 复现

```bash
bash albus/w960/b2.sh     # 单臂 B + J 打印；A 用同样命令换 /data/bin/strata-0.1.56
# 汇总
grep -hE "^prefill " data/w9{57,58,60}/*.out
```
