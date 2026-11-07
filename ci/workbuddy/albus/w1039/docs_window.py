import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old4 = "**430 条 / 已结 343 / 79.8%**（本轮 +43：`P445`–`P487`）"
new4 = "**432 条 / 已结 345 / 79.9%**（本轮 +45：`P445`–`P489`）"
assert old4 in r
r = r.replace(old4, new4, 1)

section = """
**29. `kvg` 窗口跑完：槽 7463 → 8301（+11.2%），prefill 一条没退，20K 增长路径走通（`P488`）**

窗口 13:42:01–13:53:16，两次重启各 **39 s**，结束把 config 逐字节还原到 `5e9b81e2`。

**起机行（实测，不是推算）：**

```
expert cache 8301 slots, 24.23 GiB of VRAM            （在产 7463 / 21.79 GiB）
elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB);
             the expert cache (8301 slots) gives the K/V room below slot 5692
```

**+838 槽（+11.2%）**，比我预注册的 +767 还多——因为全额 K/V 是 **2.65 GiB**（含 MTP 草稿层），不是我在 `P474` 里按 12 层算的 2.391 GiB。**这是我那次算漏的一项，以实测为准。**

| 形状 | A（`b12180`） | B（`kvg`+GROW） | Δ | 2×CV（跨 run） |
|---|---|---|---|---|
| 2.5K | 1579.4 | **1561.6** | −1.13% | 2.46% |
| 8K | 1249.6 | **1246.0** | −0.29% | 0.48% |
| 16K | 1280.1 | **1277.5** | −0.20% | 0.40% |
| **20K** | 1244.1 | **1242.5** | −0.13% | 0.18% |

（us/token；每臂 2 pass、每点 n=4。**四项全部落在噪声内或略快，没有一项变慢。**）

**20K 是增长测试点**（> 起机初始的 16384 cells）：请求跑完，且 arm B 之后的日志里既没有 `could not map`、也没有 `ERR the K/V could not give its VRAM back` ⇒ **增长与归还都真的执行了**，这正是 `P478` 那道硬门想保的东西。

**decode 侧我只敢说到「方向为正」**：tok/s 59.13 → **65.23（+10.32%）**，但跨 run 2×CV **28%** ⇒ 不成立。预注册的那条判据（「应当看到 miss 数下降」）在单样本上是兑现的：`CPU experts` 0.64 → **0.49**、`VRAM hits` 25.28 → **29.09**、`CPU` 2.92 → **2.25 ms**——方向对，但两行来自不同请求，**这只是方向证据，不是定量结论**。

**外部也核了（`P489`）**：社区实测算过同一道题——「28 tok/s 需要 ~46 GB/s 的专家流，是 PCIe 3.0 x16 的 3 倍」，反过来 `--n-cpu-moe` 下 decode 只有隐状态过总线（~16 MB/s，低三个数量级），且 llama.cpp 只在 **batch ≥ 32** 时才把专家矩阵交给 GPU（`GGML_OP_OFFLOAD_MIN_BATCH`）——这正是「prefill 走 PCIe、decode 留 CPU」的分界。与我们的 95 µs vs 225 µs 完全同向，`--pcie-frac` 这条彻底关闭。
"""
r = r.rstrip() + "\n" + section + "\n"
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §29 added; §四 ->", new4)

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / P488（13:42–13:53）kvg 窗口：槽 +838、prefill 无退化、20K 增长走通

- 实测起机行：`expert cache 8301 slots, 24.23 GiB`（在产 7463/21.79）；`elastic K/V: 16384 of 262144 cells (0.21 of 2.65 GiB)`，给 K/V 的空间在 slot 5692 以下。
- **全额 K/V 是 2.65 GiB 不是 2.391**（含 MTP 草稿层）⇒ +838 槽（+11.2%），比预注册 +767 多。
- prefill（每臂 2 pass、n=4、跨 run 2×CV）：2.5K −1.13%、8K −0.29%、16K −0.20%、20K −0.13% ⇒ **没有一项变慢**。
- 20K 请求跑通且无 `could not map` / 无 `ERR the K/V could not give its VRAM back` ⇒ 增长+归还都执行了。
- decode 59.13→65.23（+10.32%）但 2×CV 28% ⇒ 不成立；预注册判据方向兑现（CPU experts 0.64→0.49、VRAM hits 25.28→29.09、CPU 2.92→2.25 ms），单样本。
- 外证（P489）：社区算过 46 GB/s 需求 vs PCIe 16 GB/s，且 llama.cpp batch≥32 才交给 GPU ⇒ CPU 算专家是唯一合理路径，`--pcie-frac` 彻底关闭。
- 停机：2 次重启各 39 s；config 已还原 5e9b81e2。**未装机，待批。**
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
