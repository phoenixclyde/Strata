import io

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()

old = "- **CPU vs PCIe 的单件成本（`P484`，本机实测）**：CPU 190–215 µs/个（4.64 ms ÷ 21.6–24.5 个），PCIe 一个 2.99 MiB blob 在 13.2 GB/s 上是 225 µs ⇒ **只差 1.05–1.2×**，引擎模型假设的 81 µs 把 CPU 低估了 2.3×（`P485` 记为已知未解释）。**⇒ 改 `--pcie-frac` 不是杠杆，`--pool-workers` 也已判无差。**"
new = ("- **CPU vs PCIe 的单件成本（`P484` 更正 / `P487`，本机实测）**：逐请求拟合 `cpu_ms = 95 µs × missed_experts + 2.7 ms`，**R² = 1.000**（342 请求）；"
       "PCIe 一个 2.99 MiB blob 在 13.2 GB/s 上是 225 µs ⇒ **CPU 便宜 2.4×**（引擎模型常数 81 µs 只差 17%）。"
       "**⇒ 改 `--pcie-frac` 不但不是杠杆，方向也是错的（会更慢）；`--pool-workers` 已判无差。**"
       "早期写的 190–215 µs 是「两个中位数相除」的错数，已作废（`P485` 记方法教训：比率必须来自同一样本配对）。"
       "miss 数是**重尾**：每请求 p50 222、p90 7,102、max 109,738 ⇒ 加槽收益按重尾算，不按均值算。")
assert old in p
p = p.replace(old, new, 1)
p = p.replace("**429 条 / 已结 342 / 79.7%**", "**430 条 / 已结 343 / 79.8%**", 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: §十六 单件成本更正 + denom")

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
old4 = "**429 条 / 已结 342 / 79.7%**（本轮 +42：`P445`–`P486`）"
new4 = "**430 条 / 已结 343 / 79.8%**（本轮 +43：`P445`–`P487`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**28. 上一节那个「2.3× 缺口」是我的错，逐请求拟合把它结清了：95 µs/个，R² = 1.000（`P487`）**

上一节我用「CPU 段中位数 4.64 ms ÷ 每层窗专家中位数 0.45×48」算出 190–215 µs/个，并说这与引擎的 81 µs 差 2.3×。**这是把两个中位数相除——两个数来自不同请求，中位数不可除。** 正确做法是把两个量**在同一条请求上配对**，而 `decode timing` 那一行里正好两个都有（`CPU %.2f` 是 `d1.run/w`，源头是 `expert_source.cpp:5302 d.ms_run += ms(c3, c4)` 的真实墙钟；`CPU experts %.2f` 是 misses/(w×L)）。

对 342 个「至少 1 个 CPU 专家」的请求做最小二乘：

```
cpu_ms = 0.0954 × missed_experts + 2.69 ms      R² = 1.000
        (95 µs/个)                  (2.7 ms/请求的固定开销)
```

R² 这么高不奇怪：每个专家 blob 形状相同（gu 1280×2560、down 2560×640），CPU 侧成本几乎恒定。对照拟合 GPU 命中：**33 µs/件**，CPU/GPU = **2.9×**，与引擎注释里 38.6 GB/s 的口径一致。

**三条后果：**

1. **9 成数字对上**：模型 81 µs vs 实测 95 µs，差 17% ⇒ 引擎的 `pcie_frac` 自适应可信，**CPU 比 PCIe（225 µs/blob）便宜 2.4×**，「把 miss 改走 PCIe」这条不但不是杠杆，**方向还是错的**。`P484` 的结论方向对、数字错，已在原行里更正。
2. **`P485` 改判 DONE_NEG**：所谓「2.3× 未解释缺口」不存在，它是我的算术错。保留该行只为一件事——**方法教训：比率必须来自同一样本的配对，不能拿两个边缘分布的中位数相除。** 这一条今天已经在 `P482`（decode 分解）和 `P486`（pass 位置）上各犯过一次同类错误。
3. **miss 数是重尾**：每请求 p10 **0**、p50 **222**、p90 **7,102**、max **109,738**（58/400 请求为 0）。所以「CPU 段 11.7%」是中位数口径，**少数请求会被它吃掉几秒**；`R104` 加槽的收益要按重尾算，不能按均值算。

**给窗口的一条预注册**：如果 `kvg` 真的多给了槽，应当看到的是 **miss 数下降**，而不是「CPU 段均匀变快」；两者在重尾下不是一回事。窗口里我会同时抓 `CPU experts` 与 `CPU ms` 两列。
"""
r = r.rstrip() + "\n" + section + "\n"
r = r.replace("`warmup_effect.py` / `summarize_kvg.py`。", "`warmup_effect.py` / `summarize_kvg.py` / `cpu_cost_fit.py`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §28 added; §四 ->", new4)

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / P487（14:1x）自我更正：CPU 单件 95 µs，R²=1.000；「2.3× 缺口」是我把两个中位数相除

- 逐请求配对拟合（342 请求）：`cpu_ms = 95 µs × missed_experts + 2.7 ms`，**R²=1.000**；`d1.run` 源头是 `expert_source.cpp:5302 d.ms_run += ms(c3,c4)` 的真实墙钟。
- 引擎模型 81 µs vs 实测 95 µs ⇒ 只差 17%，**没有缺口**；PCIe 一个 blob 225 µs ⇒ CPU 便宜 **2.4×**，`--pcie-frac` 方向不能动。
- GPU 命中 33 µs/件 ⇒ CPU/GPU = 2.9×。
- **P484 数字作废（结论方向对）**；**P485 改判 DONE_NEG**（原「2.3× 未解释」是算术错）。
- **方法教训（第三条同族）**：比率必须来自同一样本的配对；**中位数不可除**。同类错误今天已出现三次（P482 分解、P486 pass 位置、P485 比率）。
- miss 数重尾：p10 0 / p50 222 / p90 7,102 / max 109,738 ⇒ 加槽收益按重尾算。
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
