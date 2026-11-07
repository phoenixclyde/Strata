# W775delta W6 续 ---- `STRATA_ATTN_LANECELL` 源码级判定（`P41` §4 族**最后一个未测候选**）

> 触发：`W750 §4` 的 **W6 = `STRIX_HALO §4` 族其余开关**（15 -> 候选 13 -> R4 先排 3 个：已测 `Q8_PACKED` / `GDN_PP=2` 均 **exact but no gain**；余 **`ATTN_LANECELL`**）。
> 做法：**只读** 0.1.42 源码树（`deploy/tmp/src142/`，机主指点自 166 镜像 `/src` 归档）。时间 2026-10-11 19:3x。**0 发车、生产未动。**

## 0 结论（先行）

**`ATTN_LANECELL` 在本机生产配方（`--kv k8v4`，单卡 gfx906）下「可达 + 有动作 + 声明不改答案」，但「证据面为空」=> 按 `W17b` 判据（有可测杠杆才发车）判「不发车」，保留为可发车候选。**

要点四条：

1. **可达**：`lane_cell` 是**运行期 `getenv`**，**无 `#if` 守卫**（`qsa_decode_attn.cu:638`）=> 设 env 即生效，不需重编。
2. **有动作（且正好命中我们的 KV 形态）**：`if (lane_cell)` 分支按 `kv_mode` 选核（`:653-657`）；`kv_mode=3` 正是 `--kv k8v4` 的推定 mode（`:626`：`k_q` + `v_q4` => 3）=> 会走 `attn_chunk_kernel<3, **true**>`。
3. **声明零成本**：注释逐字 *"**bit-identical scores, no shuffle reductions**"*（`:637`）=> 声明**不改答案**（仍须 parity 门实测）。
4. **与 `P55` 的互斥在本机不成立**：`use_query_swizzle = query_swizzle && !lane_cell && kv_mode == 1 && ...`（`:643`）---- swizzle 还需 **`kv_mode == 1`（= `--kv int8`）**；我们 `k8v4` 下它本就恒假 => **`lane_cell` 关不掉任何本机可达路径**（`R4 §1.6` 的判断由此源码证实）。

## 1 源码依据（0.1.42，逐字 + 行号）

```cpp
// src/kernels/cuda/qsa_decode_attn.cu:626    （kv_mode 由 pool 布局推得）
const int kv_mode = pools.k_q4 != nullptr ? 2 : (pools.k_q != nullptr && pools.v_q4 != nullptr ? 3
                    : (pools.k_q != nullptr ? 1 : 0));
// :637
// S25: STRATA_ATTN_LANECELL=1 - the score phase one cell per thread (bit-identical scores, no shuffle reductions)
// :638
static const bool lane_cell = [] { const char* v = std::getenv("STRATA_ATTN_LANECELL"); return v && v[0] == '1'; }();
// :639-651  （仅 gfx906 块内的 swizzle；lane_cell 只作为 use_query_swizzle 的否定项出现）
const bool use_query_swizzle = query_swizzle && !lane_cell && kv_mode == 1 && query_swizzle_gfx906_device();
// :652-659
#define STRATA_ATTN_LC(M) attn_chunk_kernel<M, true><<<...>>>(...)
if (lane_cell) {
    if (kv_mode == 3) STRATA_ATTN_LC(3);
    else if (kv_mode == 2) STRATA_ATTN_LC(2);
    else if (kv_mode == 1) STRATA_ATTN_LC(1);
    else STRATA_ATTN_LC(0);
} else
```

- 自动开启面：`src/core/arch_defaults.cpp:49` = `{"STRATA_ATTN_LANECELL", "1"},   // decode attention scores, one cell per thread (S25)`
  ---- 该表**只在 gfx12 / gfx1151 返回**（`R4 §1.1`：`if (!gfx_arch_is_gfx1151(gcn_arch)) return t;`）=> **gfx906 空表，不会自动开**；须显式设 env。
- 落点**只有一处**（`grep -rn` 全树：`arch_defaults.cpp:49` / `qsa_decode_attn.cu:166,637,638,643,648,653` + 文档 1 处）=> **无第二处行为面**。

## 2 与本机形态逐条对照

| 对照项 | 本机形态 | `ATTN_LANECELL` 是否适用 |
|---|---|---|
| KV 形态 | `--kv k8v4` => `kv_mode=3`（`qsa_decode_attn.cu:626`） | **适用**（`:654` 走 `LC(3)`） |
| 卡 | gfx906（MI50 32GB） | **适用**（`:638` 无架构守卫） |
| 阶段 | decode 注意力 score phase | **适用**（decode 侧） |
| 与 `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | 我们**未设**该 env | 无冲突（swizzle 本就关） |
| 与 `P55`/`P56` | k8v4 下不可达（`W775delta_W12_BANNER.md`） | **互斥不成立**（见 §0 第 4 条） |
| 是否改答案 | 声明 bit-identical | 须 **parity 门**实测（本项目已固定做法） |

## 3 证据面（为什么判"不发车"）

1. **上游对该条无量化收益**：`arch_defaults.cpp:49` 的注释只有 `(S25)`（Aurora 流编号），**没有数字** ---- 对比同表 `Q8_PACKED` 写 "decode +2.3%"、`GDN_PP` 写 "64K prompt +2.9%"。=> 属 `W17b §1` 定义的**「证据面为空」**。
2. **同族实测记录为 0/2**：`Q8_PACKED`（exact but no gain、白吃 1.87 GiB）、`GDN_PP=2`（prefill **-0.13%**，在 0.4-0.8% spread 内）。
3. **我方"上游增益不迁移"总记录 0/4**（`W17B §4`：GDN_PP / Q8_PACKED / SH_STREAM / P59P60）。
4. **观测面偏弱**：它只动 decode score phase => 只能落 **decode `ms/step`** 轴，而该项目 spread 16-41%（`W17B §3`）=> 需 **5+ runs** 才有分辨力（成本高于其余车）。

## 4 处置建议

| 选项 | 内容 | 成本 |
|---|---|---|
| **建议（默认）** | **不发车**；`P41` **status 不动**（仍 CANDIDATE），verdict 追加本条判定。理由 = §3 四条（证据面为空 + 同族 0/2 + 不迁移 0/4 + 观测面弱） | 0 |
| 备选 | 若机主要"把 §4 族跑全"：单变量车（env 一键 `STRATA_ATTN_LANECELL=1`），ABBA x5，主口径 decode `ms/step`（n_q=1）+ parity 门 | 约 20 min 生产停机 + 恢复 |

**注**：`P41` 是**族级**条目（15 开关的集合），本轮把族内**最后一个未测项**判完 => **§4 族全部 3 个先测项均有结论**（2 实测 + 1 源码判定）。

## 5 复现

```bash
grep -rn "STRATA_ATTN_LANECELL\|lane_cell" deploy/tmp/src142/src deploy/tmp/src142/docs
sed -n '636,660p' deploy/tmp/src142/src/kernels/cuda/qsa_decode_attn.cu
sed -n '40,55p'   deploy/tmp/src142/src/core/arch_defaults.cpp
```

## 6 局限

- 本件**未发车**：结论限于「源码在性 + 运行期可及性 + 形态对照 + 证据面」。
- 「bit-identical」是**上游注释声明**，本机**未实测** => 若将来发车，parity 门不可省。
- `kv_mode=3` 是**由 pool 布局推定**（`qsa_decode_attn.cu:626`），与 `W775delta_W12_BANNER.md` 实测 `--kv k8v4 => kv_mode=3` 一致；但该推定在**其它采样点**未逐一验。
