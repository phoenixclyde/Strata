# W868 · 那 148 ms 收窄到 185 行：`best()` 无罪，代价在其后的「取回/校验/回放」段

> 2026-11-01 22:16–22:40。第八次部署（`0.1.55q`，tag `mi50-0.2.9-r24`）。
> 本轮只加打点，不改任何行为。

---

## 0 三句结论

1. **`tr()` 之前只在启动时读一次标记文件**（serve 循环之前），所以 r19 之后加的点在活着的服务上从来不打印；
   改成**每次调用 stat** 后，`touch` 就能实时开、`rm` 就关。`[实测]`
2. **相邻两个 `tr()` 的间隔是 0.0 ms** ⇒ 之前怀疑的「stderr 背压」不成立，时间是真的。`[实测]`
3. 那 148–164 ms **不在 `conversations.best()` 里**：`before best → taken → validated → streams ready` 全程 **0.0–0.1 ms**，
   真正的位置被压到 **`streams ready` → `cache lookup done` 这 185 行（14388–14572）**。`[实测]`

---

## 1 打点时间线（同一条请求，ms）

```
r0                 6994.9
kv ensured         6994.9   (0.0)
kv ensured 2       6995.0   (0.0)   ← 相邻对：不是 stderr 背压
before best        6995.0   (0.0)
taken              6995.0   (0.0)   ← conversations.take() 取出停泊会话
validated          6995.1   (0.1)   ← conversation_snapshot_validate
streams ready      6995.1   (0.0)   ← 每卡 cudaMemGetInfo + copy-stream 探测
cache lookup done  7158.9   ★ +163.8
mounted            7183.5   (+24.6) ← 快照挂载
checkpointed       7196.8   (+13.3)
request            7196.8
prompt done        7250.0   ← 读 53 ms（窗口路径）
```

⇒ `rest` = **163.8 + 24.6 + 13.3**，与摘要里的 `rest 202.0` 对得上（另有 ~0.3 ms）。
被排除的：`best()`（0.0）、`take()`（0.0）、快照校验（0.1）、每卡 `cudaMemGetInfo` + 流探测（0.0）。

---

## 2 剩下那 185 行里有什么（源码，待下一个点）

`14388–14572` 之间的可疑条目（已按「会不会等设备」排序）：

| 行 | 代码 | 判断 |
|---|---|---|
| 14394 | `for (k < restore_free.size())` 比较空闲显存 | 纯计算 |
| 14402–14403 | `incoming.reset(); conversations.put(std::move(retry))` | 归还快照，move |
| 14411 | `conversation_snapshot_validate(*donor, …)` | **只在 borrow 分支**；本次 `borrow=false`，应未执行 |
| 14434–14438 | `park_held` / `park_worth` 计算 | 纯计算 |
| 14468 | `incoming.emplace(conversations.take(at))` | 另一分支的第二次取回 |
| 14525–14549 | `sc.erase(...)` 检查点链维护 | vector erase |
| 14571 | `conversation_park_vram_release_all()` | **有设备调用，但在 `kvg_ensure` 失败后的重试分支** |

> **【AUDIT20：本表漏了真凶】** 表里没有 `park_current(...)` —— 而 W869 证明 163.8 ms 里 **147.3 ms 就是它**，
> 并且 `park_vram_release_all()` 被判成「只在重试分支」进一步把 park 方向排除掉了。
> 最终定位靠的不是新打点，而是**对齐引擎自己已经打出的 `parked 1906 tokens in 147.3 ms`**（见 W869 §1）。

⇒ 下一个打点放在 **14438 之后**（park_worth 之后）和 **14549 之后**（链维护之后），即可把 163.8 一分为二。
**这两处都不需要新的部署范式，还是同一套 `tr()`。**

---

## 3 今天的部署账（八次，全部可回滚）

| 版本 | tag | 改动 | 停服 |
|---|---|---|---|
| 0.1.55j | r17 | solo 请求打四段拆分；标记文件 | 241 s |
| 0.1.55k | r18 | 标记改到请求末尾判定 | 232 s |
| 0.1.55l | r19 | r0→request 四个点 | 253 s |
| 0.1.55m | r20 | 再加两点 + 去掉锁存 | 239 s |
| 0.1.55n | r21 | `/data/strata-short-read` 文件开关 + best 前点 | 247 s |
| 0.1.55o | r22 | 修累加器被 `trace` 挡住 | 240 s |
| 0.1.55p | r23 | `tr()` 逐次判定 + 相邻对 + resume decided | 245 s |
| 0.1.55q | r24 | take / validated / streams ready 三点 | 243 s |

**每次** `weights = 499 native projection matrices, 3619.14 MiB` 逐字相同；`/health ok`；decode 稳在 48–55 tok/s。
合计停服 ≈ **32 分钟**（八次 × 4 分钟）。这条流水线本身是这轮最贵的资产：**改引擎 → 30 s 编译 → 18 项静态门 → 4 分钟部署 → 打点即读**。

---

## 4 下一步（两种走法，选一个）

**A. 继续钉死这 163.8 ms**（一次重启 + 两个打点）：它占短追问 TTFT 的 **62%**（5 token 时 164/262），
而且很可能是一段可以在 `Prefill::relayout`/缓存 bookkeeping 里一次性修掉的东西。

**B. 回 decode 主线**（机主的原始目标：单流 decode TPS、带宽利用率）。多轮 TTFT 这条线今晚已经产出：
拆成 164 + 25 + 13 + 读，且**三个假设被判否**（4 KB 页、借槽回填、`--short-read 0`）。

我倾向前者再花一次重启把线收干净，然后整条转回 decode——因为 62% 这种量级的单项，放着不命名，
下次又会有人（包括我）从零猜起。
