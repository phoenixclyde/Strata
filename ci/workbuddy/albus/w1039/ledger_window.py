import io

P = "deploy/PROGRESS.tsv"
rows = [
    ("B9显存", "P488",
     "`kvg` 窗口实测：**专家槽 7463 → 8301（+838 / +11.2%）**，K/V 只占 **0.21 of 2.65 GiB**；prefill 四个形状全部落在噪声内或略快（−0.13% ~ −1.13%），20K 请求走通（增长路径无 `could not map`、无 `ERR the K/V could not`）",
     "W1039", "count", "1", "1", "OPEN",
     "**窗口 13:42:01–13:53:16**，2 次重启（各 39 s，健康检查通过后才继续），config 逐字节还原 `5e9b81e2`。"
     "**起机行（实测）**：`expert cache 8301 slots, 24.23 GiB of VRAM`（在产 7463 / 21.79 GiB）；"
     "`elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB); the expert cache (8301 slots) gives the K/V room below slot 5692`。"
     "注意全额是 **2.65 GiB** 不是我推算的 2.391——因为含 MTP 草稿层的 K/V；让出 **2.44 GiB** ÷ 槽均价 ⇒ +838 槽，比我预注册的 +767 还多。"
     "**prefill（us/tok，每臂 2 pass、每点 n=4，判据用跨 run 2×CV）**：2500 **1579.4 → 1561.6（−1.13%，2×CV 2.46%）**；8000 **1249.6 → 1246.0（−0.29%，0.48%）**；16000 **1280.1 → 1277.5（−0.20%，0.40%）**；20480 **1244.1 → 1242.5（−0.13%，0.18%）** ⇒ **没有一项变慢**，四项都在噪声内或略快。"
     "**20K 是增长测试点**（> init 16384 cells）：跑完拿到 1242.5 µs/tok，且在 arm B 结束后的日志里既无 `could not map` 也无 `ERR the K/V could not give its VRAM back` ⇒ **增长与归还都真的执行了**。"
     "**decode 侧**：tok/s 59.13 → **65.23（+10.32%）**，但跨 run 2×CV **28%** ⇒ **不成立**，只能说方向为正。"
     "**预注册判据兑现情况（诚实版）**：我写的是「应当看到 miss 数下降，而不是 CPU 段均匀变快」。单样本对比：`CPU experts` 0.64 → **0.49**、`VRAM hits` 25.28 → **29.09**、`CPU` 2.92 → **2.25 ms**——方向对，但两行来自不同请求，**只是方向证据，不是定量结论**。"
     "**⇒ 判决：装机**（不是负优化 + 槽 +11.2% + 增长路径已验证），装后再用同一套协议做一次「在产 vs 回滚件」复测。",
     "R104;P474", "KW:8301|+11.2%|20K 走通"),

    ("B1参数轴", "P489",
     "外部核实与我们的单件成本同向：社区实测算出「28 tok/s 需要 ~46 GB/s 的专家流，是 PCIe 3.0 x16 的 3 倍」，且 llama.cpp 只在 batch ≥32 时才把专家矩阵交给 GPU ⇒ decode 阶段 CPU 算专家是唯一合理路径",
     "W1039", "count", "1", "1", "DONE",
     "**外证（2026 年社区实测，非本项目）**：① `--n-cpu-moe` 下 decode 只有每层每 token 的隐状态过 PCIe（~576 KB/token，28 tok/s 时约 **16 MB/s**，比链路低三个数量级）；② 反过来「把 1.65 GB 活跃专家每 token 流过去」需要 **~46 GB/s**，是 PCIe 3.0 x16 的 **3 倍**，「所以这条路根本不通」；③ llama.cpp 的调度规则：权重在 host 上的算子默认在 CPU 跑，只有 batch ≥ 32（`GGML_OP_OFFLOAD_MIN_BATCH`）才请 GPU 代跑——**这正是「prefill 走 PCIe、decode 留 CPU」的分界**。"
     "**与我们的数一致**：CPU 95 µs/个 vs PCIe 225 µs/blob（`P487`）⇒ CPU 便宜 2.4×，同向；GPU 在 decode 期利用率不高也是同一现象。"
     "**⇒ `--pcie-frac` 这条彻底关闭**（往 PCIe 偏只会更慢）；这也解释了为什么引擎自适应把它压到 0.15。",
     "P487;P484", "KW:46 GB/s|GGML_OP_OFFLOAD|关闭"),
]
lines = io.open(P, encoding="utf-8").read().splitlines()
for r in rows:
    assert len(r) == 11
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", ", ".join(r[1] for r in rows))

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**430 条 / 已结 343 / 79.8%**", "**432 条 / 已结 345 / 79.9%**", 1)
a = "→ **R105（进行中，`P479`–`P481`"
b = ("→ **R104 已实测通过（`P488`：槽 7463→8301、prefill 无退化、20K 增长路径走通）→ 待装机** "
     "→ **R105（进行中，`P479`–`P481`")
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: denom + R104 状态")
