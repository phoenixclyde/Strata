# W905 · 精度账：我们今天调的是"已经用精度买过单"的那条轴

> 2026-11-03 02:3x。零落产。本件回答两个问题：①我今天开的哪个设置让这些尝试注定没有实质收益；
> ②"Strata 一味追速度牺牲精度"这句外部评价，落到**我们这台机器**上具体是哪几个开关、代价多少。

---

## 1 一句话结论

**不是调参手法错，是轴选错了。** decode 窗口的 **69.9%** 在等 GPU（33.42 / 47.83 ms），host CPU 只占 9.0%；
而 GPU 时间里最大的一块是专家权重读取（W863：11.78 ms = 24.9%）。所以：

- 改 **ALU / 指令**（R51 解包、R55 swizzle）→ 落在 30% 里的一小块，实测 0 或负；
- 改 **launch/同步**（R54 megakernel）→ 只对 T≥4 有效，生产 `avg T 3.7`；
- 真正能动的只有**专家驻留/搬运**，而这块的余量早就被 `--expert-cache auto` + `vram-reserve-mib 832`
  + `--kv k8v4` 这几项"用精度换显存"的设置吃掉了。

## 2 外部证据（联网核实，分清"项目自己写的"和"第三方测的"）

| 来源 | 主张 | 性质 |
|---|---|---|
| 仓库 `docs/DETAILS.md:215` | `--kv q4_0`：**perplexity +8–12%**，needle 仍过，128K 快约 4% | **项目自述** |
| 仓库 `docs/DETAILS.md:216` | `--kv k8v4`：比 q4_0 更精确，KV 省 23%，prompt 慢 2–5% | 项目自述（**我们在用这个**） |
| 仓库 `docs/DETAILS.md:1424` | `STRATA_ROUTE_TAIL_SKIP`：KL 0.0058 / 0.0056，top-1 97.7% / 97.5%，PPL ×1.011 | 项目自述（**我们 tuned 包里的一项**） |
| 仓库 issue #1815 | logits 变 NaN 时连打 256 个 `!`，0.1.43 才加 guard | 项目自述 |
| ic.work 报道 | speed projection 控制向量：约 **10% 位置 Top-1 改变**、代码困惑度 **+15%**、连拒答行为都变 | 第三方 |
| solosoft 审计 | 视觉路径 median error **154.8 px vs llama.cpp 46.5 px**；仓库**没有任何权重精度数字** | 第三方（独立复现） |
| bytenote 实测 | KLD/top-1/PPL 几乎不变时，**EAR 仍差 2–3%**（≈ 一档量化） | 第三方 |

**结论**：那句"牺牲精度换速度"不是黑它——**项目文档自己写着**，而且是**按开关分开写**的。
所以问题不是"有没有代价"，而是"**这些开关组合起来的代价，我们从来没测过**"。

## 3 我们生产到底开了什么（逐条，含代价与证据）

| 设置 | 数值 | 性质 | 文档/实测代价 | 我们测过吗 |
|---|---|---|---|---|
| `STRATA_GFX906_TUNED` | `1` | 启动横幅逐字：**"the rounding-level recipe is on"**，展开 7 项 | **组合代价未知** | **从未** |
| └ `GFX906_ATTN_QUERY_SWIZZLE` | 开 | 注意力查询重排 | 未单列 | 否 |
| └ `GDN_PP` | 开 | 逐点精度 | 未单列 | 否 |
| └ `HC_Q8` | 开 | HC 侧量化到 8-bit | 未单列 | 否 |
| └ `SELECT_SIMT` | 开 | top-k 选择走 SIMT | 未单列 | 否 |
| └ `ROUTE_TAIL_SKIP` | 开 | 路由尾部跳过 | **KL 0.0058，top-1 97.7%**（文档） | 仅文档 |
| └ `MMQ_KQ` | 开 | K-quant prompt 走 MMQ | 源码注释：**"opt-in: other rounding than the FP16 path"** | 速度测过（1.57×），精度没测 |
| └ `HIP_PROMPT_F16` | 开 | prompt 的 GEMM 走 FP16 in/out | 启动日志自述"not bit-identical to the default" | 否 |
| 关掉上面整包后仍有 | 2 项 | 今晚 B 臂横幅：`GDN_HEAD`、`GFX906_ATTN_REDU` **默认仍开** | 未单列 | 否 |
| `--kv` | `k8v4` | K 8-bit + V **旋转 4-bit** | q4_0 为 +8–12% PPL；k8v4 只写"更精确" | 否 |
| `--spec 4 --spec-min-p 0.70` | 开 | 投机解码（验证是精确的，不改输出） | 不影响精度 | — |
| `STRATA_DECODE_TIMING` / `SPEC_DEPTH` / `VERIFY_NODES` | 常开 | **纯测量** | 每窗口付 host 时间 | — |

**我们手上唯一的精度证据**：`W806`（prompt 侧 KL .0139）、`W888`（needle 32k 3/3、128k 1/1）。
两件都是**单项、单点**；而且 needle 对 KV 量化**不敏感**（文档自己写"needle tests still pass"），
拿它当"精度没退化"的证据是不成立的。

## 4 为什么今晚三次尝试都没有实质收益（用量化数字说）

最新一条生产窗口（42 windows，avg T 3.74，47.83 ms/window）：

```
47.83 ms = GPU-reach wait 33.42 (69.9%) + per-layer host 5.00 (10.5%, 其中 CPU 4.31)
         + adapt wait 1.91 (4.0%) + stage 0.12 + commit/emit 0.05
```

- **能改的只有那 33.42 ms 里的东西**，而里面最大一块是专家读：`VRAM hits 8.85 + waitB 1.28 + PCIe 0.81 + copy 0.84 = 11.78 ms（24.9%）`（`W863`）。
- R51 打的是 **prefill** 的 MMQ（decode 不经过它）⇒ 对 45→70 tok/s 这条线**天然无效**；而 prefill 里 MMQ 占比 34.6%，即使 hoist 完全成功、也只值 **~3% 的 prefill**，实测还是负的。
- R55 打的是 `qsa_select` 的交换指令，实测三档上下文 **±0.4%**（该核由标量/shared 主导）。
- R54 打 launch 合并，只在 **T≥4** 有 +12~16%，生产 `avg T 3.7`、且窗口以 T≤3 为主。

⇒ **几何上就不可能有大收益**。这不是运气问题。

## 5 今晚做了但没跑出数据的那个实验（如实记）

工具是有的：`--dump-logits PATH`（源码 `generate.cpp:1015`，头部 2×int32 = n_vocab, n_rows）。
目标是同一批 128 个 token，比 `TUNED=1` 与 `TUNED=0` 的 KL / top-1 —— 这正是"组合代价"的直接测量。

**排掉的坑（都已确认）**：
1. 二进制没有 `generate` 子命令，参数直接给；
2. `--tokens-file` 比 `--tokens` 稳；`/usr/bin/time` 在镜像里不存在；
3. native pack **必须** `--spec T(≥2)` + `--prefill CHUNK`；
4. `--spec` 又要求 `--expert-profile`（用镜像自带的 `/src/data/expert-profile.bin`）。

**结果**：A 臂跑通（`prefill 127 tokens in 1080.5 ms`，打印 `logits dumped /data/tmp/logits_a.txt`），
但文件 **0 字节**。⇒ 不是命令拼错，是 `logits_selection` 的 `dump_positions` 判定没满足。
**本件不编 KL 数字**；下一步直接读那段判定（或改用 `--check-logits` 的路径）。

## 6 结论与下一步

1. **R51/R54/R55 的失败是同一个原因**（选错轴），不是三次独立失误——这条要写进方法的账。
2. **`W904 §7.4` 的方法教训再补一条**：微基准不仅要含被调函数的完整固定成本，还要确认**这段代码在目标
   场景（decode/prefill）里真的被执行**，否则测的是"另一台机器上的另一个程序"。
3. **新条目 R59（精度账）**：先测组合代价（A/B logits → KL / top-1），再决定回退顺序：
   先动"文档有代价、我们又能不用"的项（`ROUTE_TAIL_SKIP`、`HC_Q8`、`--kv k8v4`），
   最后才动"速度依赖大"的项（`MMQ_KQ`，1.57×）。判据：任一组合的 **KL ≤ 0.005 且 top-1 ≥ 99%** 才算可用；
   超过就要么回退、要么在方案里显式登记"这段精度是我们主动放弃的"。
4. **速度轴改向**：从 ALU 转到**专家驻留**（VRAM 余量、`vram-reserve-mib`、`--kv` 的显存-精度交换比），
   这是唯一还有量级空间的地方；而且它本身就是精度/显存的权衡，必须和 R59 一起算。

## 7 复现

```bash
# 已确认可用的调用（在镜像内，需 --device /dev/kfd）
strata-0.1.55t --pack /data/packs/ud-q4_k_xl --native <shard1.gguf> \
  --expert-profile /src/data/expert-profile.bin --expert-cache auto --pcie-frac 0.20 \
  --max-context 32768 --prefill 8192 --spec 4 --vram-reserve-mib 832 \
  --tokens-file /work/tokens.txt --max-new 1 --dump-logits /data/tmp/logits_a.txt
```
