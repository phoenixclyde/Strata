# W961 · 0.4.1 → 0.8.0：版本地图与源码分析（全部实查，不靠印象）

- 日期：2026-11-04 19:4x–20:1x
- 触发：机主「去 llama.cpp 找我们使用的上一个版本之后所有的 release 信息，以及所有相关信息，做源码分析」
- 方法：GitHub API 取 `CMakeLists.txt` 的版本 bump 提交 → 锁定四个 minor 的边界；再按文件取提交历史（`mmq.cuh`、`gated_delta_net.cu`）；
  关键结论都落到**具体 commit 的源码**上，能用 diff 证的就用 diff 证。

---

## 1 版本地图（四个 minor，全部实查）

| 版本 | bump commit | 日期 | PR |
|---|---|---|---|
| **0.4.1（我们）** | `e6ab7c1a4` | **2026-09-22** | — |
| 0.5.0 | `7fe450e` | 2026-09-23 | #29333 |
| 0.6.0 | `d812350` | 2026-10-05 | #29997 |
| 0.7.0 | `620d222` | 2026-10-15 | #30603 |
| 0.8.0 | `8642541` | 2026-10-28 | #31309（`b12099` = 11-04 发布） |

注意 **0.5.0 只比我们晚一天**：我们不是"落后一个版本"，是**几乎正好停在 0.4.1 的末态**，之后四个月（09-23 → 11-04）一条没吃。

## 2 MMQ 这条线：我们之后一共 8 个提交

| 日期 | commit | 标题 | 对我们的影响 |
|---|---|---|---|
| 09-25 | `e9f824d8` | llama : add `llama_prec_policy` + model-driven W4A4 (#24364) | `ggml_prec` 从这里进来（我们移植要补的参数源头） |
| 10-08 | `fc9ce6b9` | **CUDA: fix MMQ out-of-bounds reads (#29953)** | **正确性修复，我们没有**（见 §5） |
| 10-09 | `8a1a9b51` | CUDA: pass src1 precision to host MMQ config helpers (#30168) | 我们 7 处 `get_config` 补参的直接原因 |
| 10-13 | `882d6716` | cuda : fix warnings from dead breaks (#30441) | 无 |
| 10-19 | `4c1004c4` | cuda: cap MMQ Stream-K blocks at available work (#30553) | 只动 stream-k；**我们的表不走 stream-k**（R60 已判否） |
| 10-23 | `1a24df16` | Enforce DP4A MMQ tile height multiple of warp size (#30837) | 只加 `static_assert`，顺手给了我们一条判据 |
| 10-25 | `c49edf09` | **CUDA: fuse FFN gate/up matmuls and GLU in MMQ (#29948)** | **0.8.0 的 `mmq.cuh` 就是它**（见 §4），−6% 头号嫌疑 |
| 10-29 | `eb4e244b` | ROCm/HIP: add RDNA4_M family (#31373) | 只影响 gfx117x |

## 3 三条怀疑，用源码排除（不是排除"感觉"）

| 怀疑 | 结论 | 依据 |
|---|---|---|
| **GDN MMA（新增 `gated-delta-net-mma`）拖慢我们** | **排除** | `select_gdn_mma_path()` 在 `#ifdef GGML_USE_HIP` 下要求 `GGML_CUDA_CC_IS_RDNA3_5(cc)` 且 `n_tokens ≥ 2048` ⇒ gfx906 直接 `return gdn_path::ar`（老路径） |
| RDNA4_M 新架构代码 | 排除 | 只在 `CC_IS_RDNA4` 分支 |
| MUSA 的 `__CUDA_ARCH__` | 排除 | MUSA 专用 |

**但 GDN 还有一个通用改动**：`24e41838`（10-08）"assign four GDN state columns per warp (#30087)"，把 `cols_per_warp` 默认改成 4。
这条**对 HIP 生效**，而 GDN 占我们 prefill 12.7% ⇒ 计入 −6% 的候选（排第三）。

## 4 硬证据：0.8.0 的 `mmq.cuh` 等于 fusion 那一次提交

```
a55c16e4 (fusion 的父)   74,111 B  1588 行
c49edf09 (fusion)        79,374 B  1659 行   <- diff 283 行
8642541  (0.8.0)         79,374 B  1659 行   <- 与 c49edf09 逐字节相同（diff 0）
```

⇒ 0.8.0 的 MMQ 内核**就停在 10-25 的 fusion 版本**，之后（10-29 的 RDNA4）没再动 `mmq.cuh`。
所以"0.8.0 比 0.4.1 慢 6%"只能来自 10-25 之前那一串，**fusion 是最大的一次重写**（283 行）。
它自述"The MMA loop is unchanged: same tile, warp layout, vec_dot and one `sum[]` per thread"，但**loader 的签名与数据交错方式全变了**
（`mmq-load-tiles.cuh` 322 行差异）——非 fused 路径是否等价，需要实测，不能看注释。

## 5 该摘的一条：`#29953` 的越界读修复（**正确性，不是性能**）

patch 的两处关键（`ggml/src/ggml-cuda/mmq.cu`）：

```cpp
-    ggml_cuda_pool_alloc<int32_t> ids_dst(ctx.pool(), ne_get_rows);
+    ggml_cuda_pool_alloc<int32_t> ids_dst(ctx.pool(), ne_get_rows + J_best-1); // padded for unconditional access
...
-    const size_t nbytes_src1_q8_1 = ... + ggml_cuda_mmq_get_J_max(...) * sizeof(block_q8_1_mmq);
+    const size_t src1_load_chunk_size = nthreads_best * sizeof(int);
+    const size_t src1_q8_1_padding = ((J_best*sizeof(block_q8_1_mmq) + src1_load_chunk_size - 1) / src1_load_chunk_size) * src1_load_chunk_size;
+    const size_t nbytes_src1_q8_1 = ... + src1_q8_1_padding;
```

意思是：**一个 J 宽度的 tile 会多读最多 J-1 列**，以前靠 `get_J_max()` 的余量撞运气，现在按 `nthreads*sizeof(int)` 向上取整显式补。

我们 0.4.1 **没有**这个修复。生产一直在跑，说明越界读落在 pool 的余量里（没有段错误），但这是**未定义行为**，
而且我们自己的 `moe_mmq.cu` 是直接调 `mul_mat_q_case`，`xq`/`ids` 的尾部余量得自己保证——
**下一步必须核对我们的分配是否有同样的 padding**（本轮只做到 grep 出分配点，没算完）。

## 6 −6% 的归因：【已定位】fusion `#29948`（见 `W962`）

候选排序（按改动规模 × 与我们的相关性）：

1. **fusion `#29948`**（283 行，改 loader 与写回）
2. `#30087` GDN `cols_per_warp=4`（GDN 占 12.7%，若要凑出 6% 总降幅，它自身得慢 ~47%）
3. `#30553` stream-k cap（我们不走 stream-k，概率低）

**bisect 设计**：0.7.0（`620d222`）已有 `J_best` + `prec`，但**没有 fusion**。
用同一棵树、同一套 35 行适配对 0.7.0 编译 → 一次 prefill 测量：

**结果（`W962`）**：0.7.0 = **594.11 tok/s**（A 599–604，B 552–577）⇒ C 与 B 差 **5.0%**、C 与 A 差 **1.3%**。
**⇒ 凶手是 fusion（`c49edf09`，10-25，283 行）：它拿走 ~5%，其余全部改动合计 ~1%。**

（0.7.0 的 `ggml` 版本 = 0.27.0，`J_best` 出现 3 次，已实查。）

## 7 结论与建议

1. **不整树升级**（`W960` 的 −6% 已站住）；`R90` 保持"参考实现/按需摘取"。
2. **摘 `#29953` 的 padding 修复到 0.4.1** —— 这是正确性问题，不是性能问题，且改动小（两处分配 + 一个 padding 计算）。
   摘之前先核我们自己的 `moe_mmq` 是否有同样的隐患。
3. 若 0.7.0 bisect 证明"fusion 之前的 0.8.0 更快"，则折中方案是 **0.7.0 + 我们的补丁**（但六长度档 A/B 仍要做）。
4. 记住一条时间线：我们停在 0.4.1（09-22），**0.5.0 只晚一天**——"落后 4 个 minor"实质是"落后四个月的 4 个版本"，
   而不是"落后 4 个语义大版本"。

## 8 复现（全部可重跑）

```bash
# 版本 bump 提交
curl -s "https://api.github.com/repos/ggml-org/llama.cpp/commits?path=CMakeLists.txt&since=2026-09-20" | grep -E '"message"|"sha"' | head -40
# MMQ 提交历史
curl -s "https://api.github.com/repos/ggml-org/llama.cpp/commits?path=ggml/src/ggml-cuda/mmq.cuh&since=2026-09-20"
# 0.8.0 的 mmq.cuh == fusion
for t in a55c16e4 c49edf09 8642541; do curl -sL -o /tmp/m_$t.cuh https://raw.githubusercontent.com/ggml-org/llama.cpp/$t/ggml/src/ggml-cuda/mmq.cuh; done
diff /tmp/m_c49edf09.cuh /tmp/m_8642541.cuh | wc -l     # 0
```
