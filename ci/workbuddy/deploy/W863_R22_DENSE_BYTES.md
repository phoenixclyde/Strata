# W863 · R22 重算：decode 每步真正的 dense Q8_0 字节（AUDIT17 P0-1 结案）

> 2026-11-01 14:2x–15:0x CST。**零干扰**：全程只读 GGUF 头 + 只读生产日志 + 只跑微基准；
> 生产进程、源码树、镜像、配置一字未动（VRAM 33,470,955,520 B 运行前后完全一致）。
> 数字标注：`[实测]` 本次测到 / `[源码]` 读源码确认 / `[推导]` 由前两者算术得到。

---

## 0 结论

1. **每层不是 9 个矩阵**。真实组成：**GDN 层 6 个张量 63.42 MiB / QSA 层 7 个张量 55.45 MiB**（全 Q8_0）。
   bench 用的「9 个矩阵 = 106.54 MB/层」比真实层**多 60%（GDN）/ 83%（QSA）**。`[实测]`
2. **枚举结果与引擎自己的日志逐字节对上**：301 native + 194 HC Q8 + 4 scratch = **499 矩阵**、
   **2975.00 + 644.14 = 3619.14 MiB**，与 `native projection matrices, 499 ... 3619.14 MiB` 完全一致。`[实测]`
3. **每步真正的 dense Q8_0 读 = 4263.24 MiB（4.47 GB）**，其中 **LM head 644.10 MiB 两轮都漏了**
   （它是 native head，在 VRAM，每窗口都读一遍）。`[实测]`
4. **占时 37.8%**（相位表 16.99 ms / 44.98 ms）。既不是 W861 的 59%，也不是 W862 的 16%。`[实测+推导]`
5. AUDIT17 P0-1 三条反证全部核实：36+12 成立；HC Q8_0 = 644.14 MiB = 0.629 GiB（日志 0.63 GiB）成立；
   **embedding 那条要改写**——它在 host 是事实，但**每 token 只 gather 一行 2720 B**，不是 644 MiB。

## 1 真实张量表（GGUF 逐张量枚举，非假设）

判据来源：`src/core/native_dense.cpp:140-152`（`eligible()` 的 10 个后缀）与 `:71-77`（`hc_q8_name()`）。
枚举脚本 `albus/w863/r22_enum.py`（读 4 个分片的 tensor table，按 ggml 类型表算字节）。

| 张量 | 层数 | 每层 | 合计 | 类型 |
|---|---:|---:|---:|---|
| `attn_qkv` 2560→10240 | 36 | 26.56 MiB | 956.25 MiB | Q8_0 |
| `attn_gate` 2560→6144 | 36 | 15.94 | 573.75 | Q8_0 |
| `ssm_out` 6144→2560 | 36 | 15.94 | 573.75 | Q8_0 |
| `attn_q` 2560→12288 | 12 | 31.88 | 382.50 | Q8_0 |
| `attn_output` 6144→2560 | 12 | 15.94 | 191.25 | Q8_0 |
| `ffn_gate_shexp` 2560→640 | 48 | 1.66 | 79.69 | Q8_0 |
| `ffn_up_shexp` 2560→640 | 48 | 1.66 | 79.69 | Q8_0 |
| `ffn_down_shexp` 640→2560 | 48 | 1.66 | 79.69 | Q8_0 |
| `attn_k` 2560→512 | 12 | 1.33 | 15.94 | Q8_0 |
| `attn_v` 2560→512 | 12 | 1.33 | 15.94 | Q8_0 |
| **小计（300 矩阵）** | | | **2948.44 MiB** | 全 Q8_0 |
| `blk.1.ple_key` 2560→10240 | 1 | 26.56 | 26.56 | Q8_0 |
| **native 合计（301 矩阵）** | | | **2975.00 MiB** | |

- **GDN 层 = 6 个张量、63.42 MiB/层 × 36 = 2283.05 MiB**
- **QSA 层 = 7 个张量、55.45 MiB/层 × 12 = 665.39 MiB**
- 层类别由张量名机械判定（有 `ssm_out` ⇒ GDN），结果 **36 / 12**，与 `full_attention_interval=4` 一致。`[实测]`

### 1.1 与引擎日志对账（这一条决定数字可不可信）

生产日志（最后一次启动，`81409-81412`）：

```
native pack: ... token embedding Q8_0 in mapped host memory (644 MiB, 1.9 s)
216 MiB of weights loaded from /data/packs/ud-q4_k_xl (495 canonical tensors skipped: served natively)
STRATA_HC_Q8=1: 0.63 GiB of Q8_0 hyper-connection projections for the verify read
499 native projection matrices, 3619.14 MiB of weights, in 9.0 s
```

`[源码]` `native_dense.cpp:494` 是 `bytes_ = total + hc_q8_bytes`，`tensor_count()` 是 `weights_.size() - packed_keys_.size()`。

| 项 | 数 | 字节 |
|---|---:|---:|
| native 等价集（含 ple_key） | 301 | 2975.00 MiB |
| HC Q8_0（48×4 + output 2） | 194 | 644.14 MiB |
| HC F32 inject（`STRATA_HC_Q8_INJECT` 未开，不走 Q8） | 96 | 15.00 MiB（不计入） |
| `weights_` 里的 dequant scratch（2 类 × 2 槽） | 4 | 0 |
| **合计** | **499** | **3619.14 MiB** ✔ |

⇒ 矩阵数与字节数**两项同时吻合**，枚举可信。差额逐年查清：3619.14 − 2975.00 = 644.14（HC 的全部）。

## 2 每步真正读多少（含两轮都漏掉的 head）

| 项 | 字节 | 位置 | 每步读 | 依据 |
|---|---:|---|---|---|
| native dense Q8_0（301） | 2975.00 MiB | VRAM（`cudaMalloc` + 拷贝） | 全部 | `native_dense.cpp:353-356` `[源码]` |
| HC Q8_0（194） | 644.14 MiB | VRAM（同上） | 全部 | `native_dense.cpp:401-408` `[源码]`；日志写明 "for the verify read" |
| **LM head `output.weight`** | **644.10 MiB** | **VRAM（native head）** | **全部** | 见 §2.1 |
| `token_embd` Q8_0 | 644.10 MiB | **pinned host（mapped）** | **每 token 一行 = 2720 B** | `native_head.cpp:208-213` gather `[源码]` |
| **每窗口合计** | **4263.24 MiB（4.47 GB）** | | | |

### 2.1 head 为什么算进来（两轮都漏）

- `[源码]` `generate.cpp:3085`：`if (o.native_head_gguf.empty()) o.native_head_gguf = o.native_preset;`
  ⇒ 只要给了 `--native`，**native head 默认开启**，不需要写 `--native-head-gguf`。
  生产 args 里正有 `--native .../Q8_K_XL-00001-of-00004.gguf`。
- `[实测]` 日志每次启动都有：`experimental native Q5_K head, 675430400 bytes, in 1.5 s`
  （675 430 400 B = 644.10 MiB = 248320×2560 Q8_0 的精确字节数；"Q5_K" 是没更新的横幅文字）。
- `[源码]` `verify.cpp:2213-2221`：head 在**每个窗口**用 `T` 列算一遍，**不是 1 列**。
- `[实测]` 相位表里 `head` 是独立一项：**1.73 ms/窗口**（675.4 MB / 1.73 ms = 390 GB/s）。

## 3 占时占比（相位表实测，100 窗口）

取自日志同级最新一条完整相位（`36311`，`total 44.98 ms/window over 100 windows`）：

| 块 | 项 | ms/窗口 | 说明 |
|---|---|---:|---|
| native dense | GDN `q8+qkv/q-idx gemv` 2.44 + `out-proj` 1.62 + `shared+quant` 1.54 | 5.60 | 含激活 q8_1 量化 |
| native dense | QSA `q+q-idx` 1.67 + `out-proj` 0.60 + `shared+quant` 0.50 | 2.77 | 同上 |
| HC Q8_0 | `hc0/hc1 down+up`（GDN 5.15 + QSA 1.74） | 6.89 | 2 组 × down/up |
| head | `head` | 1.73 | |
| **dense 合计** | | **16.99** | **37.8%** |
| | 其余（专家 VRAM hits / wait / router / GDN / attention …） | 27.99 | 62.2% |

- `[推导]` 有效带宽 **4263.24 MiB / 16.99 ms = 263 GB/s = 711 的 37%**。
  与微基准（ncols=2 大矩阵 408 GB/s、小矩阵 100–130 GB/s）自洽：大头贴带宽，小矩阵受限。

## 4 除数必须写明（本轮新纪律的第一次执行）

| 口径 | 除数 | 字节 | 说明 |
|---|---|---:|---|
| 每**窗口**（一次权重读） | ÷1 | **4263.24 MiB** | 一次 verify 窗口 = 一次全量 dense 权重读 |
| 每**接受 token** | ÷**1.79**（实测 tokens/窗口） | **2382 MiB/token** | 44.98 ms ÷ 25.2 ms/token = 1.79 |
| 每**列** | ÷**2.26**（实测平均 T） | **1886 MiB/列** | |

**这就是 AUDIT17 P0-1 的病根**：W861 除 2.36、W862 除 6，两边都没说除的是哪一个，差 2.54 倍。

## 5 顺带查出的事（改变 R23 判断，详见 `W863_WAVE_ROWS_TABLE.md`）

生产**典型验证窗口是 T≈2，不是 6**。三条独立证据：

1. `[实测]` 相位表 GDN `q8+qkv` 2.44 ms / 36 层 = **67.8 µs/层**；
   真实 kernel 微基准 qkv：n1 **58.4**、n2 **69.3**、n6 **153.8** µs ⇒ 落在 **n≈2**。
2. `[实测]` 单请求 64 tok：`drafts accepted 33 of 39`，生成 64 = 33 接受 + **31 窗口**
   ⇒ **1.26 draft/窗口**。
3. `[实测]` 全量请求：4480 tok、`drafts 1646/2746` ⇒ 窗口 = 4480 − 1646 = 2834 ⇒ **0.97 draft/窗口**。

`[源码]` 原因：`generate.cpp:13992-13994`
`while (T < S_mtp && ... && pr[from + T - 1] >= req_spec_min_p) ++T;`
⇒ 草稿链在「下一 token 概率 < `--spec-min-p`（生产 0.70）」处**截断**，所以窗口基本停在 2 列。

**这不影响 R22 的数字**（R22 用字节 × 实测相位），但它把 R23 的收益从「1.52×」拉到「约 2.8% 墙钟」。

## 6 与 AUDIT17 P0-1 三条反证的逐条核对

| AUDIT17 反证 | 本次核实 | 判 |
|---|---|---|
| 每层不是 9 个矩阵，36 GDN + 12 QSA | GDN 6 张量 63.42 MiB、QSA 7 张量 55.45 MiB；36/12 由张量名机械判定 | **成立**，且给出了准确形状 |
| HC 的 Q8_0 日志是 0.63 GiB，bench 只算了 0.33 GB | 644.14 MiB = 0.629 GiB；bench 假设 6.96 MB/层×48 = 334 MB | **成立**，且 HC 是 194 个矩阵不是 96 |
| embedding 644 MiB 在 host，每 token 读不读没查 | 在 host 属实（`cudaHostAlloc` mapped），但用法是 **gather 行**：2720 B/token | **结论要改写**：不构成每 token 的 644 MiB |
| （新增）head | **两轮都没算**：644.10 MiB，每窗口读满，1.73 ms | 新增 P0 级遗漏 |

## 7 复现

```bash
python albus/push_file.py albus/w863/r22_enum.py /home/albus/strata166/w863/r22_enum.py 755   # 需 MSYS_NO_PATHCONV=1
python albus/rs.py albus/w863/s6_run.sh 220     # 打印 §1 的表
python albus/rs.py albus/w863/s8_phase.sh 120   # 打印 §3 的相位表（取日志里最新一条完整窗口）
```

产物：`albus/w863/r22_enum.py`（枚举）、`r22_recon.py`（对账）、`s5_pack2.sh`/`s7_startup.sh`/`s8_phase.sh`（取日志）。
