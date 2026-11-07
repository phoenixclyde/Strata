# W754 · W2 非专家张量精度核查（只读，零发车）

日期 2026-10-10 02:1x ｜ 引擎 0.1.41 ｜ pack `huihui-ud-iq4_xs`

**目的**：W750 §0.0 的 P0 第 1 项 -- 它是 routeK 的 T1 路线（"把未量化的 BF16 质量做 int8"）
在 Strata 上**成立与否的证伪器**。**结论：routeK T1 的直接前提在 Strata 上不成立，但查出了一个更具体的新目标。**

## 1 方法（列义先定死，再算账）

`index.txt` 是 pack 的**唯一权威张量表**（1079 行）。它的列义**不是猜的**，
取自解析它的源码 `src/core/weights.cpp`：

- `:136` 注释逐字：*"the first ten fields of the row `load` parses: name file kind src_off src_bytes dst_off dst_bytes ne0 ne1 code_bits"*
- `:168-173` 的 sscanf **19 字段**：`name file kind src_off src_bytes dst_off dst_bytes ne0 ne1
  code_bits code_bias group_elems codebook has_offset codes_bytes scales_bytes offset_bytes scales_fp16 act_kind`
- `:184-187` 的 kind 语义：**index kinds 4 (BF16) 与 5 (F16) 被拷贝并取引擎形态 1 与 3**；
  `tools/iq_pack.py:17` 逐字：*"dense.bin standalone: the BF16/F16/F32 tensors ... (index kinds 4/5/2)"*

-> `kind` 就是 `WeightKind`；`code_bits + group_elems` 是**原生编码**参数（8 + 32 = Q8_0 的形态）。

## 2 结果（1079 张量 / dst 合计 1416.78 MiB）

| kind | 含义 | 张量数 | dst 体量 | 备注 |
|---|---|---|---|---|
| **0** | Verbatim，**`bits=8 / group=32` = Q8_0** | **303** | **0.00 MiB** | **native 服务**（在 GGUF 里原生读，不进 dense.bin） |
| **4** | **BF16** | **483** | **1407.11 MiB** | 本次的主角 |
| 2 | F32 | 292 | 9.60 MiB | 小张量（norm 等） |
| 3 | F16InF32 | 1 | 0.08 MiB | `ple_conv1d`（源码 `:2925` 专门校验它） |

### 2.1 已经是 Q8_0 的（routeK T1 的原目标）

`Q8_0(native)` 里包含 **`output.weight`（lm_head）· `token_embd` · `attn_qkv` · `attn_gate` ·
`attn_q/k/v/output` · `ssm_out` · `ffn_{gate,up,down}_shexp` · `ple_key`**。

-> **routeK T1 的机会（"lm_head / FA qkv / GDN proj / shared expert 是未量化 BF16"）
在 Strata 上不存在** -- 它们**已经是 8-bit**。**T1 的直接前提被证伪。**

（顺带解掉一个旧疑点：Strata 启动日志那行 *"experimental native Q5_K head"* 不是 `output.weight` 的**存储**类型；
它在 index 里是 `kind=0 / bits=8 / group=32`。）

### 2.2 真正的 BF16 质量（1407 MiB）

| 名字（去层号） | 张量数 | 体量 | 占 BF16 |
|---|---|---|---|
| `blk.N.hc_attn_down.weight` | 48 | 300.00 MiB | 21.3% |
| `blk.N.hc_attn_up.weight` | 48 | 300.00 MiB | 21.3% |
| `blk.N.hc_ffn_down.weight` | 48 | 300.00 MiB | 21.3% |
| `blk.N.hc_ffn_up.weight` | 48 | 300.00 MiB | 21.3% |
| `blk.N.ffn_gate_inp.weight`（**路由门控**） | 48 | 120.00 MiB | 8.5% |
| `blk.N.indexer.q_proj.weight` | 12 | 30.00 MiB | 2.1% |
| `blk.N.ple_value.weight` | 1 | 12.50 MiB | 0.9% |
| `blk.N.ssm_alpha/beta.weight` | 36+36 | 8.44 + 8.44 MiB | 1.2% |
| `blk.N.indexer.k_proj.weight` | 12 | 7.50 MiB | 0.5% |
| `output_hc_down/up.weight` | 1+1 | 6.25 + 6.25 MiB | 0.9% |
| `blk.N.hc_attn/ffn_inject.weight` | 48+48 | 3.75 + 3.75 MiB | 0.5% |
| `blk.N.ffn_gate_inp_shexp.weight` | 48 | 0.23 MiB | 0.0% |

**-> 主项是 `hc_*`（hyper-connection）四类：4 类 x 48 层 x 6.25 MiB = 1200 MiB = BF16 的 85.3%**；
连同 `ffn_gate_inp`（120 MiB）合计 **1320 MiB = BF16 的 93.8%**。
（`output_hc_down.weight` 的 shape 是 `ne0=10240, ne1=320`，6,553,600 B = 6.25 MiB，与 dst_bytes 相符。）

## 3 判定

1. **B2 照搬 routeK T1：不成立。** 它假设的目标（lm_head / qkv / shexp）在 Strata 上**已是 Q8_0**；
   Q8_0 已 8-bit，**没有 byte-side 收益**（再 int8 化只是 8->8）。
2. **但查出一个新目标，比 T1 更聚焦**：`hc_*` 四类 + `ffn_gate_inp` = **1320 MiB BF16**，
   **每层都有、每步都参与**。
3. **收益路径与 routeK 不同，必须先验一道**：routeK 的 T1 赚的是 **HBM 地板**（它实测 lm_head 1.93x
   是因为那个形状**就在地板边界**）。而我们的 `hc_*` 是 **dense 常驻**（在 1.4 GB 的 `dense.bin` 里、
   已全量在 arena），所以它的收益取决于**是否 memory/bandwidth-bound**，**不能照搬 1.93x**。
   => 下一步应是 **ISA/roofline 级的前置探查**（W749 的 B3 逐桶账 + 反汇编），**不是直接发车**。

**-> 本项的净产出**：把 routeK 的一条路线**判掉一半**，并把剩下的那一半收敛到一个**具体的、可测的对象**上。

## 4 口径与局限

- 体量口径 = `index.txt` 的 **`dst_bytes`**（引擎 arena 里的字节）；`src_bytes` 合计同为 1384 MiB。
- `file` 列全为 0（1079 行）-- 本次**未**用它区分来源；来源由 `kind` 判别（native 的 dst=0）。
- 本报告**不含任何收益承诺**；1320 MiB 只是**候选规模**，不是收益。
- 只读：本波未改 pack、未改 config、未发车。

## 5 证据件

| 件 | 内容 |
|---|---|
| `deploy/tmp/_w754_index.txt` | pack 的 `index.txt` 逐字副本（93,559 B，1079 张量） |
| `deploy/tmp/_w754_w2{a,c,d}.py` | 取数与统计脚本 |
| 源码依据 | `src/core/weights.cpp:136`（列义注释）· `:168-173`（19 字段 sscanf）· `:184-187`（kind 4/5 语义）· `tools/iq_pack.py:17`（kinds 4/5/2 表） |
| pack 现场 | `/home/albus/strata166/data/packs/huihui-ud-iq4_xs/{index.txt,native_experts.txt,dense.bin}` |
