import io

P = "deploy/PROGRESS.tsv"
rows = [
    ("B1参数轴", "P484",
     "把「missed 专家交给 CPU 算」与「走 PCIe 读」按**本机实测量**对比：CPU 约 190–215 µs/个，PCIe 一个 2.97 MB blob 在 13.2 GB/s 上是 225 µs ⇒ **只差 1.05–1.2×**，不是引擎模型假设的 2.9×；所以改 `--pcie-frac` 救不了那 11.7%",
     "W1039", "count", "1", "1", "DONE",
     "**两个数都是本机实测，不是估**：① 引擎自己的模型行（日志）：`the CPU pool takes 81 us per missed expert (38.6 GB/s of expert bytes), the link 13.2 GB/s -> pcie_frac 0.15`；② 我们的窗口账（`P482`）：CPU 段 **4.64 ms/窗**，而 `CPU experts 0.45 (0.51 entries)` per layer-window × 48 层 = 21.6–24.5 个 ⇒ **每 190–215 µs**。"
     "⇒ 实测 CPU 单件是模型常数的 **2.3×**。而一个专家 blob = 槽均价 2.99 MiB、链路 13.2 GB/s ⇒ 走 PCIe 是 **225 µs**。**两者落在 5% 以内**，所以「把 miss 改走 PCIe」不是一个杠杆；引擎自适应出的 `pcie_frac 0.15` 方向也对（它按 81 µs 算，本该更偏向 CPU）。"
     "**这条同时解释了 `P416`**：decode 不稳定与**缓存命中率**相关（corr 0.49）——命中率掉的正是这一项，机制与量级都对上了（11.7% 的窗口、p90 17.11 ms）。"
     "**结论**：CPU 段只能靠「少 miss」压，也就是**加槽**（`R104`）；`--pcie-frac`、`--pool-workers` 都不追（`P265` 已判 pool-workers 无差）。",
     "P482;P416", "KW:190|225|少 miss"),

    ("B1参数轴", "P485",
     "模型常数 81 µs 与实测 190–215 µs 的 2.3× 缺口是**池的尾延迟**（10 worker × 24.5 个 ⇒ 每窗约 2.5 轮，每轮按最慢 worker 计），不是算力不够——但它已不在可优化路径上，只记不追",
     "W1039", "count", "1", "1", "DONE",
     "**推理链**：24.5 个 CPU 专家 ÷ 10 个 worker = 2.45 轮/窗；若单件纯计算 81 µs，则每窗 CPU 段应 ≈ 2.45 × 81 ≈ 199 µs ≈ **0.2 ms**，而实测是 **4.64 ms**（23 倍）。"
     "所以「轮数」这条解释不成立——除非很多窗口的 CPU 专家数远高于中位（`P482` 的 p90 CPU 段是 17.11 ms，说明分布是双峰的，中位样本里大量窗口 CPU ≈ 0）。"
     "**诚实的结论**：这 2.3× 缺口用现有日志**无法再拆**（缺「每窗口 CPU 专家数」与「CPU 段」的联合分布；现在只有两者的边缘）。要拆得在窗口里抓 `decode timing` 的逐请求行，或用 `--pool-workers` 做单变量对照——而 `P265` 已判过它无差。"
     "⇒ **记为「已知未解释」而不是「已解释」**，不再投入；若将来 decode 成为主目标，第一件事是把 `d1.run` 与 `d1.misses` 的逐窗口配对打出来。",
     "P484;P265", "KW:尾延迟|双峰|未解释"),
]
lines = io.open(P, encoding="utf-8").read().splitlines()
for r in rows:
    assert len(r) == 11
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", ", ".join(r[1] for r in rows))

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**426 条 / 已结 339 / 79.6%**", "**428 条 / 已结 341 / 79.7%**", 1)
a = "- **对 `R104` 的意义**：CPU 专家由「缓存装不下的专家」驱动"
b = """- **CPU vs PCIe 的单件成本（`P484`，本机实测）**：CPU 190–215 µs/个（4.64 ms ÷ 21.6–24.5 个），PCIe 一个 2.99 MiB blob 在 13.2 GB/s 上是 225 µs ⇒ **只差 1.05–1.2×**，引擎模型假设的 81 µs 把 CPU 低估了 2.3×（`P485` 记为已知未解释）。**⇒ 改 `--pcie-frac` 不是杠杆，`--pool-workers` 也已判无差。**
- **对 `R104` 的意义**：CPU 专家由「缓存装不下的专家」驱动"""
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: denom + §十六 追加单件成本")
