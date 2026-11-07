#!/usr/bin/env python3
"""W1038: append the kv k8v4-vs-int8 measured rows to deploy/PROGRESS.tsv."""
import io

P = "deploy/PROGRESS.tsv"

ROWS = [
    dict(
        block="B6判定探针",
        id="P442",
        item=("k8v4 vs int8 直接换参数实测（同机/同二进制/同 prompt/各 n=6+4）：int8 在 prefill 上 +0.42% @8K、"
              "decode −5.6% 不可分，性能零收益，代价 +720 MiB 显存 = −240 专家槽"),
        source="W1038",
        kind="count", count="1", done="1", status="DONE_NEG",
        note=("**W1038 实测（机主 08:30「直接换参数跑了对比」；两次重启，停机 45+45=90 s，config md5 已还原 `5e9b81e2…`）**。"
              "臂：ctl=`--kv k8v4`（在产，不重启）/ b=`--kv int8`，其余 37 个 args 与 9 个 env 全同，二进制全是 `b12180` `d24f8293…`。"
              "每臂两轮冒烟（`ab_w1037.py`，2.5K×3 + 8K×2 + decode×3，两轮合计 2.5K n=6 / 8K n=4）。"
              "**prefill 8K**：1250.9 → 1256.2 µs/tok = **+0.42%**（int8 侧 CV 0.24%，2×CV 0.48%）；**2.5K**：1565.5 → 1585.6 = +1.29%（int8 CV 2.39%，2×CV 4.78% ⇒ 不显著；首个样本 1661.8 是冷启动，剔除后 +0.3%）。"
              "**相位不动的证据**：8K `qsa attn` 2237.5 → 2245.5（**+0.36%**，n=4），`gemm gate/up` 2653→2643、`down` 1672.8→1671.5、`dequant` 520.5→514.8 逐项在噪声内 ⇒ 换 KV 格式**没有改变 attention 的时间**。"
              "机制（源码）：`kv_q8.hpp:33` 与 `kv_q4.hpp` 的 gather 都**反量化进同一块 FP16 scratch**，attention 内核读到的输入完全一致 ⇒ 后端 fp32 fma 的计算量不变，只有 gather 的字节数变（V 528 B vs 288 B/cell）；而 gather 在 8K 的 13516 ms 里占比极小 ⇒ 净效应为 0。"
              "**decode**：62.90（CV 10.8%，n=6）→ 59.40（CV 6.7%，n=6）= −5.56%（中位数 −4.21%）⇒ 落在 decode 的天然离散带内，不作为判据，但方向与 −240 槽一致。"
              "**显存**：专家槽 7463 → 7223（−240，−3.2%），专家池 21.79 → 21.08 GiB（−0.71 GiB）。"
              "源码口径 `kv_q8_bytes_per_cell`（`kv_q8.hpp:25`）= `n_head_kv*head_dim*2 + n_head_kv*(head_dim/64)*2*2` = 2×256×2 + 2×4×2×2 = **1056 B/cell**；k8v4 = int8 K 528 + q4 V 288 = **816 B/cell**；"
              "× 262144 cells × 12 层（`kv_q8.hpp:3` 的「12 QSA layers」）= 3.094 vs 2.391 GiB，差 **754,974,720 B = 720.0 MiB**，与实测 0.71 GiB 的偏差 1.3%。"
              "**判决：性能上 int8 无收益，保持 k8v4**（唯一可能的收益是质量，本轮未测）。"),
        ref="M3",
        kw="KW:int8|专家槽",
    ),
    dict(
        block="B6判定探针",
        id="P443",
        item="更正：「k8v4 比 int8 省 3.8 GiB / 1700 槽」不成立——实测 720.0 MiB / 240 槽，两个独立口径互证",
        source="W1038",
        kind="count", count="1", done="1", status="DONE",
        note=("**W1038 更正（`AUDIT24`/`W928` 留的「需复核」结案）**。旧值 3.8 GiB 与 1700 槽是把 **fp16→int8** 的差当成了 **k8v4→int8** 的差："
              "fp16 2048 B/cell − int8 1056 = 992 B/cell ⇒ 992×262144×12 = 2.9 GiB（仍不是 3.8，说明旧值另有一处口径错，不再追溯，直接以本轮实测为准）。"
              "**实测口径一（行为）**：`--kv int8` 启动后专家池 21.79 → 21.08 GiB，专家槽 7463 → 7223。"
              "**实测口径二（源码算术）**：240 B/cell × 262144 × 12 = 754,974,720 B = 720.0 MiB；槽均价 21.79 GiB/7463 = 2.990 MiB ⇒ 240 槽 = 0.701 GiB。"
              "两条路径独立得到 0.70–0.71 GiB，偏差 1.3% ⇒ **k8v4 相对 int8 只省 0.70 GiB / 240 槽**，不是 3.8 GiB / 1700 槽。"
              "连带修正：`AUDIT24` 的「W929 实测 717 MiB/240 槽」是对的，本轮的 720.0 MiB 与它一致，W928 的 3.8 GiB 作废。"),
        ref="AUDIT24;M3",
        kw="KW:3.8|实测",
    ),
    dict(
        block="B9显存",
        id="P444",
        item=("新候选：KV 按 `--max-context` **全额预分配**（本轮实测证明）——开 `--kv-grow` 可把 2.39 GiB 让给专家池（≈820 槽，+11%），"
              "比 int8↔k8v4 那 240 槽大一个量级"),
        source="W1038",
        kind="count", count="1", done="0", status="OPEN",
        note=("**W1038 立（本轮实测的副产品）**。证据链：`P442` 里 KV 只多了 720 MiB，专家池就正好少了 0.71 GiB、专家槽正好少了 240 —— 一一对应 ⇒ "
              "**KV 是按 262144 cells 一次性占满的，与实际用到多少无关**。当前 k8v4 的 KV 全额 = 816 B/cell × 262144 × 12 = **2.391 GiB**；int8 = 3.094、q4_0 = 1.688、fp16 = 6.000。"
              "`--kv` 帮助文本（`generate.cpp:1058`）自己写着 `--kv-grow`：*「the K/V takes VRAM only for the cells the requests reach and the expert cache holds the rest, "
              "giving slots back as the context grows (one GPU, with --expert-profile; STRATA_KV_GROW=1/0 also). Default: the whole --max-context allocated at start」* —— 正是我们现在的默认反例。"
              "我们**有** `--expert-profile`（前置条件满足）。若按典型 8K–16K 实际用到，KV 只需 0.08–0.15 GiB，可让出 **2.24–2.31 GiB ≈ 770–790 槽（+10.3–10.6% 槽位）**；"
              "代价是长上下文时专家池要被回收（换出即掉命中率），且 `--kv-grow` 与 `--kv-resident` 是两条不同机制（前者按需长，后者把 KV 放内存）。"
              "**判据**：先在 8K / 32K / 128K 三档量「槽位换来多少 decode」，要求 n≥5、2×CV，且 128K 档不得比现在差超过 2×CV；**停机**：一次重启（约 45 s）；**成本**：只改一个 CLI 参数，零代码。"
              "**为什么值得排在 int8 之前**：本轮已证明 KV 格式换来换去只有 240 槽，而这里一次就能拿 770+ 槽。"),
        ref="P442;P443",
        kw="KW:kv-grow|预分配",
    ),
]


def main():
    with io.open(P, "r", encoding="utf-8") as fh:
        s = fh.read()
    add = []
    for r in ROWS:
        if ("\t" + r["id"] + "\t") in s:
            print("skip existing", r["id"])
            continue
        add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"],
                              r["done"], r["status"], r["note"], r["ref"], r["kw"]]))
    if not add:
        print("nothing to add")
        return
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    with io.open(P, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    print("appended", len(add))
    for a in add:
        print("  ", a.split("\t")[1], a.split("\t")[7])


if __name__ == "__main__":
    main()
