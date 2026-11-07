# W869 · 那 147 ms 找到了：它在下一次请求里执行——上一次会话的「停放」（省下的 92 ms 实为 move，非 async）

> 2026-11-01 22:40–23:10。第九次部署（`0.1.55r`，tag `mi50-0.2.9-r25`）。
> 本轮**把一个行为开关从「HIP 上不可能」改成「可测」，并实测省下 75–92 ms/次续写**。

---

## 0 三句结论

1. **`rest` 里那 147–197 ms 就是「停放上一个会话」的耗时**，而且它发生在**下一次请求内部**（不是生成之后）：
   `streams ready`(690641.8) → `parked 1906 tokens in 147.3 ms` → `cache lookup done`(690789.2)，
   **引擎自己打的 147.3 与缺口 147.4 逐字对得上**。`[实测]`
2. 这条路径的异步版本（`ParkAsync`）**在 HIP 上被 `park_async_on()` 硬编码 `return false` 屏蔽**，
   在 CUDA 上也只是 opt-in。打开后：`parked` **147.3 → 74.8 ms**，`rest` **196.5 → 104.8 ms**（省 ~92 ms/次）。`[实测]`
3. 只省一半，是因为 `ParkAsync` 走 **4 MiB staging 两跳**：VRAM→stage 仍在调用线程上同步做，
   搬进后台的只是 stage→镜像。**再省需要把整幅 D2H 也排到私有流。**`[源码]`

> **【机制更正 · W870】上面这句「异步省了一半」是错的归因。** 本机 stage **根本分配不出来**：
> `conversation_park_async_begin` 要求 `cudaMemGetInfo >> fr >= want + 3 GiB`（want = need 向上取整到 64 MiB ≈ 320 MiB），
> 而本机空闲只有 0.8 GB ⇒ 直接 `return false`，走同步路径。真正省下那 92 ms 的是同一个 env 打开的另一条分支
> `park_drops`：**把本次要被丢弃的检查点「搬」进停放镜像，而不是复制**（`generate.cpp:10738-10749` → `conversation_snapshot_save(..., &moved)`）。
> 一个 1900-token 会话的检查点 KV ≈ 260 MB，省两次复制 ≈ 50–90 ms，与实测同量级。

---

## 1 定位过程（打点法，九次部署的收敛）

| 轮次 | 打点 | 结论 |
|---|---|---|
| r19 | r0 / cache lookup / mounted / checkpointed | 缺口 174.6 ms 在「读之前」 |
| r20 | previous commit joined / kv ensured | 再分为 145.6 + 23.7 + 13.1 |
| r21 | before best | 145.6 与 `best()` 无关 |
| r23 | kv ensured 2（相邻对）/ resume decided | 相邻 tr() 差 0.0 ⇒ **不是 stderr 背压** |
| r24 | taken / validated / streams ready | 全部 0.0–0.1 ⇒ 落在 `streams ready` 之后 |
| **r25** | **对齐引擎自己的 `parked … in X ms`** | **就是 park** |

**关键一步不是新打点，而是把引擎已有的日志与打点对齐**：`parked` 那行正好落在缺口里，且毫秒数相同。
⇒ 一条通用教训：**先找引擎已经打出来的数，再决定要不要加打点**（今天的 r19–r24 六个补丁，有四个最终只是排除了候选）。

---

## 2 A/B（同进程、文件开关、零重启）

| 臂 | 开关 | `rest`（续写 5 新 token） | `parked` 自身 |
|---|---|---:|---:|
| A 同步 | 无文件 | 226.3 / 196.5 ms | 147.3 ms |
| B 异步 | `/data/strata-park-async` | 159.5 / 104.8 ms | **74.8 ms** |

**浸泡**（16 个请求，B 臂）：错误行 **0**、`restored … in 18.5–18.8 ms`、复用稳定（1406/1472/1477）、VRAM **33.53 GB 不变**。

---

## 3 落产

| 项 | 内容 |
|---|---|
| 代码（r25） | `park_async_on()` 去掉 HIP/Metal 的硬屏蔽（Metal 仍关）；改成「`STRATA_PARK_ASYNC=1` 或 `/data/strata-park-async`」**逐次判定**；`generate.cpp` 的 `park_async_env()` 同步改成一致语义 |
| 生产 config | `env` 增加 `"STRATA_PARK_ASYNC": "1"`（备份 `strata-huihui-ud-iq4_xs.json.bak_parkasync_*`）；**下次重启生效**，当前进程靠 marker 文件已生效 |
| 参数表 | `PARAM_REGISTER.tsv` 新增 **P245**（ADOPTED，含 A/B 数、风险、未解决项） |
| 回滚 | `rm /data/strata-park-async`（即时回同步）；或 `ci/rollback.sh --exe /data/bin/strata-0.1.55q --apply`（整机回滚） |

---

## 4 剩余可挖

- **~75 ms**：`ParkAsync` 的两跳里，第一跳（VRAM→4 MiB stage）仍在调用线程。改成「一个大拷贝排到私有流 + 下次取用时 join」可望把这 75 ms 也拿掉。
- **25 ms 挂载 + 13 ms 检查点**：`conversation_kv_restore` 已接近 PCIe 地板：260 MB ÷ 13.2 GB/s = **19.7 ms**，
  实测 23.7 ms ⇒ 达地板的 **83%**（原文写 87%，`AUDIT19` 复算不符，已改），基本没空间。
- 短追问 TTFT 的账更新为：**~105 park + 25 mount + 13 ckpt + 46 window + ~30 misc ≈ 220 ms**（原 262 ms）。

**一句话**：今晚从「830 ms 的谜」一路收敛到「一次续写的固定开销是 197 ms，其中 147 是上一次会话的停放、已经在下一请求里偷偷做掉」，
并把停放搬进后台拿到 **-92 ms**；剩下的 75 ms 是同一个停放的传输本体，方向已明确。
