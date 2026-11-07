"""W822: 落账两条 —— 换权重（UD-Q4_K_XL）+ K-quant 的 MMQ_KQ 开关。"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"

ROWS = [
    [
        "P148",
        "MODEL",
        "UD-IQ4_XS -> UD-Q4_K_XL",
        "Q4_K_XL",
        "model/weights",
        "ADOPTED",
        "pack 需按 docs/UNSLOTH_Q4.md 用 iq_pack --compat-bf16 重打",
        "",
        "P149",
        "**2026-10-29 换权重，已上生产**。四个分片 104 GB（00001 10.9 MB / 00002 49.86 GB / 00003 49.38 GB / "
        "00004 12.09 GB），20:54 下完；pack 按上游 `docs/UNSLOTH_Q4.md` 的命令重打（`tools/iq_pack.py --gguf …00001-of-00004.gguf "
        "--out … --compat-bf16`，45 s）。**`--compat-bf16` 是文档强制项**（不带则拒绝打包）：该文件把 195 个 Q8_0 小投影"
        "（hyper-connection 上下矩阵、output_hc_*、PLE value）转成 BF16，`conversions.json` 记 264 exact / 196 rounded，max|err| 0.0144。"
        "**已知代价（上游自述）**：该舍入在 Strix Halo 上让 ppl 比 llama.cpp 高 6-9%，「读 Q8_0 原值可抹平大部分但不在本版本」。"
        "同时修掉配置里两处残留：`tokenizer` 曾指向已删的旧 pack（否则 server.py 直接拒启），`vision.model` 曾指向旧权重的 GGUF。"
        "**实测（同一语料 2636 token）**：arena 55.43→**71.7 GiB**（36727×2 MiB），槽位 9873→**7551**（blob 3.48→3.99 MB），"
        "PLE 表仍是同一张 320,001,536 行（在 00002-of-00004），MTP 草稿层复用（源头是 BF16 原模型，与量化档无关）。"
        "旧的两个 iq4_xs pack 与 4 个旧 learned profile 已删；旧 GGUF 88 GB 暂留。",
        "",
    ],
    [
        "P149",
        "ENV",
        "STRATA_MMQ_KQ",
        "1",
        "prefill/kquant",
        "ADOPTED",
        "需构建期 STRATA_MMQ_KQUANTS=ON（本机已 ON）",
        "",
        "P148",
        "**K-quant 的核心配套开关，实测 +60% 提示**。上游 `docs/UNSLOTH_Q4.md` 原文："
        "\"With STRATA_MMQ_KQ=1 the engine multiplies the Q4_K / Q5_K / Q5_1 experts of a prompt with llama.cpp's MMQ kernels "
        "… instead of dequantizing them to FP16: 4x less GPU time for those products\"。"
        "不开时走 FP16 反量化路径（每个专家按 ~10 MB FP16 读）。"
        "**本机实测（同 pack、同语料 2636 token、暖缓存）**：不开 9.86 s = **267 tok/s**；开 5.77 s = **457 tok/s**（测试臂）、"
        "生产复测 6.17 s = **427 tok/s** ⇒ **+60~71%**；解码中位 32.9 → 38.8/42.0 tok/s（+18~28%，非 MMQ 直接作用，属状态差异）。"
        "与旧 IQ4_XS（508 tok/s / 48.9 tok/s）相比仍 −16% / −14%，但比不开 MMQ 的 −47% / −33% 好得多。"
        "**注意**：启动未受影响（180 s，与旧权重相同口径）；但多次重启后 2 MiB THP 块会碎片化，"
        "曾出现 `transparent huge pages NOT requested: only 26 GiB of free 2 MiB blocks` 使启动拖到 350 s+，重启机器即恢复。",
        "",
    ],
]

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], rows[1:]
ids = {r[0] for r in body}
for row in ROWS:
    assert row[0] not in ids, row[0]
    assert len(row) == len(hdr), (row[0], len(row))
    body.append(row)

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
print("rows", len(rows) - 1, "cols_ok", all(len(r) == 11 for r in rows),
      "dups", [i for i in {r[0] for r in rows[1:]} if [x[0] for x in rows[1:]].count(i) > 1])
