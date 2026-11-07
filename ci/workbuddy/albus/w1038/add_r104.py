import io

P = "deploy/PROGRESS.tsv"
ROWS = [dict(
    block="B9显存",
    id="R104",
    item=("`--kv-grow`：把 KV 从「按 `--max-context` 全额预分配」改成按需分配（本轮实测已证明现在是全额占），"
          "典型 8K–16K 可让出 2.24–2.31 GiB ≈ 770–790 专家槽（+10.3%–10.6%）"),
    source="W1038",
    kind="count", count="1", done="0", status="OPEN",
    note=("**W1038 立（机主 08:30「直接换参数跑了对比」的副产品；`P444` 是它的实测证据行）**。"
          "证据：`--kv int8` 让 KV 多 720 MiB，专家池就正好少 0.71 GiB、槽正好少 240 —— 一一对应 ⇒ "
          "**KV 是按 262144 cells 开局占满的，与实际用到多少无关**。当前 k8v4 全额 = 816 B/cell × 262144 × 12 层 = **2.391 GiB**"
          "（int8 3.094 / q4_0 1.688 / fp16 6.000）。"
          "`--kv` 帮助文本（`generate.cpp:1058`）自带开关：*\"the K/V takes VRAM only for the cells the requests reach and the expert cache holds the rest, "
          "giving slots back as the context grows (one GPU, with --expert-profile; STRATA_KV_GROW=1/0 also). Default: the whole --max-context allocated at start\"*。"
          "我们**有** `--expert-profile`（前置满足）。按需分配下典型会话只用 8K–16K cells ⇒ KV 只需 0.08–0.15 GiB，"
          "可让出 **2.24–2.31 GiB ≈ 770–790 槽（+10.3%–10.6%）**，比 `P442` 里 int8↔k8v4 的 240 槽大一个量级。"
          "代价：长上下文时专家池要被回收，命中率会掉；且与 `--kv-resident`（把 KV 放内存）是两条不同机制，别混用。"
          "**判据**：8K / 32K / 128K 三档各测「槽位换来多少 decode」，n≥5、2×CV；128K 档不得比现在差过 2×CV。"
          "**停机**：一次重启（约 45 s）。**成本**：零代码，只加一个 CLI 参数。"),
    ref="P444",
    kw="KW:kv-grow|按需分配",
)]

s = io.open(P, encoding="utf-8").read()
add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"])
        continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("appended", len(add))
else:
    print("nothing")
