# W887 · R46 第一步：prompt attention 的有效算力只有 FP32 峰值的 **11–16%**，所以「换 fp16」不是第一杠杆

**结论先行**：`qsa attn` 在长 prompt 上占 **19.2%**，但它跑在 **2.0 TFLOPS**，而 MI50 的 FP32 峰值是 **13.4 TFLOPS**。
⇒ **先修效率（上限 3.3×），再谈精度（2×）**。R46 原来的判据「19.2% × 2× = 9.6%」是**两种杠杆里较小的那一个**，
把它当成主方案会把 13% 的收益换成 9.6%。

---

## 1 先把模型的存在形式搞清（GGUF 元数据，现场读的）

`gguf_meta.py` 直读 `/models/.../Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` 的头 67 个 kv：

| 键 | 值 | 含义 |
|---|---|---|
| `qwen4exp.block_count` | **48** | 总层数 |
| **`qwen4exp.full_attention_interval`** | **4** | **每 4 层一个 QSA 全注意力 ⇒ 只有 12 层**，其余 36 层是 GDN/SSM 线性注意力 |
| `qwen4exp.attention.head_count` | 24 | 查询头 |
| `qwen4exp.attention.head_count_kv` | 2 | KV 头（GQA 12:1，源码 `constexpr int G = 12`） |
| `qwen4exp.attention.key_length` / `value_length` | **256** / **256** | head_dim = 256（源码 `constexpr int HD = 256`） |
| **`qwen4exp.attention.indexer.top_k`** | **2048** | **每个 query 只读 2048 个 KV cell**（源码侧 `qsa_selection_width(kTopkMaxCells)` → 工具注释写 "the 2,051 widest"） |
| `qwen4exp.attention.compress_ratios` | `[0,0,0,4, 0,0,0,4, …]` | 第 4/8/12… 层的 KV 以 4:1 压缩（与 interval=4 同一条缝） |
| `qwen4exp.expert_count` / `used` | 512 / 10 | MoE |
| `qwen4exp.context_length` | 262144 | |

**`full_attention_interval = 4` 是这一轮最重要的一个数**：它把「48 层都在做 attention」这个默认假设直接砍到 12 层。

---

## 2 于是每 token 的 attention 算术量是确定的

```
12 层 × (QK + PV 各 2 flop/MAC) × 24 头 × 256 维 × 2048 cell = 604 MFLOP/token
```

## 3 用生产相位表的三个点算有效算力（零停服，数据本来就在日志里）

`strata prefill timing: <n> tokens, GPU timeline <ms> … qsa attn <ms> (<pct>%)`

| 提示 | GPU timeline | `qsa attn` | 占比 | ms/token | 有效 cell/query | **有效 TFLOPS** | 占 FP32 峰 13.4 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 893 tok | 3,195 ms | 78 ms | **2.4%** | 0.087 | 446（因果平均，未触到 cap） | **1.51** | **11.3%** |
| 21,822 tok | 32,880 ms | 6,202 ms | **18.9%** | 0.284 | 2048（已饱和） | **2.13** | **15.9%** |
| 99,382 tok | 153,872 ms | 29,513 ms | **19.2%** | 0.297 | 2048（已饱和） | **2.03** | **15.2%** |

### 3.1 一个自检：如果 attention 是稠密 O(N²)，这组数**不可能**

按稠密算，99,382 token 需要 `4×24×256×9.88e9/2×12 = 1.16e16 flop`，29.5 s 内完成 ⇒ **395 TFLOPS** —— 是这块卡的 **29 倍**。
⇒ 反过来证明：**它确实是「每 query 只读 2048 个 cell」的块稀疏注意力**，而不是稠密。

### 3.2 ms/token 饱和本身就是证据

0.087 → 0.284 → **0.297**：从 22K 到 99K（4.5 倍长度）每 token 成本只涨 **4.5%**。
⇒ 成本 **∝ n**（线性），不是 ∝ n²。这正是 `indexer.top_k = 2048` 的形状。

---

## 4 三种改进假设分别值多少 prefill

| 假设 | attn 变成 | 省 prefill（22K / 99K） | 依据 |
|---|---:|---:|---|
| **只换 packed fp16（效率不变）** | 6,202 → 3,101 ms | **9.4% / 9.6%** | Vega20 每 CU **128 FP16 vs 64 FP32 单元** ⇒ 峰值 2×（26.8 TFLOPS）；这就是 R46 原先写的 9.6% |
| **只修效率到 FP32 峰的 50%** | 6,202 → 1,967 ms | **12.9% / 13.4%** | 6.7 TFLOPS；同形状 attention 在 SIMT 卡上 40–60% 是常规 |
| **两者都拿到（理论上限）** | 6,202 → 984 / 2 → 492 ms | **17.4% / 17.7%** | 效率 ×2.9 再 ×2 精度 |
| 现状 | 6,202 ms（2.13 TFLOPS） | — | 本文件 §3 |

**⇒ 只做 fp16 是三种里最差的一种**，而它恰好是我上一轮写进 R46 的那条。R46 已据此改靶。

---

## 5 为什么「效率只有 15%」不能直接说成「代码写得差」

这个 kernel 每读一个 cell 要做的事不止 FMA：

| 工作 | 量（每 cell） | 落在哪个单元 |
|---|---|---|
| K 反量化 | 256 × int8→half | VALU（不是 FMA 单元） |
| QK | 256 FMA | FMA |
| V 反量化 | q4_0：256 值 = 128 字节 + 8 组 scale，需解包 | VALU |
| PV | 256 FMA | FMA |

⇒ **有用 FMA 只占 VALU 总量的一半左右**，「15% of FP32 peak」里至少有一半是反量化的必要成本。
所以：**2× 是能拿的，2.9× 要看反量化能不能并进 FMA 流水**——这个问题只能靠给 kernel 加相位计时，不能再靠算术推。

---

## 6 本轮**没能**拿到的：隔离内核的实测

试了两条，都堵死，记下来免得下次重试：

| 工具 | 结果 |
|---|---|
| `src/kernels/qsa_prompt_attn_parity.cpp`（能在 gfx906 编译，需 `-Iinclude/strata/hip_compat`、`.a` 前加 `-x none`） | 运行即 `SKIP: gfx906… is not gfx11 / gfx12 (the matrix-core prompt attention)`，**return 77** —— 它只测矩阵核路径 |
| `tests/cuda/pa_bench.cpp`（正是「按录制的 selection 跑 prompt attention」） | 需要 `STRATA_QSA_DUMP` 产出的 dump 文件；该 env 在**容器 create 时固化** ⇒ 一次重建才能录 |

⇒ 想拿「内核隔离吞吐」和「反量化占多少」，**下一次重启窗口顺手录一份 dump**（`STRATA_QSA_DUMP=/data/qsa.dump`，`STRATA_QSA_DUMP_LAST=4096`），之后 `pa_bench` 可零停机反复跑。

---

## 7 对账本与方案的影响

1. **R46 改靶**：`packed fp16` → **`先修效率、后换精度`**；判据从「19.2%→9.6%」改为「先测出反量化占比；若反量化 ≤ 40% VALU，则效率路线优先，目标 attn ≤ 8.6%（省 13%）」。
2. **`W875` 的「48 层 × 45 节点」需要限定**：图节点是**全部 48 层**（含 36 层 GDN 与 MoE），只有 **12 层**跑 QSA。
3. **`W793` 的定性再修正一次**：上一轮我把「整段 prompt 用 decode 核跑」改成「跑 FP32 核」；这一轮补上**量的部分**——FP32 核只跑到峰值的 11–16%，所以「结构性缺口」这个说法真正错在**把硬件上限当成实现上限**。

## 复算命令

```bash
# 元数据
docker cp ~/strata166/ci/gguf_meta.py strata166-407:/tmp/
docker exec strata166-407 python3 /tmp/gguf_meta.py <gguf>

# 相位表（三个长度档）
docker exec strata166-407 bash -lc 'grep -a "prefill timing: 99382 tokens" /data/strata-huihui-ud-iq4_xs.log | tail -1 | fold -w 150'
# 有效算力：fl = 4*24*256*cells*12*n ；cells = min(n,2048)/2 (n<2048) else 2048
```
