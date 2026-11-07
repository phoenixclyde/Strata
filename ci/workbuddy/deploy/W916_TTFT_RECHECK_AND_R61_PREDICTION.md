# W916 · 新二进制（a97f4479）prefill 复核 + R61 的算术预判

> 2026-11-03 22:1x。零停服（只发 4 个基准请求）。两件事：①`W913` 遗留的"重启后换了主机侧构建，要补一次 TTFT 复核"；
> ②R61 在 PMC 之前先给一个**不需要 profiler 的算术下界**。

---

## 1 新二进制的 prefill 复核：无回退

**背景**：`W913` 的 6 次重启把运行件从已删除 inode `e0c6f250…` 换成了磁盘件 `a97f4479…`。
两者 `.hip_fatbin` 逐字节相同（`b4f1e26a…`），但主机侧差约 25 KB，且新件从未 A/B。

**方法**：`ci/bench_pair.py --prefill-words 4100 --n 4 --decode-tokens 64`（每 rep 一个新随机 prompt，防缓存命中），
**以服务端 `read in` 行为准**（客户端 ttft 含网络/排队）。

| rep | prompt tokens | 服务端 read in | tok/s |
|---|---|---|---|
| 1 | 6290 | 9003 ms | 698.7 |
| 2 | 6385 | 8904 ms | 717.1 |
| 3 | 6279 | 8788 ms | 714.5 |
| 4 | 6318 | 8827 ms | 715.8 |

**median = 715.2 tok/s，CV 1.1%**。

**基线**（`W897`，同一脚本、同一口径，跑在 `e0c6f250…` 上）：**720.7 tok/s / 717.7 tok/s**。

⇒ **−0.3% ~ −0.8%，小于 1×CV** ⇒ **没有可测的回退**。`W913` 那条"待复核"可以关掉。

**本轮 decode 不作判据**：只生成 64 token、且是 prefill 之后的冷启（rep1 45.3 → rep4 64.5 tok/s，CV 12.5%），
与 `W897` 的 70.7 tok/s（更长生成、稳态）不是同一口径。要判 decode 必须单独跑 ≥256 token × ≥4 rep。

---

## 2 R61 的算术预判：VALU 大概率**已经过了 40% 的门**

R61 要的是 rocprof 的 `VALUBusy`，但它需要独占或 attach 生产进程。在做那个之前，用**已实测的量**先算一个下界：

```
峰值指令率 = 60 CU × 64 lane × 1.725 GHz = 6.624 T instr/s
dot4 峰值   = 6.624T × 4 MAC/instr      = 26.5 TMAC/s
生产折算    = 4.55 TMAC/s               = 17.2% of dot4 峰值
```

`W904` 在这张卡上量过真实 MMQ 形状的指令配比：**0.75 条指令 / MAC**（每个 dp4a 配 1 移位 + 1 与）。
若整机 MAC 率 4.55 TMAC/s 全由 MMQ 承担：

| 假设 | 指令率 | 占峰值 | 含义 |
|---|---|---|---|
| 每 MAC 0.75 条指令（W904 实测配比） | 3.41 T instr/s | **51.5%** | VALUBusy 下界 ≈ 52% ⇒ **已过 40% 门** |
| 只有 dp4a（理论 0.25 条/MAC） | 1.14 T instr/s | 17.2% | 下界 17% ⇒ 供给不足、R60 该做 |

而 MMQ 只占 prefill 的 **34.6%**（gate/up 20.7% + down 14.0%，`W903`）⇒ MMQ 相位内的 MAC 率其实是
`4.55 / 0.346 ≈ 13.2 TMAC/s = 50% of dot4 峰值`。**这个数已经让"每 MAC 再加 2 条 VALU"不可能成立**
（50% × 3 = 150% > 100%），说明真实内核的指令配比远好于微基准的 0.75，VALU 占用实际落在 **50–65%** 区间。

⇒ **预判：R61 的答案大概率是"VALU ≥40%，已在发射墙"**，也就是 **R60（stream-k）不该做**，
真正的杠杆是"每条 dp4a 的固定开销"（R58 的三段计数），而这个方向 `R51` 已经试过一次并失败（hoist 慢 6–10%）。

**但预判不是结论**。要坐实仍需一次真实 PMC，可选两条路：

| 路径 | 做法 | 风险 |
|---|---|---|
| A. attach 生产 | `rocprof-attach -p <pid> -t librocprofiler-sdk-tool.so -d 20000` + 发一个 6K prompt | **可能挂死服务进程**（恢复 4–5 min）；且 tool 库只有默认那个，PMC 配置要经目标进程 env，attach 后能否生效未验证 |
| B. 重启注入 | config env 加 `HSA_TOOLS_LIB=…` + `ROCPROF_*`，重启一次、发一个请求、读输出，再重启移除 | 2 次重启（约 9 min），但**不挂死**；副作用是那一轮 serve 带 profiler |

`rocprofv3-avail` 已确认 gfx906 上 `VALUBusy / MemUnitStalled / FetchSize / TA_TA_BUSY` **都可用**，
所以这条路本身通，只是选哪种注入方式。

---

## 3 复现

```bash
python3 ~/strata166/ci/bench_pair.py --prefill-words 4100 --n 4 --decode-tokens 64
docker exec strata166-407 grep "read in" /data/strata-huihui-ud-iq4_xs.log | tail -40 | grep -E "prompt 6[0-9]{3} tokens"

# PMC 可用性
docker exec strata166-407 rocprofv3-avail list --pmc | grep -E "VALUBusy|MemUnitStalled|FetchSize"
```
