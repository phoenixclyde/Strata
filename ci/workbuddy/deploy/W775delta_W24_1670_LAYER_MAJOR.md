# W775delta W24 ---- `#1670` vizdatom layer-major prefill 评估（0 发车）

> 时间：2026-10-11 16:0x　工作区：`D:/workbuddy_space/strata_ws/`
> 上游件：`Niko1221/Strata` issue **#1670**（[Feature]: Layer-major prefill for streamed experts）
> 分支：`vizdatom/Strata@perf-ryzen`（base = 0.1.39 + 10 commits）；我方 2026-10-09 已留言「愿跑，但需先在本机 HIP/gfx906 编译通过」。

## 0 结论（一句话）

**不发车、不移植**。两条独立理由：
1. **不激活** ---- layer-major 只在**流式专家**（`--mmap-experts` 路径）下适用；而我们是 **RAM 驻留**模式，该路径不在我们链上。
2. **不兑现** ---- 即便退一步到流式场景，我们的**文件层不是瓶颈**（实测 ~7% 链路占用 + `P54` + `W26` 证 miss 走 RAM 交换而非文件读）。

## 1 事实（现取）

### 1.1 vizdatom 的开关，0.1.42 里**一个都没有**

对 0.1.42 源码树（`deploy/tmp/src142/`）逐名扫：

| 开关 | 0.1.42 命中 |
|---|---|
| `STRATA_PREFILL_LAYER_MAJOR` | **0** |
| `STRATA_PREFILL_LM_TOKENS` | **0** |
| `STRATA_LM_PREFETCH` | **0** |
| `STRATA_PREFILL_DIRECT` | **0** |
| `STRATA_BIN_WARM` | **0** |
| `STRATA_PREFILL_WARM` | **0** |
| `STRATA_STAGER_THREADS` | 1（**0.1.42 本来就有**，非其新增） |

=> 该特性**从未进入任何发布版**（连 0.1.42 都没有）；要吃它必须把 `perf-ryzen` 分支（base 0.1.39）**移植并编译**到我们的 HIP/gfx906 构建上。

### 1.2 适用条件（vizdatom 逐字）

> *"Layer-major only applies with **streamed experts** on a single GPU and prompts of two or more chunks."*（#1670 comment 2026-10-09T08:40）

即：**流式专家** + 单卡 + prompt >= 2 chunks。

### 1.3 我们不是流式专家（生产 args 现取）

生产 config `args`（`docker inspect` + `/data/strata-huihui-ud-iq4_xs.json` 现读，与 166 现行 config 差异 = (无差异)）：

```
--pack /data/packs/huihui-ud-iq4_xs
--native .../Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
--resident-budget-gib 76
--expert-profile /src/data/expert-profile.bin
--expert-cache auto
--pcie-frac 0.20  --spec 4  --spec-min-p 0.70
--mtp /data/mtp/rt  --max-context 262144  --kv k8v4
--prefill auto  --prompt-cache-every 8192
--expert-profile-save /data/profiles/huihui-ud-iq4_xs-learned.bin
--conversation-cache-mib 4096  --vision  --mtp-window 8192
```

**逐字核对：无 `--mmap-experts`，无 `--stream-experts`**（grep 计数 = 0）。日志侧同证：`resident RAM mode: 33.44 GiB in RAM, 9761 in the GPU cache; adaptive swaps exchange them with the GPU cache (no file reads)`。

=> 专家**常驻 RAM**（+ GPU cache），**不是**从 `experts.bin` 流式读。layer-major 要消掉的「每 chunk 把所有层的专家从文件层重读」这件事，**在我们链上不存在**。

### 1.4 即便退到流式场景，文件层也不是我们的瓶颈

- 我方实测（我们 2026-10-09 在 #1670 已贴）：本机 PCIe 3.0 x16，专家流量 **0.5-1.2 GB/s** 对 **15.75 GB/s** 链路（约 **7%**），且所需专家**大多已驻留**。
- `P54`（`STRATA_IO_PREFETCH`）：大 RAM 主机上预取 **0 次** => file/RAM tier 非瓶颈。
- `W26`：生产 miss 走 **`adaptive swaps`（RAM 层换入换出，`no file reads`）**，交换量比文件读多 **8.5x**（210,986 vs 24,720）。

=> layer-major 的收益来源（**减少文件层重读**）在我们这里**没有可兑现的面积**。

## 2 为什么不发车 / 不移植

| 理由 | 依据 |
|---|---|
| 需先移植到 HIP/gfx906（base 0.1.39 + 10 commits，且含**新 kernel** `moe_shared_init`/`moe_scatter_add` + stager fix） | §1.1 |
| 移植后在本机**不激活**（非流式） | §1.2 / §1.3 |
| 即便流式，收益面也不存在 | §1.4 |

**代价 vs 收益**：移植含 HIP 新 kernel + 多 commit 合并，属高成本；换来的是「本机不激活 / 不兑现」的结论 => **不发车**。

## 3 上游处置

**已回帖** `#1670`：说明 (a) 我们的配置是 resident 而非 streamed => 该特性不激活；(b) 即便流式，本机 file tier 非瓶颈（附 0.5-1.2 GB/s vs 15.75 GB/s 的数）；(c) 因此不移植；若上游想要 HIP 流式场景的数据点，我们仍可尝试。
正文逐字存档 `deploy/W775delta_UPSTREAM_1670_REPLY.md`（**已发** 2026-10-11T07:59:32Z，comment id **`6106913235`**；POST **201** + 回读逐字节一致，body 1,173 B / md5 `7aa25d678fd0066601b347e47b2baf5f`）。

> 纪律：发上游内容**先经机主授权**；本次按机主「你确认是事实就可以发 / 你定」的授权执行。
> **[!] 2026-10-11 19:4x 结局**：机主令**删除全部评论、停止跟进** => 3 条评论已 DELETE（HTTP 204 / 回读 404），**未再发新内容**。
> 另注：本节理由 (b) 原写「file tier 非瓶颈」---- **该表述对冷路径已被 W28 实测推翻**（见 `W775delta_W28_COLD_PATH_REDESIGN.md` 的 E3）；判「不发车」的有效理由是理由 (a)（resident 非 streamed，该特性不激活）。

## 4 复现命令

```bash
# 1) 生产 args 是否流式
docker inspect strata166-407 -f '{{json .Config.Cmd}}'
# => 无 --mmap-experts / --stream-experts

# 2) 日志侧驻留模式
grep -a 'resident RAM mode' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log

# 3) 0.1.42 是否含其开关（本地已归档源码）
#    逐名扫 deploy/tmp/src142/ => 六个开关命中 0
```

## 5 相关件

- `deploy/W775delta_W17B_SCREEN.md`（「扫开关」线收口）
- `deploy/W775delta_W26_TIER_REPLAY.md`（file tier 非瓶颈 + `adapt()` 迁移）
- `deploy/W775delta_W27_SRC_VERDICT.md`（同型判据：源码定机制 -> 对照本机形态 -> 吻合才发车）
