# W775delta W17b / W23 续 ---- 短名单 36 条 + 候选逐条「证据筛」（结论：**不发车**）

> 触发：`W23` 收窄后剩下的候选（`P47` 的 `--mtp-draft-vocab`、`P48` 的三项）与 `W17b` 的"优先族试车序列"。
> 判据（`W27` 立 + 本轮补）：**(1) 读源码定机制 -> (2) 与本机形态逐条对照 -> (3) 有可测量的杠杆才发车**。
> 本轮**0 发车**，全部结论来自 0.1.42 源码 + 上游文档 + 产线实读。

## 0 结论（先行）

**短名单 36 条里没有值得花一车的杠杆**，理由三条（每条独立成立）：

1. **证据面为空**：36 条逐条扫源码/文档注释找"带数字或快慢"的句子 => **唯一带数的是 `STRATA_GR_V3`，且是 −4~−6%（负）**，并且 `fused_gr.cu:847` 逐字说默认路径**从不走**它的 opt-in 分支。
2. **撞上限**：`P48` 里机制最强的 `STRATA_EMB_REUSE_ACCOUNT=1`（上游实测 *RTX 3060, IQ3_XXS: chunk 6400 -> 6656, prompt +3.9%*）在本机**无处可涨** —— `generate.cpp:522` 逐字 `--prefill auto: the largest chunk (**up to 8192**)`，而产线实测 chunk **就是 8192**。
3. **平台不适用**：`--pcie-mode dma` 由**上游自己的文档**关死 —— `docs/BATCHED_DMA.md:3-13` 逐字 *"through `cudaMemcpyBatchAsync` on **CUDA 13.0 or later** ... Older CUDA builds and **HIP retain individual copies**"*，且自称 *"**not a demonstrated increase in model tokens per second**"*。我们是 HIP。

=> **`W17b` 改判：不发车**（原设"8 族串行试车"= 36 条 × 1 车 ≈ 数小时生产时间，换不到可测增益）。
=> 生产**全程未停**（本件 0 车）。

## 1 证据面扫描（36 条逐条）

判据：在该 env 名的所有源码/文档命中行里，是否出现 `%` / `faster` / `slower` / `measured` / `no faster` / `gain` / `saves` 等**证据词**。

| 族 | 条数 | 带证据的条数 | 备注 |
|---|---:|---:|---|
| prefill | 11 | **0** | 注释只讲机制，无数字 |
| MTP | 9 | **0** | 同上 |
| verify/commit | 5 | 1（`STRATA_DF_PLE`，只写 *"bitwise the per-token loop"*，无收益数） | - |
| GDN | 5 | 1（`STRATA_GDN_CONVL2`，见 `arch_defaults.cpp:19` 的说明，无收益数） | `GDN_PP` 已被我们实测为 **−0.13%** |
| KV/IO | 4 | **0** | `STRATA_IO_THREADS` 只在 Intel/AMD 文档里作为**文件层**队列深度 |
| 采样 | 1 | 0 | - |
| 会话 | 1 | 0 | - |

**唯一带正向数字的候选不在短名单里**：`STRATA_GR_V3`（`docs/INTEL.md:544` 逐字 *"`STRATA_GR_V3=1` 73.2 / 72.4 (**−4 to −6%**)"*）=> **负的**，且默认不走。

## 2 `P48` 三候选的逐条关闭

| 候选 | 关闭依据（逐字） |
|---|---|
| `STRATA_EMB_REUSE_ACCOUNT=1` | `prefill.cpp:258-261` 逐字 *"`bo` shares `emb`'s storage (carve) ... **STRATA_EMB_REUSE_ACCOUNT=1** lets it use the saved bytes: **a larger chunk** or more borrowed slots **where VRAM is the limit** (RTX 3060, IQ3_XXS: chunk 6400 -> 6656, prompt +3.9%), **with other rounding in the prompt path**"* + `generate.cpp:522` 的 **up to 8192** 上限 + 产线 **chunk = 8192**（`strata serve: prompt chunk auto: 8192 tokens, a 96-slot ring`，12/12 次）=> **无位置可涨**；且它**改 prompt 路径的位**（需质量门） |
| `--pcie-mode dma` | 上游 `BATCHED_DMA.md:3-13` 自述 **CUDA 13.0+ only、HIP 保留逐条拷贝、未证明提升 tok/s** => **HIP 上无效** |
| `STRATA_KV_GROW_HOLD=1` | `generate.cpp:10167-10168` *"keep the K/V as long as the longest parked conversation"* => 改 KV 驻留 => 改专家槽 => **可能改答案**（须配 `STRATA_LOGPOS` 门），且收益路径未量化。**保留为条件性候选**（唯一未关闭的一条） |

## 3 `P47` 唯一候选的现状

`--mtp-draft-vocab FILE`：

- **机制成立**：草稿头默认已是一个子集 —— 产线逐字 `strata mtp: draft head over **106,299 tokens** (212.9 MiB)`（非全词表）。
- **但是 trade，不是增益**：再收窄词表可降草稿成本，**同时降接受率**；两侧都未量化。
- **前置缺失**：需要一份代表我方用法的语料来造词表（上游 `tools/draft_vocab.py`），我们**没有**（生产 prompt 未明文留存）。
- **观测面差**：日志里**没有接受长度/草稿轮次的 per-request 指标**（只 `draft head over N tokens` 一行），=> 只能落在 **decode 时机轴**（本项目 spread 16-41%）=> 分辨力最差。
=> **暂不发车**（前置不足 + 观测面差 + 是 trade）。列为**条件性候选**。

## 4 我们自己的"上游 prompt 侧增益不迁移"记录（0/4）

| 开关 | 上游数字（卡） | 本机实测 |
|---|---|---|
| `STRATA_GDN_PP=2` | 64K prompt **+2.9%**（gfx1151/Aurora） | **−0.13%**（prefill 口径，spread 0.4-0.8%） |
| `STRATA_Q8_PACKED=1` | decode **+2.3%**（gfx1151） | +1.57~2.78%（< 臂内 spread）+ 白吃 1.87 GiB |
| `STRATA_SH_STREAM=1` | decode +1.8%/+6.7%（UD-Q4_K_XL） | **−0.13%**（`P40 REJECTED`） |
| `P59`/`P60` | 上游 *"no gain we can show here"* | **exact but no gain**（W12D） |
=> 这条记录本身就是"再加 4 个同族试车"的低期望依据。

## 5 复现

```
sed -n '518,525p'  src/program/generate.cpp     # --prefill auto 的 8192 上限
sed -n '254,265p'  src/prefill/prefill.cpp      # EMB_REUSE_ACCOUNT 的机制与数字
sed -n '1,14p'     docs/BATCHED_DMA.md          # --pcie-mode dma 的 CUDA-only 声明
sed -n '10165,10170p' src/program/generate.cpp  # KV_GROW_HOLD
grep -a 'prompt chunk auto' <prod log> | tail -3   # 产线 chunk = 8192
grep -a 'draft head over' <prod log> | tail -1     # 草稿词表 106,299
```

## 6 处置建议（改 status 属签字项）

| ID | 现值 | 建议 |
|---|---|---|
| `P48` | CANDIDATE（已收窄为 3 项） | **再收窄为单条 `STRATA_KV_GROW_HOLD`**（另两项已由 §2 关闭）；或整条 REJECTED |
| `P47` | CANDIDATE（已收窄为 `--mtp-draft-vocab`） | 保持 CANDIDATE 但**标注前置缺失**（需语料 + 需 decode 轴观测），**暂不发车** |
| `W17b` | 待办（8 族试车） | **判"不发车"**（本件证据链）；`W17a` 的短名单保留为档案 |
