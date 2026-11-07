# WorkBuddy 自定义模型设置清单  -  166 测试台的 Strata（UD-IQ4_XS）

> **升级于 2026-10-08 22:35 CST**：Strata `v0.1.40.4` -> **`v0.1.41`**（当日第二次）
> **2026-10-09 20:3x 更新**：此后 W715 又切至 **huihui abliterated** 权重（现役容器 **`strata166-407`**）。本文档余下章节仍是 **W712 时代视图**；当前权威指针见 `MEMORY.md` §0 与 `W715_HUIHUI_SWITCH.md`。C3 清理后 `-402/-404/-405/-401/strata166` 等旧容器与 `0.1.40.x/0.1.39` 旧镜像**已不存在**。
> 服务：镜像 **`strata-gfx906:0.1.41`** / 容器 **`strata166-407`**（回滚位 `strata166-406`）/ 端口 **8090**
> 自启方式：**Docker restart policy（`unless-stopped`）**  -  与 166 上另 5 个常驻容器同机制，**不用 systemd**
> 回滚：`docker stop -t 30 strata166-407 && docker start strata166-406`（回滚位保留，`Exited (0)`）
> 所有字段均为**真实请求验证**（HTTP 状态码 + 响应体），非读文档推测。

## 一、必填项

| WorkBuddy 字段 | 填什么 | 依据（实测） |
|---|---|---|
| **模型地址 / Base URL** | `http://192.168.50.166:8090/v1` | `GET /v1/models` -> **200**，返回 `id: qwen3.8-flash-next-ud-iq4_xs` |
| **API Key** | 随便填一个非空串，如 `sk-strata166` | 服务**未设 key**（启动日志有 `WARNING: no API key`），任何值都过；要真设就把 `"api_key"` 写进 `/data/strata-huihui-ud-iq4_xs.json`（W735 更正：现役 config 名已带 `huihui-`）|
| **模型名称 / Model ID** | `qwen3.8-flash-next-ud-iq4_xs` | 同上，来自 `/v1/models` |

⚠️ 别填 `172.17.0.x`（那是容器内网地址，Windows 侧不可达）；端口已发布到宿主，用 `192.168.50.166:8090`。

## 二、能力开关

| WorkBuddy 字段 | 建议值 | 依据（实测） |
|---|---|---|
| **支持思考模式** | ✅ **勾** | 返回体带 `reasoning_content`（默认不传就思考） |
| **允许关闭思考** | ✅ **勾** | `reasoning_effort: "none"` -> 无 `reasoning_content`、prompt 从 59 -> **19** token |
| **默认思考强度** | `medium` | 实测 `medium` 正常 |
| **支持的思考强度** | 勾 **low / medium / high** | 三者均 **200**；`xhigh` 也 200（等价模板默认），`minimal` 也 200（等效关思考） |
| **工具调用（Function Calling）** | ✅ **勾** | 0.1.40.2 复测：`finish_reason = tool_calls`，返回 `{"city":"Shanghai"}` |
| **图片输入** | ❌ **暂不勾** | 实测 **HTTP 400**：`this server was started without the vision encoder`。mmproj 已就位（`/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/mmproj-Qwen3.8-Flash-Next-BF16.gguf`，907.5 MB），但**镜像里没有 `strata-vision` 二进制** => 启用需先重编镜像（多编一个目标）+ 写 `vision` 段 |

## 三、长度限制（输入 + 输出 <= 262144，服务端**不做截断**）

| WorkBuddy 字段 | 建议值 | 依据（实测） |
|---|---|---|
| **上下文窗口** | `262144` | `/v1/models` -> `meta.n_ctx = 262144` |
| **输出上限** | `32768` | `max_tokens=65536` -> 200；超过剩余窗口 -> **400**：`prompt + max tokens exceeds the context` |
| **输入上限** | `229376` | = 262144 - 32768 |

> 262144 的代价只有 776 个专家槽（~1.76 GiB），而 `--kv k8v4`（K 保持 int8 精确、V 用旋转 Q4_0，816 B/cell vs int8 的 1056）把这笔抵掉大半还富余。

## 四、采样参数（服务端一律尊重请求里的值）

引擎自身默认 **greedy（argmax）**；以下键服务端接受并透传：
`temperature`（0..2）· `top_p`（0<p<=1）· `top_k`（整数 1..64）· `seed`（正整数）· `max_tokens`（正整数）

- 通用对话建议：`temperature 0.6 / top_p 0.95 / top_k 20`
- 代码、工具调用建议：`temperature 0`（或 0.2）

## 五、可选：Anthropic 方言也能用

`POST /v1/messages` -> **200**，返回 `content: [{"type":"thinking",...}, ...]`。端点同为 `http://192.168.50.166:8090`。

## 六、运维须知（2026-10-08 起已变更）

1. **开机自启已生效**（此前是手动档）：容器带 **`--restart unless-stopped`**，`docker.service` 开机起 => 容器自动拉起，**冷启动到可用约 20 秒（页缓存热）~ 240 秒（冷）**。
   - 查状态：`docker ps | grep strata` · `curl -s http://127.0.0.1:8090/v1/models`
   - 手动重启：`docker restart strata166-407`
   - 停（且不要它自己回来）：`docker stop strata166-407`（`unless-stopped` 语义：手动停后 daemon 重启不会拉起它；要它回来就 `docker start strata166-407`）
   - 改回"永活"：`docker update --restart always strata166-407`
   - ~~回滚到 0.1.40.2~~（**作废**：`-402` 等 0.1.40.x 容器与镜像已于 2026-10-09 C3 清理中删除）；**当前回滚位 = `strata166-406`**
2. **166 是测试台，仍会被关机**；关机后 WorkBuddy 里该模型会报连接失败。**166 无远程唤醒**，重启要现场按电源键（但起来后服务会自启，不必再手工 exec）。
3. **服务无鉴权**：同网任何人都能用。要收口就在 `/data/strata-huihui-ud-iq4_xs.json` 里加 `"api_key"`（W735 更正 config 名）。
4. **不用 systemd 管这个容器**：本机 6 个常驻容器（open-webui / netdata / comfyui-cu130 / portainer / searxng / strata166-407）**全部靠 Docker restart policy**，`/etc/systemd/system/` 下没有任何 docker 相关 unit。
5. 当前实测性能：**0.1.40.4 中性 A/B**（0.1.40.4 vs 0.1.40.2，18,084-token 冷 prompt，Z0=off）
   = 冷预填 **456.1 vs 457.6 tok/s**（-0.33%，落在 1.2-1.7% 分辨力内）、温 TTFT **5.753 vs 5.853 s**、
   前缀复用 `reused` **均 16384**、常驻专家 RAM 均 33.45 GiB => **两版不可分辨**（详见 `W712_UPGRADE.md` §3）。
   历史读数（0.1.40.1 时代，18k prompt）：预填 438.8 tok/s · 解码 42.9 tok/s · MTP 接受 61-66%。
   **0.1.40.4 解码基准已补测（A2，2026-10-08 21:1x）**：512 token x 3（temp 0 / top_k 1，预热 2 条）
   = 引擎行 **45.7 / 43.3 tok/s**（探针中位 43.53），MTP 接受 **71.2% / 71.6%**；对历史差 +1%~+6.5%，
   **落在 9.5-15% 解码分辨力内 => 未见差异**（证据 `deploy/tmp/_w712_decode_bench.out.txt`）。
   0.1.40.2 的短请求实录：`prompt 17 tok @ 33.2 tok/s`、`predicted 2 tok @ 10.3 tok/s`、**`draft 3 / accepted 3`**。

## 七、一行式自检（在 WorkBuddy 接入前先跑）

```bash
curl -s http://192.168.50.166:8090/v1/models
curl -s http://192.168.50.166:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":16}'
```

两条都 200 再填表单，能省掉"以为是 WorkBuddy 配错了"的排查。

---

## 八、升级记录（0.1.40.1 -> 0.1.40.2，2026-10-07/08）

**构建配方**（`/home/albus/strata166/build-ctx-402/`）：
底座 `docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete` + 源码 `strata-src-0.1.40.2.zip`
（sha256 `7d595d4ae04b1e163ddd642c5e307d1931b17c36c26a267be0c201f90173383b`）
+ 复用 `llama.cpp-3cf0325.tar.gz`（`LLAMA_CPP_COMMIT` 与 0.1.40.1 相同，未变）
+ 补丁器 **`patch_gfx906_402.py`（v3）** + `Dockerfile-0.1.40.2`。

**补丁面变化（这是本次升级的实质差异）**：

| 处 | 0.1.40.1 | 0.1.40.2 | 依据 |
|---|---|---|---|
| H1 `strata_hip.h` cudaFuncSetAttribute 宏->模板函数 | 要打 | **上游已修** | `inline hipError_t cudaFuncSetAttribute`（行 163） |
| H2 `fused_gr.cu` 裸 `return;` -> `return false;` | 要打 | **上游已修** | `the gfx906 STRATA_GR_SPLIT read`（行 1743） |
| H3 `mtp.cpp` stream-priority 门 | 要打 | **上游已修** | `!defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`（行 420） |
| H4 `vmm.cpp` `<cuda.h>` 门 | 要打 | **上游已修** | 同上（行 3） |
| **H5 `CMakeLists.txt` q6_k 实例门** | 要打 | **仍需打** | `moe_mmq.cu:219` 在 `__HIPCC__` 下调 `mul_mat_q_case<GGML_TYPE_Q6_K>`，而 CUDA 分支只在 `STRATA_Q6K_EXPERTS` 时加该实例 |
| **H6 `strata_hip.h` 补 `cudaEventBlockingSync` 映射** | 不存在 | **新增（上游漏了）** | `prefill.cpp:399` 用 `cudaEventBlockingSync`；wave32 头 `hip_compat/cuda_runtime.h:39` 早有该映射、gfx906 专用头独缺 |

**H6 的发现过程**：首次构建在 `[118/139]` 失败，报
`/src/src/prefill/prefill.cpp:399:99: error: use of undeclared identifier 'cudaEventBlockingSync'`。
随后做了一次**映射审计**（对比两个 hip_compat 头的全部 `cuda*` define）：只差
`cudaEventBlockingSync` 与 `cudaDevAttrIntegrated` 两个；后者已被上游
`#if defined(__linux__) && !defined(STRATA_HIP_GFX906)` 正确 gate（`expert_cache.cpp:31`），故只补前者。

**升级后的自证**：`patched=2 (H5+H6) / verified=4 / PATCH_V3_OK`，跑两遍 => 第二遍 `patched=0`（**幂等**）；
Dockerfile 里 6 条复核 grep（H1/H6/H2/H3/H4/H5）**全中**（不中即构建失败）。

---

## 九、升级记录（0.1.40.2 -> 0.1.40.4，2026-10-08）

- 新版时间线：`0.1.40.1`(10-06 09:53) -> `0.1.40.2`(10-07 12:13) -> `0.1.40.3`(10-07 18:01) -> `0.1.40.4`(10-08 08:04)。
- 源码指纹：`strata-src-0.1.40.4.zip` sha256 `7d19b4d5cc8922d4e558f2cddec9a28b7595775ccfb4e6085b02287d95059300`（本机与 166 各自下载、哈希相同）。
- 补丁面与 0.1.40.2 **完全相同**（H1~H4 上游已修 / H5+H6 仍需打），补丁器 `patch_gfx906_402.py`(v3) 一字未改直接复用；
  `LLAMA_CPP_COMMIT` 也未变 => `llama.cpp-3cf0325.tar.gz` 复用。
- 镜像 `strata-gfx906:0.1.40.4`（`8f8f6e87e664` / 6.57 GB）；
  引擎 `/src/build-906/strata` = 24,841,832 B / md5 `b0020081b8292d48c4a555c5f036081b`。
- 切换：20:11:47 停 `strata166-402` -> 20:11:52 起 `strata166-406` -> **20:12:28 ready（35 s）**；
  复验 `verify_config.py` **PASS=15 / FAIL=0**；LIVE config md5 未变
  （`d2b10f0c4e8293ba010614c7acc70bea`，本波未改任何参数）。
- 中性验证：背靠背 A/B（0.1.40.4 vs 0.1.40.2，18,084-token 冷 prompt）实测两版不可分辨，见上面第 5 条。
- 全部细节与证据链：`deploy/W712_UPGRADE.md`；**后续方案：`deploy/W713_PLAN.md`**（`W712_PLAN.md` 已被取代）。

---

## 十、前缀复用的边界（B1 实测，2026-10-08）

> 环境声明：本节全部读数均在 **Z0=off（省电档）** 下取得；分辨力 = 预填 1.2-1.7%。 -  解释"为什么短对话每轮都慢"

`--prompt-cache-every` 的效果**只取决于 prompt 长度落在哪一档**（温 = 同一 prompt 末尾追加一句再发）：

| prompt 长度 | 现役 8192 的温 TTFT | 复用 `reused` | 说明 |
|---|---|---|---|
| **< 8k**（如实测 4,589 tok） | **10.47 s（≈ 冷 10.83 s）** | **0** | 整条 prompt 不足一个 prefill chunk（8192），**没有可对齐的边界 => 完全没有复用**。换 `16384`/`32768` 同样是 0 |
| **8-16k**（如实测 9,989 tok） | **5.87 s（冷 23.10 s，-74.6%）** | 8192 | 这是 `--prompt-cache-every 8192` **唯一的受益域**；`16384`/`32768` 在这一档得 0（温 23.07 / 23.15 s） |
| **> 16k**（如实测 23,939 tok） | **16.99 s（冷 50.10 s，-66.1%）** | 16384 | 8192 与 16384 等效；`32768` 归零（温 50.18 s，≈ 冷） |

**实用含义**：WorkBuddy 日常短会话（1k~6k prompt）**吃不到任何前缀复用**，每轮都要整条重预填
（4.6k 约 10.4 s）；`--prompt-cache-every` 改成别的值**救不了**，因为瓶颈是 prefill chunk 尺寸。
解法是把 chunk 调小（`--prefill 4096`，引擎 help 支持显式尺寸）：**B1b 已实测**，4.6k 会话温 TTFT 10.58 -> 3.59 s（冷预填 -11%），但**尚未采纳**（未在 0.1.41 复核、答案是否变未测）。现行方案与全量账见 `deploy/W713_PLAN.md`。
