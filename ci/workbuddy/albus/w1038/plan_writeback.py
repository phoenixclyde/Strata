#!/usr/bin/env python3
"""W1038: write the W1038 block into W832 and refresh §0.1 (queue + denominator)."""
import io
import re

P = "deploy/W832_OPT_PLAN_V2.md"

BLOCK = """### 回写 · W1038（2026-11-07 08:3x）直接换 `--kv` 跑对比：int8 相对 k8v4 性能零收益，只买到质量，价钱是 240 专家槽

> 生产 **2 重启 / 停机 90 s（45+45）/ 装机 0**。`--kv int8` 跑完已**还原 k8v4**，config md5 回到 `5e9b81e2f66ca48999766d2ae0201fb6`，
> `/health` ok、单引擎、exe 仍是 `b12180`（`d24f8293…`）。账本 `P442` / `P443` / `P444`。

**一、问的是"收益"，量出来的是"没有收益"（`P442`）。** 只换一个 CLI 参数，其余 37 个 args 与 9 个 env 全同，二进制同 md5。
每臂两轮冒烟（2.5K×3 + 8K×2 + decode×3，两轮合计 2.5K n=6 / 8K n=4）。

| 轴 | `--kv k8v4`（在产） | `--kv int8` | Δ | 判据 |
|---|---|---|---|---|
| prefill 8K µs/tok | 1250.9（n=4, CV 0.24%） | 1256.2（n=4, CV 0.24%） | **+0.42%** | 2×CV 0.48% ⇒ 边缘、方向为负 |
| prefill 2.5K µs/tok | 1565.5（n=6, CV 0.96%） | 1585.6（n=6, CV 2.39%） | +1.29% | 2×CV 4.78% ⇒ 不显著（首个样本冷启动 1661.8，剔除后 +0.3%） |
| 8K `qsa attn` | 2237.5 ms | 2245.5 ms | **+0.36%** | 相位不动 |
| 8K `gemm gate/up` / `down` / `dequant` | 2653.0 / 1672.8 / 520.5 | 2643.0 / 1671.5 / 514.8 | −0.4% / −0.1% / −1.1% | 逐项在噪声内 |
| decode tok/s | 62.90（CV 10.8%, n=6） | 59.40（CV 6.7%, n=6） | −5.56%（中位 −4.21%） | 落在 decode 天然离散带内，不作判据，方向与 −240 槽一致 |
| 专家槽 / 专家池 | **7463 / 21.79 GiB** | **7223 / 21.08 GiB** | **−240（−3.2%）/ −0.71 GiB** | 直接量 |

**二、为什么 attention 时间不动——源码给的是必然，不是巧合。**
`kv_q8.hpp:33` 的 `kv_gather_q8_step` 与 `kv_q4.hpp` 的 gather **都反量化进同一块 FP16 scratch**，attention 内核读到的输入逐元素同类型同布局
⇒ 后端 fp32 `fmaf` 的计算量与指令数完全不变，换格式只改 gather 的字节数（V 528 → 288 B/cell）。
而 8K 的 gather 只占 13516 ms 里的零头 ⇒ 净效应落在 0.4% 以内。
**推论（可复用）**：只要 KV 是"gather 后再算"，KV 位宽就不是速度旋钮，只是显存旋钮。

**三、显存差被两个独立口径同时钉住（`P443`）。**
源码：`kv_q8_bytes_per_cell`（`kv_q8.hpp:25`）= 2×256×2 + 2×4×2×2 = **1056 B/cell**；k8v4 = int8 K 528 + q4 V 288 = **816 B/cell**；
× 262144 cells × **12 层**（`kv_q8.hpp:3`）= 3.094 vs 2.391 GiB，差 **754,974,720 B = 720.0 MiB**。
行为：专家池 21.79 → 21.08 GiB、槽 7463 → 7223；槽均价 2.990 MiB ⇒ 240 槽 = 0.701 GiB。
**两条路径偏差 1.3%** ⇒ 旧账「k8v4 省 3.8 GiB / 1700 槽」作废（那是把 fp16→int8 的差当成了 k8v4→int8）。

**四、真正的钱在别处（`P444`，新候选）。** 上面这条一一对应（KV +720 MiB ⇔ 槽 −240）同时证明了一件事：
**KV 是按 `--max-context` 262144 一次性占满的**，与实际用到多少无关。k8v4 全额 = **2.391 GiB**（int8 3.094 / q4_0 1.688 / fp16 6.000）。
`--kv` 帮助文本（`generate.cpp:1058`）自带开关 `--kv-grow`：*"the K/V takes VRAM only for the cells the requests reach and the expert cache holds the rest … Default: the whole --max-context allocated at start"*。
我们**有** `--expert-profile`（前置满足）。典型 8K–16K 实际用到时 KV 只需 0.08–0.15 GiB ⇒ 可让出 **2.24–2.31 GiB ≈ 770–790 槽（+10.3%–10.6%）**，
比 int8↔k8v4 那 240 槽大**一个量级**。判据：8K / 32K / 128K 三档量"槽换 decode"，n≥5、2×CV，128K 不得差过 2×CV；停机一次重启；零代码。

**五、没测的那一半。** 质量本轮**没测**（KL 需要 LOGPOS 探针独占窗口）。账本里的 `0.0416`（int8）对 `0.0704`（k8v4）是旧测、且 `AUDIT24` 标了"需复核"，
本轮**不拿它当依据**；能核的是 `bench/results/2026-09-27-kv-q4/README.md` 的 fp16/int8/q4_0 三列表（int8 ≈ fp16；q4_0 在 8K 上 KL 4.2× int8、ppl +12%）——
k8v4 的 V 就是那个 q4_0，所以"int8 质量更好"方向可信，幅度待测。
**结论：现有数据支持"保持 k8v4"**——int8 在速度上是 0 甚至微负，在显存上是 −240 槽，唯一收益是质量，而质量这一半还没在本模型上量过。
"""


def main():
    with io.open(P, "r", encoding="utf-8") as fh:
        s = fh.read()

    if "### 回写 · W1038" not in s:
        if not s.endswith("\n"):
            s += "\n"
        s += "\n" + BLOCK + "\n"
        print("block appended")
    else:
        print("block exists, skip")

    # §0.1: denominator
    m = re.search(r"\*\*(\d+) 条 / 已结 (\d+) / ([\d.]+)%\*\*（W1037 校正", s)
    s2 = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1037 校正",
                "**386 条 / 已结 302 / 78.2%**（W1038 校正", s, count=1)
    print("denom:", "ok" if s2 != s else "MISS")
    s = s2

    # §0.1: queue — insert R104 before R103 marker
    old_q = "| **唯一队列** | **R103（最优先；"
    new_q = ("| **唯一队列** | **R104（新，`P444`：`--kv-grow` 把 KV 从 2.391 GiB 全额预分配改为按需，"
             "让 770–790 槽给专家池；一次重启、零代码）** → **R103（最优先；")
    if old_q in s and "R104（新" not in s:
        s = s.replace(old_q, new_q, 1)
        print("queue: R104 inserted")
    else:
        print("queue: pattern miss or exists")

    with io.open(P, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    print("len", len(s))


if __name__ == "__main__":
    main()
