# -*- coding: utf-8 -*-
"""追加 [W-Strata-31]：Strata serve 的 API 字段实测矩阵（WorkBuddy 接入用）。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-31] Strata serve 的 API 字段实测矩阵（供 WorkBuddy 接入；全部用真实请求验过）

服务：`http://192.168.50.166:8090/v1` · 模型 id `qwen3.8-flash-next-ud-iq4_xs` · `n_ctx 131072`。
探针脚本 `D:\\strata166\\scripts\\_probe_api166.py`；清单 `D:\\strata166\\configs\\workbuddy-strata166.md`。
**注意：Windows 侧要用宿主 IP `192.168.50.166:8090`，不要用容器内网 `172.17.0.6`。**

| 字段 | 实测 |
|---|---|
| `GET /v1/models` | 200；`{"id":"qwen3.8-flash-next-ud-iq4_xs","meta":{"n_ctx":131072},"input_modalities":["text"]}` |
| `reasoning_effort` | **`none` / `low` / `medium` / `high` / `xhigh` / `minimal` 全部 200**（服务端 `POST /settings` 的校验集是 `none|low|medium|high`，但请求级不拒 `xhigh`/`minimal`） |
| 关思考 | `reasoning_effort: "none"` ⇒ 无 `reasoning_content`，prompt **59 → 19** token（`minimal` 同效） |
| 默认（不传） | 会思考（98 字 `reasoning_content`），= `xhigh`（模板自带 xhigh 句在顶部） |
| **tools / function calling** | **支持**：`finish_reason = "tool_calls"`，标准 OpenAI `tool_calls`（`call_3549cf…` + `{"city":"Shanghai"}`） |
| **图片输入** | **400**：`this server was started without the vision encoder`（未加载 mmproj） |
| `max_tokens` | 8192 / 65536 → 200；**200000 → 400** `prompt + max tokens exceeds the context (131072); requests are never truncated` ⇒ **输入+输出必须 ≤ 131072，服务端不截断** |
| `POST /v1/messages`（Anthropic 方言） | 200，返回 `content:[{"type":"thinking",...}]` |
| 采样键透传 | `temperature`(0..2) / `top_p`(0<p≤1) / `top_k`(1..64) / `seed` / `max_tokens`（正整数）；引擎自身默认 **greedy** |
| 鉴权 | **无**（启动日志 `WARNING: no API key`），任何 API key 值都过；要收口把 `"api_key"` 写进 `/data/strata-ud-iq4_xs.json` |

**推荐填法**：思考✅ / 允许关思考✅ / 默认 `medium` / 支持 low·medium·high / 工具调用✅ / 图片❌ /
输入 `98304` + 输出 `32768`（= 131072）。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
