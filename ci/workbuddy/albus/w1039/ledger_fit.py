import io

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()

# 1) P484: correct the number in the same row (the project rule: a wrong verdict is rewritten, not buried)
old484 = "**两个数都是本机实测，不是估**：① 引擎自己的模型行（日志）"
new484 = ("**更正（`P487`）**：本行原来写的「每个 190–215 µs」是**把两个中位数相除**得来的错数，已作废；"
          "逐请求配对后的真值是 **95 µs/个（R²=1.000）**。结论方向不变且更强——CPU 比 PCIe 便宜 **2.4×**，所以「把 miss 改走 PCIe」更不可行。以下为原始推理，数字以更正为准。"
          "**两个数都是本机实测，不是估**：① 引擎自己的模型行（日志）")
assert s.count(old484) == 1
s = s.replace(old484, new484, 1)

# 2) P485: its premise (a 2.3x gap) is gone
lines = s.splitlines()
for i, ln in enumerate(lines):
    f = ln.split("\t")
    if len(f) > 8 and f[1] == "P485":
        f[7] = "DONE_NEG"
        f[8] = ("**已由 `P487` 结清：没有 2.3× 缺口。** 逐请求拟合 `cpu_ms = 95 µs × missed_experts + 2.7 ms/request`（R² = **1.000**，342 个请求），"
                "而引擎模型常数是 81 µs ⇒ 只差 **17%**，属正常。原来那个「2.3×」是我用「CPU 段中位数 ÷ 每层窗专家中位数」算出来的，"
                "两个中位数来自不同请求，**中位数不可除**。本行保留作方法教训：**比率必须来自同一样本的配对，不能拿两个边缘分布的中位数相除。**")
        lines[i] = "\t".join(f)
        break
else:
    raise SystemExit("P485 not found")

# 3) new row: the fit, the heavy tail, and what it changes
row = ("B1参数轴", "P487",
       "逐请求拟合把 CPU 段钉死：`cpu_ms = 95 µs × missed_experts + 2.7 ms`，**R² = 1.000**（342 个请求）；且 miss 数的分布极重尾（p50 222、p90 7102、max 109,738 个/请求）",
       "W1039", "count", "1", "1", "DONE",
       "**方法**：`strata decode timing` 行里同时有 `CPU %.2f`（= `d1.run/w`，`expert_source.cpp:5302 d.ms_run += ms(c3, c4)` 的**真实墙钟**）与 `CPU experts %.2f`（= misses/(w×L)）。"
       "对 342 个「至少 1 个 CPU 专家」的请求做最小二乘：斜率 **95 µs/个**、截距 **2.7 ms/请求**、**R² = 1.000**。"
       "R² 这么高不奇怪——每个专家 blob 形状相同（gu 1280×2560、down 2560×640），CPU 侧成本几乎恒定。"
       "**两个直接结论**：① 引擎模型常数 81 µs 与实测 95 µs 只差 17% ⇒ `pcie_frac` 的自适应是可信的，**CPU 比 PCIe（225 µs/blob）便宜 2.4×**，「改走 PCIe」这条彻底关掉；"
       "② 作为对照，GPU 命中的单件是 **33 µs**（同样拟合），CPU/GPU = **2.9×**，与引擎注释里的 38.6 GB/s 口径一致。"
       "**重尾**：每请求 miss 数 p10 **0**、p50 **222**、p90 **7,102**、max **109,738**（58/400 个请求为 0）⇒ 「11.7% 的 CPU 段」是中位数口径，少数请求会被它吃掉几秒。**加槽的收益要按重尾算，不是按均值算。**",
       "P484;P485", "KW:R²|95 µs|重尾")

lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("P484 corrected in place; P485 -> DONE_NEG; P487 appended")
