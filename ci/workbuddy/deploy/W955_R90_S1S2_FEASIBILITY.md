# W955 · R90-S1/S2：0.8.0 的可行性（已编通，未上线）

- 日期：2026-11-04 17:1x–17:3x
- 前置：`W953`（我们 = 0.4.1 / `e6ab7c1a4`；上游 `b12099` = 0.8.0）、`W954`（R90 升为队列第一位）
- 结论：**S1 完成、S2 通过**（0.8.0 的 `ggml-cuda` 能用我们的 flag 编出 q4_k / q5_1 的 MMQ 实例，24 秒），
  但生成代码**确实变了**，性能未知 ⇒ S3/S4 仍需做，**生产一行没动**。

---

## 1 S1：把 0.8.0 的树拿到手（零风险）

```bash
git clone --depth 1 --filter=blob:none --no-checkout https://gh-proxy.com/https://github.com/ggml-org/llama.cpp ref/llama_b12099
git sparse-checkout set ggml && git checkout        # 只取 ggml/，28 MB
```

| 项 | 值 |
|---|---|
| `ggml/src/ggml-cuda/` 文件数 | 我们 **161** → 0.8.0 **168** |
| 新增（8） | `batch-get.{cu,cuh}`、`conv3d.{cu,cuh}`、**`gated-delta-net-mma.{cu,cuh}`**、**`top-k-mask.{cu,cuh}`** |
| 删除（1） | `fattn-swizzle.cuh` |
| `ggml/CMakeLists.txt` 的 `GGML_VERSION` | 我们 **0.24.0** → 0.8.0 **0.28.0** |

两条与我们直接相关：**`gated-delta-net-mma`**（GDN 占我们 prefill 12.7%）是新增的 MMA 路径；
**`top-k-mask`** 与 attention 的 mask 有关（`R46/R64` 的地盘）。两者都值得在 S3 之后单独读。

## 2 关键：`mmq-config-gcn.cuh` 逐字节相同

```
mmq-config-gcn.cuh   0.4.1=281 行   0.8.0=281 行   diff = 0
```

⇒ **`#27841` 的 GCN tile 表这 4 个 minor 里没动**。所以 `R60`（stream-k）/`R63`（内层）那批
"tile 层面无空间"的结论**不因升级而失效**，升级不会顺手把 MMQ 变快——这一点必须先说清，免得 S4 期待错。

## 3 mirror 钩子全部还在（S3 的前提）

| 符号 | 0.4.1 | 0.8.0 |
|---|---:|---:|
| `mul_mat_q_process_tile` | 4 | **4** |
| `DECL_MMQ_CASE` | 23 | **26**（新增 3 个类型） |
| `ggml_cuda_mmq_load_tiles_q5_1` | 3 | **3** |
| `vec_dot_q4_K_q8_1_impl_mmq` | 1 | **1** |

文本改动规模：`mmq.cuh` **585 行**、`mmq-load-tiles.cuh` **322**、`mmq-vec-dot.cuh` **93**、`vecdotq.cuh` **189**。
⇒ 我们 `R86`（Q5_1 loader）与 `R91`（`vec_dot`）要改的两个函数都还在原位，**但行号全变了**。

## 4 S2：configure 成功，但 overlay **静默关闭**

```bash
cmake /src -G Ninja -DSTRATA_GGML_DIR=/ref ... -DSTRATA_MMQ_TAB=OFF -DSTRATA_PREFILL_MMQ=OFF
# CFG_RC=0
# -- ggml version: 0.28.0
# -- trellis MMQ overlay off: anchor not found:         GGML_TYPE_COUNT   = 43,
```

`cmake/strata_ggml_tq_overlay.cmake` 有 7 个锚点，第一个是 `ggml.h` 的 `GGML_TYPE_COUNT = 43,`。
0.8.0 里这个枚举已经是 **44**（新增了类型）⇒ 锚点不命中 ⇒ **脚本打印一行就整体跳过**。

**这件事的危险不在"失败"，在于"静默降级"**：configure 返回 0，构建照常进行，只是少了 trellis 的
MMQ 实例（`TQ2_T/TQK6/TQK7`）。我们的专家是 Q4_K/Q5_1/Q8_0，**不用 trellis** ⇒ 对当前模型无害；
但任何人看到"配置成功"都会以为 overlay 生效了。**修法二选一**（S3 里做）：

1. 把锚点改成 `GGML_TYPE_COUNT   = 44,`（脆弱，下次还会断）；
2. 改成从枚举里**抓最后一个 `GGML_TYPE_*` 再 +1**（稳，但要改脚本逻辑）。

推荐 2，并给 overlay 加一条硬失败：`STRATA_MMQ_TQ_OVERLAY=ON` 且锚点不命中时**直接 FATAL_ERROR**，
不要静默——这条正好是 `AUDIT24` 里"静默降级"的同一类缺陷（`W949` 的 lint、`W832` 的破表都是这个形态）。

## 5 编译：两个关键实例 24 秒通过

```
[1/2] Building HIP object ... mmq-instance-q5_1.cu.o
[2/2] Building HIP object ... mmq-instance-q4_k.cu.o
real 0m24.089s
```

| 对象 | 0.4.1 | 0.8.0 | 差 |
|---|---:|---:|---:|
| `mmq-instance-q4_k.cu.o` | 973,544 B | **1,128,104 B** | **+15.9%** |
| 其中 `.hip_fatbin` | 701,280 B | **777,960 B** | **+10.9%** |

⇒ **机器码不一样**（fatbin md5 也不同）。所以"升级会不会让 prefill 变快"**只能靠 A/B 回答**，
不能因为"编过了"就假设等价。

## 6 本轮结论与下一步

| 阶段 | 状态 |
|---|---|
| S1 下载 / 清单 / 版本 | **DONE**（本节 §1–3） |
| S2 configure + 关键 TU 编通 | **DONE**（§4–5，configure 0，两 TU 24 s） |
| S3 修 overlay 锚点 + 重建 mirror + 逐位测试 | **未做**（下一步） |
| S4 全量构建 + 上线 A/B（六长度档） | **未做**；回滚 = `STRATA_GGML_DIR` 指回旧树 |

**给 S3 的判据（先写死，免得又"编过就算过"）**：
① overlay 在 0.8.0 上**必须**打印 "applied N/N edits"（不许静默 off）；
② 逐位测试：同 prompt 贪心前 64 token 的 argmax 序列与 0.4.1 相同（不比文本哈希）；
③ 六长度档 `0 reused`，`|Δ| ≥ 2×CV` 才算升级有/无影响；
④ 若 decode 劣化 >2×CV，直接回滚，不解释。

## 7 复现

```bash
# S1
git -C ~/strata166/ref/llama_b12099 sparse-checkout list      # ggml
# S2
cd ~/strata166/build-080 && cmake --version >/dev/null && grep -c "trellis MMQ overlay off" /tmp/cfg.log   # 1 -> 需要修
docker run --rm -v $PWD:/out -w /out strata-gfx906:0.2.10-101 ninja -j4 \
  CMakeFiles/strata_mmq.dir/ref/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o
```

## 8 顺手修掉的账本不一致（`AUDIT24` 遗留 P1）

`ci/config.sh` 一直指着 **gfx029-build / 0.2.9-101**，而生产早已是 **build-r28 / 0.2.10-101**（`W938` 改了流程没改它）。
⇒ 任何人跑 `ci/strata-ci build` 都会拿错 ninja 树与镜像。本轮已改并落库：

- 改动：`BUILD=/home/albus/strata166/build-r28`、`IMG=strata-gfx906:0.2.10-101`
- 提交 **`03381d82`**，tag **`mi50-0.2.10-r29`**（末条 tag == HEAD，满足 `R80` 的 provenance）
- 主线状态随之变成 **落后 0 / 领先 38**（原 37）
