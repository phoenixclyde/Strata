
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

⇒ **0.8.0 上能产出完整引擎**。改动总计 **30 行**：28 处 MMQ 精度参数 + `new_pool_for_device` 签名 + 两个 NVFP4 TU 的模板参数。

| 文件 | 改动 | 处数 |
|---|---|---:|
| `src/prefill/moe_mmq.cu` | `mul_mat_q_case<T>` → `<T, GGML_PREC_Q8>`；`get_config` 补第 5 参；`max_rows` 窄化 | 25 |
| `src/prefill/mmq_kq_lib.cu` | 同上（模板） | 4 |
| `src/prefill/moe_mmq_tab.cuh` | `get_config` 补第 5 参 | 3 |
| `src/prefill/ggml_cuda_host.cu` | `new_pool_for_device(ctx, dev, stream)` —— 0.8.0 把它改成三参静态成员 | 1 |
| `src/prefill/mmq_nvfp4_w4a{8,4}.cu` | 模板参数（Blackwell 路径，与 gfx906 无关但要编过） | 2 |

**没做**：overlay 的 trellis 段适配（见 §5.1），本轮 A/B 用 `-DSTRATA_MMQ_TQ_OVERLAY=OFF` 显式关闭。

## 9 下一步：S4 的两道门（还没跑）

1. **逐位**：同一 prompt，0.4.1 与 0.8.0 各跑一次首 token logits，比 **argmax 序列**（前 64 个贪心 token）。
   0.8.0 的 `mmq.cuh` 改了 585 行、fatbin +10.9%，**不保证逐位相同**——若不等，要先分清是"我们的 30 行适配"还是"上游算法变了"。
2. **A/B**：六长度档（2K/8K/16K/32K/64K/130K）、`0 reused`、`|Δ| ≥ 2×CV`；decode 只守不劣化。
   停服约 4 分 20 秒 + 每档 2-3 次，预计 **40–60 分钟**。
3. 回滚：`STRATA_GGML_DIR` 指回 `~/strata166/llama.cpp`，生产二进制与 config 全程未动。
