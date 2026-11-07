# W956 · R90-S3 第一遍：0.8.0 的 MMQ API 差异，与 28 处适配（分支 `exp/R90-080`）

- 日期：2026-11-04 17:3x–18:0x
- 前置：`W955`（S1/S2 通过；0.8.0 的 q4_k/q5_1 实例 24 s 编过）
- 一句话：**全量构建在 `moe_mmq.cu` 停下，三类 API 差异；做完机械适配后该文件单编通过。**
  改动只在实验分支 `exp/R90-080`，部署分支与生产一行未动。

---

## 1 全量构建停在哪（0.8.0 + 未适配的树）

`ninja strata` → **109/159 失败**，错误全部集中在 `src/prefill/moe_mmq.cu`：

```
error: no matching function for call to 'ggml_cuda_mmq_get_config'
  note: candidate requires 5 arguments, but 4 were provided
        ggml_cuda_mmq_get_config(const ggml_type type, const int J, const bool fallback,
                                 const int cc, const ggml_prec prec_src1)
error: non-constant-expression cannot be narrowed from 'int64_t' to 'int'
error: no matching function for call to 'mul_mat_q_case'
  note: candidate template ignored: couldn't infer template argument 'prec_src1'
        void mul_mat_q_case(ggml_backend_cuda_context & ctx, const mmq_args & args, cudaStream_t stream)
```

⇒ 上游 `#3217` 把 **`ggml_prec` 一路透传**进来，三个位置都多了一个"计算精度"参数。我们的
`cmake/strata_ggml_tq_overlay.cmake` 注释里其实早写过这件事（"llama.cpp from b11xxx on gives the MMQ helpers
a ggml_prec argument"），只是当时没落到我们自己的调用点上。

## 2 上游的约定：K-quant 一律 `GGML_PREC_Q8`

`ref/llama_b12099/ggml/src/ggml-cuda/mmq.cu` 自己的 dispatch：

```cpp
mul_mat_q_case<GGML_TYPE_Q4_0, GGML_PREC_Q8>(ctx, args, stream);
mul_mat_q_case<GGML_TYPE_Q5_1, GGML_PREC_Q8>(ctx, args, stream);
mul_mat_q_case<GGML_TYPE_Q2_K, GGML_PREC_Q8>(ctx, args, stream);
```

我们的激活本来就是 Q8_1（`x_qs`），与 `GGML_PREC_Q8` 对应，所以照抄，不自己发明第三档。

## 3 改了什么（脚本 `albus/w956/port_mmq081.py`）

| 文件 | 改动 | 处数 |
|---|---|---:|
| `src/prefill/moe_mmq.cu` | `mul_mat_q_case<T>(` → `<T, GGML_PREC_Q8>(` | 20 |
| `src/prefill/moe_mmq.cu` | `ggml_cuda_mmq_get_config(...)` 补第 5 参 | 4 |
| `src/prefill/moe_mmq.cu` | `mmq_args` 初始化里 `p.max_rows` → `(int) p.max_rows` | 1 |
| `src/prefill/mmq_kq_lib.cu` | 同上，模板参数 | 4 |
| `src/prefill/moe_mmq_tab.cuh` | `get_config` 补第 5 参（3 参的设备版也补） | 3 |

**不做**：`strata_w4a4_mul_mat_q_case`（我们自己的包装）不动——它的签名由我们控制，等 P3 再接。

## 4 结果：`moe_mmq.cu` 单编通过

```
[1/1] Building HIP object CMakeFiles/strata_mmq.dir/src/prefill/moe_mmq.cu.o
```

（构建目录 `build-080c`，`STRATA_GGML_DIR=/ref`，overlay **on**。）
⇒ 上一轮"0.8.0 换不动"的最大未知项（我们的 MoE 路径能不能接上新 API）**已经回答：能，三十几行改写**。

## 5 顺带修掉的"静默降级"（提交 `55a1acd4`，tag r30）

`cmake/strata_ggml_tq_overlay.cmake` 原来把锚点写死成 `GGML_TYPE_COUNT   = 43,`，0.8.0 里是 **44**
⇒ 打印一行 `trellis MMQ overlay off: anchor not found` 后 **configure 照样返回 0**。

- 锚点改成**按枚举名匹配**（`[ \\t]*GGML_TYPE_COUNT[ \\t]*=[ \\t]*[0-9]+,`），取上游的值；
- 真套不上时 **`FATAL_ERROR`**（除非显式 `-DSTRATA_TQ_OVERLAY_SOFT=ON`）；
- 验证：`-- trellis MMQ (Gyro prompts): overlay on the pinned ggml-cuda in /out/ggml-tq-overlay`（改前是 off）。

## 5.1 第二道坎：overlay 的 trellis 代码与 NVFP4 TU

修好锚点后 overlay 真的生效了，接着冒出两个新错误：

1. `src/prefill/mmq_nvfp4_w4a8.cu`（Blackwell sm_120 的 W4A8 路径，与我们 gfx906 无关）也调 `mul_mat_q_case`，
   补 `GGML_PREC_Q8` 即过；
2. 但它的报错把**overlay 生成的 trellis 代码**暴露出来：`ggml-tq-overlay/mmq.cuh:699/880/964` 的
   `ggml_cuda_mmq_util_funcs` 构造与 `get_util_funcs` 在 0.8.0 上也多了 `prec` 参数 ⇒ **overlay 的 trellis 段同样要再做一遍适配**。

**决定（并写清理由）**：R90 的 A/B 用 **`-DSTRATA_MMQ_TQ_OVERLAY=OFF` 显式关闭**，因为

- trellis（`TQ2_T/TQK6/TQK7/TQP5-7`）**不在我们的模型里**（专家是 Q4_K/Q5_1/Q8_0），
- 关掉是**显式**的（`W955` 加的 fail-hard 正好保证"要么生效、要么报错"，不会静默），
- 适配 trellis ctor 是独立的一小块，等真要跑 trellis 模型再做，不拖累主线。

⇒ **这条也回答了"0.8.0 迁移要改多少"**：我们的 MoE 路径 35 行；trellis overlay 另有一小块（未做，不影响本模型）。

## 7 复现

```bash
git -C ~/strata166/pr/strata-fork worktree add ~/strata166/work/r90-080 -b exp/R90-080 HEAD
python3 albus/w956/port_mmq081.py ~/strata166/work/r90-080
# configure（overlay 现在会真的生效）
cmake /src -G Ninja -DSTRATA_GGML_DIR=/ref -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
      -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_MMQ_TQ_OVERLAY=ON -DSTRATA_MMQ_TAB=OFF -DCMAKE_HIP_ARCHITECTURES=gfx906
ninja CMakeFiles/strata_mmq.dir/src/prefill/moe_mmq.cu.o
```

## 8 S3 结果：全量链接成功

```
[22/24] Linking HIP static library libstrata_mmq.a
[23/24] Linking HIP static library libstrata_prefill.a
[24/24] Linking HIP executable strata
0 error
-rwxr-xr-x 39599200  build-080c/strata
```

冒烟：

```
$ ./strata --version        -> strata 0.1.56        (RC=0)
$ ./strata serve --help     -> 286 行，RC=0
```

⇒ **0.8.0 上能产出完整引擎**。改动规模（`git diff --stat`）：**6 个文件、+35 / −35 行（零净增）**。

| 文件 | 改动 | 处数 |
|---|---|---:|
| `src/prefill/moe_mmq.cu` | `mul_mat_q_case<T>` → `<T, GGML_PREC_Q8>`；`get_config` 补第 5 参；`max_rows` 窄化 | 25 |
| `src/prefill/mmq_kq_lib.cu` | 同上（模板） | 4 |
| `src/prefill/moe_mmq_tab.cuh` | `get_config` 补第 5 参 | 3 |
| `src/prefill/ggml_cuda_host.cu` | `new_pool_for_device(ctx, dev, stream)` —— 0.8.0 把它改成三参静态成员 | 1 |
| `src/prefill/mmq_nvfp4_w4a{8,4}.cu` | 模板参数（Blackwell 路径，与 gfx906 无关但要编过） | 2 |

**没做**：overlay 的 trellis 段适配（见 §5.1），本轮 A/B 用 `-DSTRATA_MMQ_TQ_OVERLAY=OFF` 显式关闭。

## 9 下一步：S4 的两道门（还没跑）

> **【W958 更正 2026-11-04 19:2x】本节的判据①作废。** 同二进制重复跑：**A1 vs A2 只有 7/64 个 token 相同**，
> 而 0.8.0 移植版两次跑 **64/64 相同** ⇒ 生产件自己就不复现（源码 `generate.cpp:12706`：专家换入换出落在哪个窗口
> 决定它用 CPU 还是 GPU 算，两者舍入不同）。验收改为：**性能六长度档 A/B + 质量对金标的 KL/top-1（先测地板）**，
> 见 `W958`。


1. **逐位**：同一 prompt，0.4.1 与 0.8.0 各跑一次首 token logits，比 **argmax 序列**（前 64 个贪心 token）。
   0.8.0 的 `mmq.cuh` 改了 585 行、fatbin +10.9%，**不保证逐位相同**——若不等，要先分清是"我们的 30 行适配"还是"上游算法变了"。
2. **A/B**：六长度档（2K/8K/16K/32K/64K/130K）、`0 reused`、`|Δ| ≥ 2×CV`；decode 只守不劣化。
   停服约 4 分 20 秒 + 每档 2-3 次，预计 **40–60 分钟**。
3. 回滚：`STRATA_GGML_DIR` 指回 `~/strata166/llama.cpp`，生产二进制与 config 全程未动。
