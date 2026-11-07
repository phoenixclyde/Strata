# W775delta W9 ---- 并发吞吐面（`P97`）判定：**机制不可行**（0 发车）

> 触发：`W750 §4` 的 **W9 = 并发吞吐面**（`P97`）。原状态：`P97 = CANDIDATE`（原 REJECTED 系**使用面**判断 ---- 我们一直单流）。
> 机主令（2026-10-11 20:1x）「继续吧」。做法：只读 0.1.42 help + 源码 + 生产运行期实测。**0 发车、生产未动。**

## 0 结论（先行）

**本机机制上放不下** ---- 不是"没收益"，是"加不起"。判 `P97 -> REJECTED`（理由从"使用面"升级为**机制面**）。

三条独立证据：

1. **help 逐字**（`--batch N / --slots N`，`_w773_help_full.txt:93`）：
   > *"`--serve` (opt-in): up to N requests decode together in batch slots (2..8 normally; `--batch-mtp` waves more through eight-row windows), **each slot with its own session (VRAM like the main one)**; docs/BATCHING.md"*
2. **help 逐字**（`--batch-mtp`）：
   > *"`--batch` (opt-in, one GPU, needs `--mtp` and `--spec`): each slot also verifies one MTP proposal per window (`STRATA_BATCH_MTP=1` does the same); **needs VRAM per slot**"*
3. **本机运行期实测**（2026-10-11 20:1x，生产 `/metrics`）：**`vram_free_mib = 574`**、`expert_slots = 9761`、`expert_cache_mib = 22516`。
   => 连**一个** slot 都放不下（它要"与主会话同等"的 VRAM）。

## 1 为什么"VRAM like the main one"在本机是最硬的墙

| 面 | 本机现值 | 含义 |
|---|---|---|
| 卡 | MI50 **32 GB**（gfx906） | 单卡 |
| 专家缓存 | `expert_cache_mib = 22516`（**22.0 GiB**） | 已按 `--expert-cache auto` 顶到上限 |
| KV | `--kv k8v4`，262144 ctx（`cache_max_tokens=262144`）+ `--conversation-cache-mib 4096` | 主会话自己的 KV/会话缓存 |
| **剩余** | **`vram_free_mib = 574`** | **0.56 GiB** |

=> `--batch 2` 要**再要一份**"与主会话同等"的 VRAM，**差了两个数量级**。

## 2 唯一理论上的腾挪（并说明为何不做）

要让 `--batch` 落地，只能**牺牲单流**：把 `expert_cache_mib` 从 22.0 GiB 调小（`--expert-cache N` 或 `--vram-reserve-mib`），把 VRAM 让给 slot。
但它**同时**会：
- 把专家缓存逼小 => 更多 **adaptive swap**（`W26` 已证 miss 走 RAM 交换），**单流 decode 变慢**；
- 与我们已确认的"**现役配置 = 跑过最快的**"（W747 自比）**直接冲突**。

=> 这不是"打开一个开关"，而是**换一个使用形态并付出单流代价** => 只有在"确实要并发服务"的前提下才值得，而本机是**单用户专卡**。

## 3 与已有账目的关系

| 项 | 原判定 | 本件 |
|---|---|---|
| `P97` | CANDIDATE（原 REJECTED 系**使用面**） | **-> REJECTED（机制面）**：VRAM 放不下（证据 3 条） |
| `W9` | 未做（"前提要重议"） | **已判：机制不可行**；若将来换大显存卡或降专家缓存，需重开 |

## 4 复现

```bash
# 1) help 的两段（本卡二进制）
docker exec strata166-407 /src/build-906/strata --help | grep -A3 -E "^ +--batch N|--batch-mtp"
# 2) 运行期余量
curl -s http://127.0.0.1:8090/metrics | python3 -c "import json,sys;d=json.load(sys.stdin)['engine'];print({k:d.get(k) for k in ('vram_free_mib','expert_cache_mib','expert_slots')})"
#   => {'vram_free_mib': 574, 'expert_cache_mib': 22516, 'expert_slots': 9761}
```

## 5 局限

- 本件**未发车**：结论来自"help/源码的机制声明 + 本机余量实测"，**未实跑 `--batch`**（跑也必然 OOM）。
- `docs/BATCHING.md` 在本机源码树里**未逐节读**（只用了 help 的摘要句 + 源码解析点 `generate.cpp:1934/1935/1943`）；若将来要开并发，该文档是第一读物。
- "牺牲专家缓存换 slot"的**量化代价未测**（本件不作数）---- 那是另一条路，需另立靶。
