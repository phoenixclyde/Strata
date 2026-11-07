# W822：换权重到 UD-Q4_K_XL（含 K-quant 配套参数）

> 状态（2026-10-29 21:52）：**已上生产**。`UD-Q4_K_XL` + `STRATA_MMQ_KQ=1`，2636 token 提示 **427 tok/s**、解码中位 **42.0 tok/s**。
> 旧 IQ4_XS 是 508 / 48.9 —— ~~新档慢 16% / 14%~~ **（AUDIT11 更正：这个比值不成立）**。
> 真实代价**只在解码（−14%）**；提示侧因为 427 是冷启动首请求、508 无测量条件，
> 今天是稳态 **525**，**两者不可比**，见下方 §3 的补注。所以换档的账应写成
> 「**用约 14% 解码速度换上游 +4.2pp top-1（本机未验）**」，不是"双降 16%/14%"。

## 1 为什么是这两个工具：`iq_pack` vs `strata_pack`

这是本次最容易搞错的一处，记录证据：

| 工具 | 定位 | 对 UD-Q4_K_XL 能否用 |
|---|---|---|
| **`tools/iq_pack.py`** | 生成引擎 `--native` 模式要的**索引 pack**（`index.txt` v3 + `native_experts.txt` + `dense.bin`），专家本体仍留在 GGUF 里由引擎按偏移读 | **能，且是官方路径**。`docs/UNSLOTH_Q4.md` 给的就是 `iq_pack.py … --compat-bf16` |
| `tools/strata_pack.py`（C++ 版 `tools/strata-pack`） | Phase-2 的 **canonical pack**：`manifest.json` + `experts.bin`（专家反量化后逐位存盘）。规则是"`decode(pack) == dequant_ggml(source)`，`verify` 不是可选项" | **不能**。它的映射表是 i-quant 的；对这份 K-quant 分片直接崩在 `data_section_offset: max() iterable argument is empty`。另：`experts.bin` 会是 75 GB，本机也放不下 |

`--compat-bf16` **是文档强制项**（不带则打包器拒绝、什么都不写）：这份文件把 195 个小投影
（hyper-connection 上下矩阵、`output_hc_*`、PLE value）存成 Q8_0，而引擎按 BF16 读，必须转一次。
代价（上游自述）：该舍入在 Strix Halo 上让 ppl 比 llama.cpp 高 6-9%，「读 Q8_0 原值能抹平大部分，但不在本版本」。

## 2 实际改动（生产配置）

| 位置 | 旧 | 新 |
|---|---|---|
| `--pack` | `/data/packs/huihui-ud-iq4_xs` | `/data/packs/ud-q4_k_xl` |
| `--native` | `…/unsloth-UD-IQ4_XS/…-00001-of-00003.gguf` | `…/unsloth-UD-Q4_K_XL/…-00001-of-00004.gguf` |
| `--expert-profile-save` | `…/huihui-ud-iq4_xs-learned.bin` | `…/q4kxl-learned.bin` |
| `tokenizer`（顶层字段） | `/data/packs/huihui-ud-iq4_xs/tokenizer` | `/data/packs/ud-q4_k_xl/tokenizer` |
| `vision.model` | 旧权重的 shard1 | 新权重的 shard1 |
| `env.STRATA_MMQ_KQ` | 未设 | **`1`** |

后两项是踩出来的：**删掉旧 pack 后 server.py 直接拒启**（`the model's tokenizer is missing … run setup again`），
而 `vision.model` 一直指着旧权重的 GGUF。`model_name` 故意没改（它是 OpenAI 侧的 model id，改了会断现有客户端）。

## 3 数字（同一语料，2636 token，暖缓存）

| 项 | 旧 IQ4_XS | 新 Q4_K_XL（不开 MMQ） | 新 Q4_K_XL + `MMQ_KQ=1` |
|---|---:|---:|---:|
| 提示 | 508 tok/s ⚠ | **267 tok/s** | **427 tok/s**（测试臂 457）⚠ |
| 解码中位 | 48.9 tok/s | 32.9 tok/s | **42.0 tok/s** |

> ⚠ **AUDIT11 补注（2026-10-30）：这一列的两个数都要重新读。**
> ①**427 是"容器就绪后第 1 个请求"的值**。今天在同一语料（`sha16=989c7369`、2636 token）实测**稳态 5.02 s = 525 tok/s**
>   （三次 5.02 / 4.84 / 4.73 s），差 **−18.6%**。机理：首请求带约 **1.0 s** 冷启动
>   （W816 原始件 `TR` 行：`read 69 tokens in 1018.3 ms` → 第二次 167.7 ms → 稳态 57-65 ms），`6.17 − 5.02 = 1.15 s` 吻合。
> ②**508 没有记录测量条件**（哪一次、是否首请求、暖冷缓存），而对照组（IQ4_XS）已被删除 ⇒ **不可复核**。
>   因此"新档慢 16%"这个代价**不成立为结论**：prefill 可能基本持平甚至略快；**确定存在的代价只有解码**（42.0 vs 48.9 = **−14%**）。
> ③ 267 与 457 之间还差一次 **pack 重打**（已核：两份日志的 `blob 3.99 MB / arena 36727 页 / 槽位 7551` 逐项相同，风险低），
>   且 `w822m` 那次 **THP 碎片化**（`only 26 GiB of free 2 MiB blocks`）而 `w822t` 是 requested ⇒ 差异对结论**保守**。
| 专家 arena | 55.43 GiB | 71.7 GiB（36727×2 MiB） | 同 |
| 槽位 | 9873 | 7551 | 7551（22.04 GiB） |
| 启动 | 170-200 s | 175 s | 180 s |

`MMQ_KQ=1` 的效果（+60~71% 提示）与上游 `docs/UNSLOTH_Q4.md` 的描述方向一致：
「…multiplies the Q4_K / Q5_K / Q5_1 experts of a prompt with llama.cpp's MMQ kernels … instead of dequantizing them to FP16:
4x less GPU time for those products」。不开时走 FP16 反量化，每个专家按 ~10 MB FP16 读。

## 4 清掉的旧数据

- `/data/packs/{huihui-ud-iq4_xs, ud-iq4_xs}`（各 1.4 GB，同源重复）——删
- `/data/profiles/{huihui-ud-iq4_xs-learned.bin, *.bak_p31_*, ud-iq4_xs-learned.bin, calib-learned.bin}`——删
- **旧 GGUF 88 GB 未动**（删除需明确确认：重下要几天）

## 5 两条新踩的坑（已写进规则）

1. **派生配置必须先于"删旧数据"重生**：我第一次的 `w822_mmkq.json` 是在修 `tokenizer` 之前派生的，
   跑起来立刻 `error: the model's tokenizer is missing` —— 与"启动很慢/内存不足"的现象完全不同，容易误判。
2. **重启多了会碎片化 2 MiB 大页**：某次启动报
   `transparent huge pages NOT requested: only 26 GiB of free 2 MiB blocks for a …`，启动从 180 s 拖到 350 s+。
   重启机器即恢复（本次 21:09 重启后，180 s 正常）。

## 6 下一步候选（按预期收益）

1. **`--spec-min-p` / `--spec`**：新权重的 MTP 接受率是 49/72（68%），与旧权重不同，这对窗口长度是有偏的。
2. **`STRATA_ROUTE_TAIL_SKIP`**：槽位从 9873 降到 7551，miss 更多 ⇒ 尾跳的覆盖面变大（本次累计 14008/14932），
   质量与速度两端都该重测（这是 register 里唯一"开着的、明说会改答案"的近似）。
3. **`--pcie-frac`**：miss 变多后，PCIe 流在 decode 里的权重上升。
4. PLE 常驻（`--ple-io ram` / 0.2.7 的 `STRATA_PLE_AUTO_RAM`）：现在是 direct，且 arena 从 55.4→71.7 GiB，
   加上表 26.8 GiB 后需要 ~110 GB 空闲 RAM，比之前更紧。

## 7 回滚

```sh
cp /home/albus/strata166/data/w822_prod_backup.json /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
# 还需要旧 pack + 旧 tokenizer 目录（已删，可从 GGUF 用 iq_pack --compat-bf16 重打，约 45 s）
docker restart strata166-407
```
