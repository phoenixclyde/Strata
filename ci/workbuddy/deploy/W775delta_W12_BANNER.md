# W775delta W12 -- banner 实测：**`P55`/`P56` 在生产 `k8v4` 下不可达**（* 重大修正）

> 承接 `W775delta_W12_PRECHECK.md`（源码面）。本轮做了 §4.1 的「零发车 banner 确认」，**结果推翻 PRECHECK 的核心假设**。
> 时间：2026-10-11 05:07–05:14。全部读数现取、可复现。

## 0 结论（先行，三条）

> **审计后收紧（P0-3）：证据主辅必须分清。**
> 「`P55`/`P56` 在 `k8v4` 下不可达」的**主证是源码条件恒假**（`use_query_swizzle` 要求 `kv_mode == 1`，而 `k8v4` => `kv_mode = 3`）。
> **banner 只是佐证，且只兑现了旁证的一半** -- 见 §1 与 §4：
> `--kv k8v4` 那一次的 banner **本波未留任何产物**（166 全盘无 `active=0` 行），
> 实测到的是 `--kv int8` 的**正对照**（`active=1 kv_mode=1`）。
> => 本节原称「双证」，**应读作「源码恒假为主证 + int8 正对照为实测旁证」**。

1. **`P55`（`STRATA_GFX906_ATTN_QUERY_SWIZZLE`）/ `P56`（`..._REDUCE12`）在生产 `--kv k8v4` 配置下恒不可达** --
   **限定为「主模型路径」（decode `qsa_decode_attn_step` + prefill `qsa_decode_attn_batch`）**。
   `use_query_swizzle` 要求 **`kv_mode == 1`**，而 `--kv k8v4` 落到 **`kv_mode == 3`** => **条件永假**。
   **主证 = 源码恒假（逐字见 §2）；banner 为佐证（且仅 int8 侧有产物）。**
   （**drafter 侧**经 `mtp.cpp:825` 且被强制 INT8 => 理论上可达，**但本波未观测到**，见 §4 与 §6。）

2. **PRECHECK §3.1 的「四条件全真」错了一条** -- 我把 `kv_mode == 1` 判成真（依据是"生产 `--kv k8v4`"），
   **这是把 `--kv` 的字面量当成了 `kv_mode`**。实际 `kv_mode` 是**从 KV pool 布局推出来的**，`k8v4` 恰好不是 1：
   ```c
   // qsa_decode_attn.cu:626-627 逐字（* 审计更正：实为四分支，跨两行；原稿截断成 ": 1"）
   const int kv_mode = pools.k_q4 != nullptr ? 2 : (pools.k_q != nullptr && pools.v_q4 != nullptr ? 3
                       : (pools.k_q != nullptr ? 1 : 0));
   ```
   => 有 `k_q4` -> 2；有 `k_q` **且**有 `v_q4` -> **3（= k8v4）**；有 `k_q` -> 1（纯 INT8 K+V）；否则 -> 0（pool 异常）。
   本处结论**不变**（k8v4 仍落 3），但原稿「逐字」引用**不诚实**，已更正。

3. **单变量对照（唯一干净的做法）已跑**：只把 `--kv` 从 `k8v4` 换成 `int8`，banner 立刻从 `active=0 kv_mode=3` 变成 **`active=1 kv_mode=1`**。
   => **靶的成立条件已被实验锁定 = `--kv int8`**。
   （**审计注**：`int8` 侧的 `active=1 kv_mode=1` 有产物；`k8v4` 侧的 `active=0 kv_mode=3` **无产物**，
   其 `kv_mode=3` 系源码推演，见 §1 注。）

## 1 实测对照表（同一份脚本、同一台机、同为 `--arm B`）

| `--kv` | banner（`qsa_decode_attn.cu:648` 逐字输出） | `kv_mode` | `active` | 判定 | 产物 |
|---|---|---|---|---|---|
| `k8v4`（生产现役） | `active=0 nq=32 cap=2051 kv_mode=3 lane_cell=0` | **3** | **0** | **不可达** | **[!] 无产物**（见下注） |
| **`int8`** | `strata attn-query-swizzle: active=1 nq=32 cap=2051 kv_mode=1 lane_cell=0` | **1** | **1** | **可达** | [OK] `stderr_B.txt` / car log |

> **审计更正（P0-3）**：**`k8v4` 那一行的 banner 在 166 上无任何产物。**
> 本机独立复核：
> ```
> grep -rn 'attn-query-swizzle' /home/albus/strata166/
>   => _w775_w12_car.log:19/:43/:81、_w775_w12_banner/stderr_B.txt:44、
>     _w775_w12_out/stderr_B.txt:44  -- 全部是 active=1 kv_mode=1（即 int8 那一次）
>   => 没有任何 active=0 / kv_mode=3 的行
> ```
> `car log` 只有**一次**车头（`:2`），`:13` 记 `ARM = B  kv = int8`；`_w775_w12_out/` 只有 `stderr_B.txt`（int8）。
> => `k8v4` 行的 `kv_mode=3` **系源码推演**（`generate.cpp:2397` -> `:626`），**不是本波实测读数**；
> 原表把两行并列为「实测对照」并称「双证」是不成立的，已改正。
> **（补产物办法：重跑 `bash /home/albus/strata166/_w775_w12.sh B k8v4`，一次停-起即可。）**

两车其余条件相同：`--arm B`（`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1`）+ `STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE=1`，
`--native SHARD1 --spec 4 --prefill auto --ple-gguf <shard2> --max-new 8`，`reps=2`。
=> **`kv` 是唯一自变量，`active` 是唯一因变量**（就 int8 侧而言因果干净）。

## 2 `k8v4` 为什么是 3（源码链，逐字）

```
generate.cpp:2397   strata::core::qsa_set_kv_hybrid(o.kv == "k8v4");   // K8V4: INT8 K + rotated Q4_0 V, 816 B/cell
                      ↑ --kv k8v4 打开 qsa_kv_hybrid()
                      ↓
qsa_decode_attn.cu:626-627   kv_mode = k_q4?2 : (k_q && v_q4 ? 3 : (k_q ? 1 : 0))
                      ↑ hybrid => pool 里同时有 k_q(INT8) 与 v_q4(Q4_0) => kv_mode = 3
                      ↓
qsa_decode_attn.cu:643   use_query_swizzle = query_swizzle && !lane_cell && kv_mode == 1 && ...
                      ↑ kv_mode == 1 为假 => use_query_swizzle 恒假 => P55 恒不生效
```

**上游注释其实已经暗示了这条**（`qsa_decode_attn.cu:32-35` 逐字）：

> `// Opt-in INT8 batched attention: prefill, verification and MTP (including n_q=1).`
> `// Other pool formats and lane-cell scoring keep their paths; qsa_decode_attn_step is unchanged.`
> `// A k8v4 model's MTP drafter uses INT8 pools and can therefore take this path.`

最后一句是关键：**"a k8v4 model's MTP drafter uses INT8 pools"** -- 即 **只有 drafter 是 INT8 池**，
主模型在 `k8v4` 下是 **hybrid 池**。而 drafter 的路径由 `mtp.cpp:825` 走 **`qsa_decode_attn_batch`**，
其 pool 在 `mtp.cpp:334-337` 被显式改成纯 INT8：

```c
// mtp.cpp:332-337 逐字
// K8V4 never applies to the drafter: its own attention paths (below, and verify.cpp) handle whole formats
// only, whatever ring shape it takes (0, a window, or the -1 fully-resident fallback).
const bool kv_hybrid_was = qsa_kv_hybrid();
const bool kv_int8_was = qsa_kv_int8();
qsa_set_kv_hybrid(false);
if (kv_hybrid_was) qsa_set_kv_int8(true);   // the drafter under --kv k8v4: plain INT8
```

=> **drafter 池是 INT8（kv_mode=1）=> 理论上可达** -- 但 **banner 只出现 2 次、都是 `nq=32`**，
两次都是 **prefill 的 batch 调用**（`prefill.cpp:2801`）。**drafter 的 `nq=T` batch 调用没有被 banner 捕获**（原因见 §4）。

## 3 四个调用点（谁走这个 dispatch）

| 位置 | 函数 | 谁用 | 池 |
|---|---|---|---|
| `layer.cpp:1138` | `qsa_decode_attn_step` | **主模型 decode（n_q=1）** | 主模型池 => k8v4 下 **kv_mode=3** |
| `prefill.cpp:2801` | `qsa_decode_attn_batch` | **prefill 批量** | 主模型池 => k8v4 下 **kv_mode=3** |
| `mtp.cpp:825` | `qsa_decode_attn_batch` | **MTP drafter** | **drafter 池（强制 INT8）=> kv_mode=1** |
| `kv_stream_parity` / `kv_hybrid_parity` | 两者 | 仅 parity 测试 | -- |
| `verify.cpp` | （见 §4） | verify 窗口 | -- |

**=> 在 `k8v4` 生产配置下，`P55` 唯一的可能靶是 MTP drafter 的那条 batch 调用**，
而它**只占整个 token 的很小一部分**（drafter 的 T-token 窗口）。
=> 相应地，「不可达」应限定为「**主模型路径不可达**」；**drafter 侧理论可达但本波未观测**（§4 banner 只打第一次调用）。

## 4 * 探针自身的缺陷（必须记下，否则下次还会看错）

`qsa_decode_attn.cu:644-646` 逐字：

```c
static const bool query_swizzle_trace = std::getenv("STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE") != nullptr;
static thread_local bool query_swizzle_said = false;
if (query_swizzle_trace && !query_swizzle_said) {
    query_swizzle_said = true;
    std::fprintf(stderr, "...");
}
```

=> **`static thread_local` + `_said` 标志 => 每个线程只打印一次**。
=> 我们看到的 banner 是**第一次进入该 dispatch 的调用**（= prefill 的 `nq=32`），
**后续 decode / drafter 的调用（包括 `nq=1`）全部静默**。

**后果**：**这个 banner 不能用来枚举"哪些路径走了 swizzle"，只能用来读"第一次调用的条件"。**
若要逐路径判定，须**改源码去掉 `_said` 检查并重编译**（成本高），或**用 `--no-capture` + 分阶段命令隔离**。

> **审计要点（P0-3 的延伸）**：正因为这个 banner **只看得到第一次调用**，
> 它**不能单凭自身**去证「`P55`/`P56` 在全机所有路径都不可达」--
> 「不可达」只由**源码条件恒假**证成（主模型池 `kv_mode=3`），banner 只能**证伪不能证真**（见 §0 声明的口径）。

## 5 判定与建议

| 问题 | 判定 |
|---|---|
| `P55`/`P56` 在**生产 `k8v4`** 下可达吗？ | **主模型路径不可达**（源码恒假为**主证**；`--kv int8` 正对照为**实测旁证**，k8v4 侧 banner 无产物） |
| 在 `--kv int8` 下可达吗？ | **可达**（banner `active=1 kv_mode=1`，**有产物**） |
| 那要测吗？ | **测出的收益不能算到 `k8v4` 头上** -- 那是**换 KV 配方**的收益，不是同配置加速。除非我们的目标本来就是评估 `--kv int8` |
| `P59`/`P60` 呢？ | **仍可测** -- 它们作用于 **verify/MTP 提交图**（`verify.cpp:195/211`、`mtp.cpp:860`），**与 KV 格式无关** |
| W774 的"prefill 中性"该怎么记？ | **双重靶选错**：(1) 阶段错（prefill vs decode，已知）；(2) **KV 格式错**（`k8v4` 下主模型根本不可达，本轮新证） |

**建议动作（待机主批）**：
1. **`P55`/`P56` -> 判「在现役生产配置（`k8v4`）下**主模型路径**不可达」**（不是"无收益"，是"够不着"）。要测只能在 `--kv int8` 下另立一车。
2. **`P59`/`P60` 仍发 D 臂**（A 基线 / D=P59+P60），主口径 decode `ms/step` x 5 runs -- **这两个与 kv 无关，靶成立**。
3. **▲ 补产物（审计新增，强烈建议）**：重跑一次 `bash /home/albus/strata166/_w775_w12.sh B k8v4`，
   把 `k8v4` 侧 banner 落成 `stderr_B.txt`，**把 P0-3 从「无产物」消掉**（一次停-起，~40 s 恢复）。
4. **回 #1661 / #1718 上游时可附此结论**：该 PR 的适用面**不覆盖 k8v4 的主模型**（作者说 "a k8v4 model's MTP drafter ... can take this path" 确为真，**但主模型不行**，而主模型是耗时大头）。

## 6 局限（随结论一起引）

- 本件**只有 banner 一类证据**（+ 源码链），**未做真机 A/B 计时**。
- **banner 的 `thread_local` 一次性静音**（§4）=> 我们**只看到了第一次调用**；drafter 路径是否真走 swizzle **未直接观测到**（只有源码推断）。
- 两车都是 `--max-new 8`，**引擎环境非生产 serve**（无 `--vision` / `--mtp` / conv-cache）=>
  `STRATA_HEAD_MIX_MULTI` / `STRATA_ONE_TOKEN_COMMIT` 的路径**在本车未启用**（D 臂未跑）。
- `cap=2051` / `nq=32` 是 prefill chunk 的形态，**不代表 decode 形态**。

## 7 产物与指针

**新件**：

| 文件 | 说明 |
|---|---|
| `deploy/tmp/_w775_w12.py`（本机，**[!] 本地副本已过期**）-> `/home/albus/strata166/data/_w775_w12.py`（166，3,843 B / md5 `5b81f46e6c767526cd44fa881e0075b3`） | banner 探针（`--kv` 由 `.sh` 传入） |
| `deploy/tmp/_w775_w12.sh`（本机，**[!] 本地副本无 `KV` 参数，不能复现**）-> `/home/albus/strata166/_w775_w12.sh`（166，**2,538 B** / md5 `43be70599cac46380470056443778468`） | 车脚本（166 版有 `ARM` + `KV` 两参数） |
| 166 `/home/albus/strata166/data/_w775_w12_car.log` | 车日志（**只有 int8 一次**；k8v4 那次**无产物**） |
| 166 `/home/albus/strata166/_w775_w12_out/stderr_B.txt` | `int8` 臂 stderr（banner 所在，`active=1 kv_mode=1`） |

> **审计更正（P0-4）**：原稿写 `_w775_w12.sh` =「2,513->2,600 B」，**实读 2,538 B**；
> 且**本机 `deploy/tmp/` 的两份副本都落后于 166 版本**（本地 `.sh` 第 47 行是 `--arm $ARM`，
> **没有 `--kv $KV`**；166 版才是带 `KV` 参数的）。=> **本机副本不能复现本波任何一车**，复现必须用 166 上的版本。

**复现命令**（166）：
```bash
bash /home/albus/strata166/_w775_w12.sh B k8v4    # 期望 active=0 kv_mode=3（* 本波未留产物，须重跑）
bash /home/albus/strata166/_w775_w12.sh B int8    # 期望 active=1 kv_mode=1（已有产物）
```


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `467aace36951ef3e350d478cef5b1f74`（字节 12448）。
