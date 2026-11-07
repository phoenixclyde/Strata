# W897 · 本轮实测：多流确认 + prefill/decode 两臂

**条件**：生产 `strata166-407`，配置与二进制均未改（`strata-0.1.55t`，md5 `e0c6f250…`）。
测量工具：`ci/bench_pair.py`（本轮新增，同一进程内分别测 **fresh-prompt TTFT** 与 **steady decode**；prefill 每发都用不同随机文本，避免 conversation/prompt cache 命中）。
两臂之间只差一个 env，各重启一次（245–265 s 载入），测完已回滚。

---


> **[口径注 · 2026-11-02 23:2x]** 本项目**只做单流**（W898）。本件里的多用户数字（6 用户 57→98 等）只作**背景**，不得引用为收益预期或验收依据；decode 的验收只守「不劣化」。

## 1 多流：引擎有，生产没开

| 证据 | 内容 |
|---|---|
| `include/strata/core/batch_rows.hpp` | 批量行结构存在 |
| `src/program/generate.cpp:141` | `void set_batch_slots(int n);` —「how many `--batch` slots the window keeps state for」 |
| `generate.cpp:797` | 「The `--batch` slots in this many groups pipelined through the stages of a layer split」 |
| `serve/server.py:1174-1187` | 读 `--batch-groups`，引擎回报 `batch_groups=G` |
| CLI | `--batch`、`--batch-groups`、`--batch-mtp`、`--parallel`、`--max-queue`、`--queue-timeout` |

⇒ **Strata 支持多槽/多流**（`--batch` 槽位 + 分组流水线 + 队列），但**生产 17 个参数里没有 `--batch` / `--parallel`**，
即当前是单流服务。这与 `furnace` 的经验一致：它的 decode 增益（57→98 @6 用户）全在多流臂，**单用户臂 62→62 持平**。

---

## 2 两臂实测

| 臂 | prefill TTFT（6.45K fresh prompt） | prefill tok/s | decode 中位 | 结论 |
|---|---:|---:|---:|---|
| **A 基线**（现产） | **8.975 s**，CV 1.0% | ≈718 | 70.70，CV 15.7% | — |
| B `STRATA_IO_THREADS=32` | 9.071 s，CV 1.5% | ≈711 | 69.05 | **无收益**（+1.1%，<1×CV）→ R53 DONE_NEG |
| C `STRATA_PREFILL_MMQ=0`（FP16 路径） | **14.079 s**，CV 1.1% | ≈458 | 68.76 | **慢 1.57×** → MMQ 必须开（R56 收口） |

decode 每臂首条都显著偏低（47–56 → 76），臂内单调爬升，CV 15.7% ⇒ **decode 用中位数跨臂比较无分辨力**，
本轮不对 decode 下任何结论；decode 的判据必须换成「同一臂内多点 + 配对」，这也是后续要改的测量方法。

---

## 3 结论

1. `STRATA_IO_THREADS`（PLE 直读队列深度）在这台机上**不是杠杆**：6.4K prompt 下 PLE 表基本命中页缓存，加大队列只增切换。
2. `STRATA_PREFILL_MMQ` 必须保持默认开启；FP16 路径慢 **1.57×**，这条把 R51（MMQ 向量化）的价值上限抬高了——
   既然 MMQ 已比 FP16 快 1.57×，**继续优化 MMQ 本身**（R51 的 128-bit load / Q8 流水线 / Y-tile prefetch）才是有杠杆的方向。
3. 若要做多流实验，应先开 `--batch 2`（或 `--parallel 2`）测聚合吞吐；单流下单用户 decode 已在这张卡的地板（见 W895 §4）。

---

## 4 复现

```bash
# 基线
python3 ci/bench_pair.py --n 4
# 臂：容器内写 profile.d 后重启（登录 shell 会 source）
docker exec strata166-407 sh -c 'echo "export STRATA_IO_THREADS=32" > /etc/profile.d/zz-ab-iot.sh'
docker restart strata166-407   # 约 245 s 载入
# 回滚
docker exec strata166-407 sh -c 'rm -f /etc/profile.d/zz-ab-*.sh' && docker restart strata166-407
```
