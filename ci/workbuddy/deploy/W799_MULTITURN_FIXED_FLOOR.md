# W799 多轮场景的真地板：每轮约 900 ms 与 token 数无关

- 日期：2026-10-25 20:37-21:45
- 起点：`W798` 量出多轮 decode 占 64-83%，但**prompt 侧的增量 token 单价没人算过**。本轮算清了，并在它下面找到一块从未被单独优化的地板。
- 结论：**没有采纳参数**；`--conversation-cache-park-gain=256` 记为 PENDING（单样本、收益 10%、但地板未动）。
  **【AUDIT9】表混源已改同源；【W801】三样本复测证明效应只在一个窄带（见 §3.2），最终处置 REJECTED。**

> **【AUDIT9 更正 2026-10-25 22:5x】§3 的 A/B 表混源，结论方向反了一格：**
> `gain=0` 那一列（917.8 / 1,564.3 / 2,187.9 / 3,086.6 / 4,155.8 / 4,345.4）**不是同一次 A/B 的 A 臂**，
> 而是重启前另一轮 floor 扫描。`w799_gain_…204625` 里 `=== GAIN 0` 臂实测是
> **1,148.4 / 1,580.4 / 2,203.6 / 3,480.5 / 4,000.6 / 4,359.4**。同源重算：

> | read | 文档 Δ | **同源 Δ** |
> |---|---|---|
> | 46 | +1.8% | **-18.6%** |
> | 108 | -13.6% | -14.5% |
> | 237 | -10.8% | -11.4% |
> | 529 | -10.3% | **-20.5%** |
> | 1,008 | -6.2% | -2.6% |
> | 1,954 | +3.3% | +3.0% |
>
> ⇒ **"地板一格没动"是错的**（同源下 read=46 是 -18.6%）；但**每档 n=1**，不能据此采纳。
> **【W801 三样本复测已做完】**：效应只出现在 read≈277（-10.0%），read≈79 是 **+3.1%**、read≈547 **+2.0%**
> ⇒ **P126 = REJECTED**（见 §3.2）。同源只解决混源，不解决样本量。
> 另：本文 §1 的"read=46 花 917.8 ms"与 §3 的表同源问题一致，引用时应改用同源数 1,148.4。

---

## 1 起点：增量 token 的单价是冷读的 14 倍

新建 8K 会话，然后只变 `read` 长度（同一会话、`reused` 固定 7,577）：

| read | prompt_ms | ms/token | 相对冷读 |
|---|---|---|---|
| 46 | **917.8** | **19.95** | **13.8×** |
| 108 | 1,564.3 | 14.48 | 10.0× |
| 237 | 2,187.9 | 9.23 | 6.4× |
| 529 | 3,086.6 | 5.83 | 4.0× |
| 1,008 | 4,155.8 | 4.12 | 2.9× |
| 1,954 | 4,345.4 | 2.22 | 1.5× |
| （参照）冷读 7,581 | 11,517.2 | **1.52** | 1.0× |

单价随 read 单调下降 ⇒ 存在**与 token 数无关的固定成本**。外推截距约 **900 ms**：
**46 个 token 花掉了冷读 694 个 token 的时间。**

`read=16` 那一档更极端：`prompt_ms=569.3`，端到端 0.77 s —— 而它**根本没有 `strata prefill timing` 行**
⇒ 这个量级的请求**不走 prefill chunk 路径**，所以那 569 ms 不是"prefill 计算"，是**请求级开销**。

---

## 2 地板的一半找到了：每轮 park 一整份 330 MB 的 KV snapshot

引擎逐字（`grep "conversation cache:"`）：

```
parked 7589 tokens in 222.9 ms; parked=2 bytes=577543548 evictions=0 snapshot_bytes=330210608 reused_kv_bytes=0
parked 7631 tokens in 205.9 ms; parked=2 bytes=696132956 evictions=0 snapshot_bytes=448800016 reused_kv_bytes=0
parked 7693 tokens in 276.5 ms; parked=3 bytes=1145726044 evictions=0 snapshot_bytes=449593088 reused_kv_bytes=0
```

三件事：

1. **每轮 park 一次，222-314 ms，写 330-460 MB 到 RAM**（`--conversation-cache-mib 4096`、4 slots）。
   下一轮再读回 ⇒ **park + unpark ≈ 450 ms**，正好占地板的一半。
2. **`reused_kv_bytes=0` —— 增量保存的复用一次都没生效。** `conversation_snapshot.cpp:178` 有"只保留未改动页"的机制，
   但每一轮都是**全量**写。这本身是个可疑点（保存路径的优化形同虚设），本轮没深挖。
3. `parked` 从 1 累加到 4 后 `evictions=1/2` —— 这是**我前面十几个测试脚本堆出来的历史会话**。
   **但重启清空后重测，地板几乎一样（917.8 vs 1,000.1）⇒ 地板是真的，不是测试污染。**
   （这一条必须写下来：今天已经三次栽在"测试构造先排除"上。）

### 2.1 为什么每轮都 park

`src/program/generate.cpp:12744` 的注释逐字说明了这是浪费：

> `--conversation-cache-park-gain N`: a park now would supersede the entry `parked_prefix_tokens()` reports …
> a conversation that advanced fewer than N tokens since then keeps it … and **re-parking writes the whole snapshot
> only for the next turn to drop it again**. 0 (the default) parks every turn, as before.

默认 0 ⇒ **每轮都 park**。我们的多轮每轮只前进 200-500 tokens，正是它说的那种情况。

---

## 3 实测 `--conversation-cache-park-gain`

| read | gain=0（同源） | gain=256 | 差 |
|---|---|---|---|
| 46 | 1,148.4 | 934.4 | **-18.6%** |
| 108 | 1,580.4 | 1,351.7 | -14.5% |
| 237 | 2,203.6 | 1,952.5 | -11.4% |
| 529 | 3,480.5 | 2,767.6 | **-20.5%** |
| 1,008 | 4,000.6 | 3,897.9 | -2.6% |
| 1,954 | 4,359.4 | 4,488.3 | +3.0% |
| park 行数 | **8** | **5** | -3 次 |

（`gain=0` 列原先写的是 917.8 / 1,564.3 / 2,187.9 / 3,086.6 / 4,155.8 / 4,345.4 —— 那是**重启前**另一轮扫描，
不是本次 A/B 的 A 臂。已按 `w801` / `AUDIT9` 改为同源值；每档仍是 **n=1**。）

它确实减少了 park（8→5）。**但每档只有 1 次样本，本表不足以下任何结论** —— 见 §3.2 的三样本复测。

⇒ **park 不占地板**（`W800` 用 `STRATA_TRACE` 逐段对账已证：park 发生在响应交付之后，不在 t0..t1 内）。
剩下的约 450 ms 是别的请求级开销（`read=16/26` 没有 prefill timing 行，说明连 prefill 路径都没进）。

### 3.2 三样本复测（2026-10-25 21:54-22:1x，`W801`，交错 A B B A A B）

8K 会话、`reused=7,576`、每档 n=3，判 `prompt_ms` 中位：

| read（目标/实读） | gain=0 中位 [范围] | gain=256 中位 [范围] | Δ |
|---|---|---|---|
| 46 / **79** | 1,409.0 [1381.6-1413.5] | 1,452.0 [1389.1-1465.3] | **+3.1%** |
| 237 / **277** | 2,356.4 [2346.9-2357.1] | 2,121.4 [2119.4-2126.5] | **-10.0%**（区间不重叠） |
| 529 / **547** | 3,098.0 [3073.0-3144.6] | 3,158.6 [3089.4-3158.9] | **+2.0%** |
| 1,954 / **1,909** | 4,326.1 [4313.1-4550.1] | 4,285.2 [4272.7-4412.2] | -0.9% |

**只有 read≈277 那一档真的赢（-10.0%，两臂区间不重叠）**；聊天最常落在的 read<150 那一档反而 **+3.1%**，
read≈550 也 **+2.0%**。

**处置：REJECTED（P126 关闭）。** 效应存在但只在一个窄带，且不在真实用量最大的一档；
单参数、无质量风险的 A/B 也证明它不值得进生产。

**附带教训（写进 `AUDIT9` 规则 V）**：`AUDIT9` 把本表改成同源后推出"地板 -18.6%"，方向是对的、算术是对的，
**但 n=1 仍然是 n=1** —— 三样本复测在 read=79 上给出的是 +3.1%。同源只解决"混源"，不解决"样本量"。

### 3.1 事故：config 被写入脏参数（已修）

`set_gain` 的实现：
```python
a = [x for x in a if x != '--conversation-cache-park-gain']   # 删了参数名
if '--conversation-cache-park-gain' in a: ...                  # 这句永不成立（已删）
if g != '0': a += ['--conversation-cache-park-gain', g]        # 旧值 '256' 留在原位
```
⇒ `gain=1024` 时 args 变成 `[..., '256', '--conversation-cache-park-gain', '1024']`，孤立数值留在中间。
**已清理并复核**：`gen_config --live` **无差异**（= 与 register 权威完全一致）、`verify_config` **PASS=34 FAIL=0**。

---

## 4 还有一条没用的机制：`pin=`（需要客户端配合）

`generate.cpp:12735` 逐字：

> `pin=N`: this request resumes exactly at the pinned shared prefix of the conversation the session holds
> (a sibling query of the last one). What the last query added past it is its private suffix — a few dozen tokens,
> **cheaper to read than the prefix's whole K/V is to copy to the host** — so it is **not parked**: N queries keep
> one prefix.

这正是多轮对话的形态（同一前缀 + 每轮几个新 token）。触发条件（逐字）：

```cpp
if (req_pin > 0 && req_ckpt && o.prompt_cache >= 3 && !from_live && !incoming && slot_source < 0 &&
    resume == req_pin && live_ok)
    for (const ConvCheckpoint& c : checks)
        if ((int64_t) c.ids.size() == resume && c.pinned) pin_sibling = true;
```

**要点**：`pin=` 是**请求侧参数**，客户端要在请求里带 `pin=N`。我们的 python 客户端没带，
机主实际用的前端（OpenWebUI 之类）也不会带 ⇒ **这条机制在当前用法下用不上**。
要利用它，得改服务端的 admission 逻辑、或者让前端配合 —— 都不是配置面能解决的。

---

## 5 这一轮改变了什么判断

1. **多轮的瓶颈不在"计算"，在"搬与启动"**：每轮约 900 ms 里，约 450 ms 是 330 MB KV snapshot 的 park/unpark，
   约 450 ms 是请求级开销。而真正的 prefill 计算只有 `1.5-1.8 ms × read`。
   ⇒ 对"每轮 200-500 新 token"的实际用法，**固定成本占 prompt 时间的 50-70%**。
2. **今天所有的 prefill 优化（-30.6%）在多轮场景下的收益被摊薄**：那些优化缩短的是 `1.44 ms/token` 那一项，
   而多轮每轮只走 200-500 个 token ⇒ 省下的是 0.4-1.0 s 里的一小部分，不是 11 s 里的一大半。
3. **`reused_kv_bytes=0` 是一个新挂账**：增量快照的"保留未改动页"从没生效过，每轮全量 330 MB。

---

## 6 生产状态（未变）

`strata166-407` / `strata-gfx906:0.2.4p4` / 0.1.49.2 / slots **9901** / vram_free 606 / governor schedutil /
**env 10 项**（无调试开关）/ args 无 `--conversation-cache-park-gain`（已清理）/ `verify_config` PASS=34 FAIL=0 /
`gen_config --live` **无差异**。

## 7 下一轮

1. **`park-gain` 复测**（PENDING→判）：修好 set_gain，`gain=0 / 256 / 512`，每档 3 次，判据 >5%。
2. **地板剩下的 450 ms 是什么**：`read=16` 没有 prefill timing 行 ⇒ 需要 `STRATA_DECODE_TIMING` 或 strace 级别的时间线，
   看请求进入后到第一个 prefill chunk 之间在做什么。
3. **`reused_kv_bytes=0`**：查 `conversation_snapshot_save` 的 incremental 路径为什么一次都没命中。
4. 内核工程（MMQ 36.4% / attn 19%）—— 仍然挂着，但在多轮场景里它只影响 `1.5 ms × read` 那一项。
