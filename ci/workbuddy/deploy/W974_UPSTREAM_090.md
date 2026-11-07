# W974 上游跟进 v0.9.0（2026-11-05）

## 结论

**这次"更新"在代码层是零差异，只换掉了版本号与溯源。** 生产已切到 v0.9.0（`cd959bae`）构建的引擎，bench 与旧引擎同量级。

## 一、边界（GitHub API 实查）

| 项 | 值 |
|---|---|
| 目标版本 | **v0.9.0** = `cd959bae99ff4bed22bef2604f45241c09bbb8c8`，2026-11-04 12:06 UTC（**20:06 CST**），PR #31646 |
| 对应 nightly | `b12110`（2026-11-04 12:52 UTC 发布） |
| 我们上一版基线 | `ref/llama_b12099` = **`feaf8000`**，2026-11-04 11:11 +0200（**17:11 CST**）——它是 **master**，不是 0.8.0 标签 |
| 结论 | 上一版已包含 0.8.0 之后 7 天的全部 master 提交（含 `#31247` Q8_1 修正、`#31188` MoE gate/up+GLU 融合、`#29510` flash_attn_ext_rows） |

## 二、v0.9.0 相对我们上一版：4 个提交、5 个文件

| 提交 | 内容 |
|---|---|
| `e853ec9a` | llama : Gemma4 assistant 跟随 ctx_other / flash attention（`src/llama-context.cpp` +29 行）**我们不用**（不编译 llama/ 层） |
| `cca14f64` | ggml : bump 0.28.0 → **0.29.0**（ggml/1680） |
| `13ec8f61` | sync : ggml |
| `cd959bae` | llama.cpp : bump 0.8.0 → **0.9.0** |

文件级：`AUTHORS`(+26)、`CMakeLists.txt`、`ggml/CMakeLists.txt`、`scripts/sync-ggml.last`、`src/llama-context.cpp`(+29)。

**整个 `ggml/` 目录 diff = 2 行**（`GGML_VERSION_MINOR 28 → 29`）。`ggml/src/ggml-cuda/` 下 `mmq.cuh`、`quantize.cu`、`ggml-cuda.cu`、`gated_delta_net.cu`、`mmq-config-gcn.cuh`、`mmq.cu` **逐字节相同**（md5 一致）。

## 三、v0.9.0 之后 master 又走了 5 个提交，全不碰 CUDA

`5851a8e5` drama-3 TTS、`efbf6e80` UI PDF 预览、`b393d73b` webgpu、`00df7c22` sycl docker、`034e2535` gguf-py tokenizer 校验。

## 四、构建

| 项 | 值 |
|---|---|
| 源码树 | `ref/llama_b12110`（v0.9.0 稀疏检出，`git log` 确认 `cd959bae`） |
| 构建目录 | `build-r32` |
| flags | 与 `build-r29` **逐字相同**（Release / `-O3 -DNDEBUG` / gfx906 / `STRATA_MMQ_TQ_OVERLAY=ON` / `STRATA_MMQ_KQUANTS=ON` / `NATIVE_EXPERTS=ON` / `Q6K_EXPERTS=ON` / `AMD_COMMUNITY_TUNING=ON`） |
| configure | `ggml version: 0.29.0`；trellis overlay **on** |
| 结果 | **44,908,992 B，0 error**（与旧二进制字节数完全相同） |

## 五、部署

| 项 | 值 |
|---|---|
| 新引擎 | `/data/bin/strata-0.1.56-090`，md5 **`eea5ea3749ad54b124330386605a18bc`** |
| 旧引擎 | `/data/bin/strata-0.1.56-080`，md5 `209d8f50a77d9d45803c9cbbe3e70dde`（原地保留） |
| config | md5 `172693a40495fe7aa943c7fff8c86e49`；`exe` 已指向 `-090`；args 33 / env 9 未动；`vision.exe` 未动 |
| 重启 | **1 次**，停机 ≈4.5 分钟（装载 55 s + bench） |
| 容器 | `restart=0`、`running`、StartedAt `2026-11-04T16:40:15Z` |
| 显存 | `expert cache 7463 slots, 21.79 GiB`（与旧版一致） |

## 六、bench（同一探针、冷读、`reused=0`）

| 输入 | 旧引擎（0.8.0 代码） | 新引擎（v0.9.0） | 差 |
|---|---:|---:|---:|
| 2,353 tok #1 | 486.0 | **488.9** | +0.6% |
| 2,354 tok #2 | 535.5 | **540.7** | +1.0% |
| ~59–60 K | 804.1 @60,330 | **794.4 @59,054** | −1.2%（噪声内，输入不同） |

判据 2×CV 未破 ⇒ 无回归。

## 七、回滚

```bash
cp /data/strata-huihui-ud-iq4_xs.json.bak_w974 /data/strata-huihui-ud-iq4_xs.json
docker restart strata166-407
```
或只改 exe：
```bash
python3 -c "import json;p='/data/strata-huihui-ud-iq4_xs.json';c=json.load(open(p));c['exe']='/data/bin/strata-0.1.56-080';json.dump(c,open(p,'w'),indent=1)"
docker restart strata166-407
```

## 八、后续策略

上游 CUDA 的实际变动频率远低于版本号频率：0.8.0 → 0.9.0 只动了版本串。建议**按 CUDA 目录指纹触发重建**（`diff -rq ref/A/ggml/src/ggml-cuda ref/B/...`），而不是每个 tag 都重编；版本号对齐只在需要溯源时做。
