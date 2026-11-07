import io

P = ".workbuddy/memory/2026-11-07.md"
ADD = """
### W1038（08:3x）`--kv int8` vs 在产 `k8v4` 直接换参数实测：速度零收益、只买到质量

- **实测（同机/同二进制/同 prompt，2.5K n=6、8K n=4）**：8K **1250.9 → 1256.2 µs/tok = +0.42%**（2×CV 0.48%）；2.5K +1.29%（2×CV 4.78%，首样本冷启动，剔除后 +0.3%）；8K `qsa attn` **2237.5 → 2245.5（+0.36%）**；decode 62.90 → 59.40（CV 10.8%/6.7% ⇒ 不可分）。**⇒ int8 没有速度收益。**
- **显存差被两口径钉住**：源码 `kv_q8.hpp:25` 公式给 1056 B/cell、k8v4 816、差 240 B/cell × 262144 × 12 层 = **720.0 MiB**；行为上专家池 21.79 → 21.08 GiB、槽 **7463 → 7223（−240）**。两路偏差 1.3%。**旧账「省 3.8 GiB / 1700 槽」作废**（那是 fp16→int8 的差）。
- **机制（可复用）**：`kv_q8.hpp:33` 与 `kv_q4.hpp` 的 gather **都反量化进同一块 FP16 scratch** ⇒ attention 内核输入一致、后端 fp32 fma 指令数不变 ⇒ **只要 KV 是「gather 再算」，位宽就只是显存旋钮，不是速度旋钮**。要变成速度旋钮得让 attention 直接吃 int8（`sdot4`，`R64`）。
- **副产品立 R104（`P444`）**：KV 多 720 MiB ⇔ 槽少 240 一一对应 ⇒ 证明 **KV 按 `--max-context` 全额预分配**（k8v4 = 2.391 GiB @262144×12）。`--kv` 帮助文本（`generate.cpp:1058`）自带 `--kv-grow`（按需长，我们有 `--expert-profile` 满足前置）⇒ 典型 8K–16K 可让出 **2.24–2.31 GiB ≈ 770–790 槽（+10.3%）**，比 int8↔k8v4 那 240 槽大一个量级。
- **口径纪律**：质量这轮**没测**（KL 要 LOGPOS 独占窗口）；账本 `0.0416/0.0704` 是旧测且被 `AUDIT24` 标「需复核」，**不拿来当依据**。能核的只有 `bench/results/2026-09-27-kv-q4/README.md`（fp16/int8/q4_0 三列，8K 上 q4_0 的 KL 是 int8 的 4.2×）。
- **窗口**：重启 2 次、停机 90 s（45+45），config 改 `k8v4→int8` 再逐字节还原（md5 回 `5e9b81e2…`），单引擎断言 + health 门 + 失败即还原。脚本 `albus/w1038/kv_ab.sh`。
"""
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD)
print("memory appended", len(ADD))
