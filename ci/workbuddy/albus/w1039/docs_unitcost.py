import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**426 条 / 已结 339 / 79.6%**（本轮 +39：`P445`–`P483`）"
new4 = "**428 条 / 已结 341 / 79.7%**（本轮 +41：`P445`–`P485`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**26. CPU 与 PCIe 的单件成本只差 5%——所以那条路不是杠杆（`P484`/`P485`）**

上一节说 CPU 段占 11.7%，自然会问：把 miss 改走 PCIe 会不会更便宜？**两个价都用本机实测，不估**：

| 来源 | 数 |
|---|---|
| 引擎自己的模型行（日志） | `the CPU pool takes 81 us per missed expert (38.6 GB/s of expert bytes), the link 13.2 GB/s -> pcie_frac 0.15` |
| 我们的窗口账（`P482`） | CPU 段 **4.64 ms/窗** ÷ `0.45–0.51 per layer-window × 48` = 21.6–24.5 个 ⇒ **190–215 µs/个** |
| PCIe 一侧算出来 | 一个专家 blob = 槽均价 **2.99 MiB**，链路 **13.2 GB/s** ⇒ **225 µs/个** |

**⇒ CPU 只比链路便宜 1.05–1.2×，不是模型假设的 2.9×。** 也就是说 `--pcie-frac` 往哪边调都不会改变 11.7% 这个数；引擎自适应出的 `0.15` 方向也没错。

**这条顺带把 `P416` 接上了**：那次判定「decode 不稳的主因是专家缓存命中率（corr 0.49），不是线程数」，当时只有相关性；现在有了机制和量级——命中率掉的就是这 11.7%（p90 17.11 ms 的窗口），而 `--pool-workers` 那条路 `P265` 早已判过无差。

**一个 2.3× 的缺口，我记成「未解释」而不是「已解释」**（`P485`）：模型说 81 µs、实测 190–215 µs。我试过用「10 worker × 24.5 个 ⇒ 2.45 轮/窗 ⇒ 199 µs」解释，但实测是 4.64 ms，差 23 倍——**轮数解释不成立**，除非中位样本里大量窗口的 CPU 段接近 0（p90 是 17.11 ms，分布确实双峰）。现有日志只有两个边缘分布、**没有「每窗口 CPU 专家数 × CPU 段」的联合分布**，所以拆不动。要拆得在窗口里抓逐请求行，而 `--pool-workers` 已判无差 ⇒ 不再投入。

**落成一句话给后续所有 R**：decode 的 CPU 段只能靠「少 miss」压，也就是**加槽**（`R104`）；这不是换路径的问题，是容量问题。
"""
r = r.rstrip() + "\n" + section + "\n"
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §26 added; §四 ->", new4)

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / 484–485（13:5x）CPU 与 PCIe 单件成本只差 5% ⇒ 不是杠杆

- 引擎模型行（日志）：`CPU pool 81 us per missed expert (38.6 GB/s), the link 13.2 GB/s -> pcie_frac 0.15`；我们的窗口账：CPU 段 4.64 ms/窗 ÷ 21.6–24.5 个 = **190–215 µs/个**；PCIe 一个 2.99 MiB blob / 13.2 GB/s = **225 µs**。⇒ CPU 只便宜 1.05–1.2×，**改 pcie-frac 无用**。
- 顺带接上 **P416**（decode 不稳 ↔ 缓存命中率 corr 0.49）：现在有机制与量级（11.7% 窗口、p90 17.1 ms）。
- **2.3× 缺口（81 vs 190–215）记为「未解释」**：轮数解释不成立（10 worker × 24.5 个应是 ~0.2 ms，实测 4.64 ms）；现有日志只有两个边缘分布，缺「每窗口 CPU 数 × CPU 段」联合分布，拆不动就不再投入。
- 给后续所有 R 的一句话：decode 的 CPU 段只能靠**少 miss**（加槽 R104）压，是容量问题不是路径问题。
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
