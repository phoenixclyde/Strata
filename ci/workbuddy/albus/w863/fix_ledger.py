# -*- coding: utf-8 -*-
"""[W863] Make the ledger self-consistent, then add this round's row.

Two defects found by plan_stats.py:
  * R22 / R23 carry status=DONE but done=0  -> the weighted settled count disagreed with
    the status count (54 vs 57).  A ledger whose two halves disagree cannot be the single
    denominator every round is reported from.
  * R25 (HC probe) was still OPEN after the probe ran this round.

Changes: fix done for every settled status, close R25 with its real conclusion, open R27
(the parallelism candidate the probe pointed at).  Nothing else is touched.
"""
import csv
import io
import shutil
import time

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
shutil.copy2(P, P + ".bak_w863_%s" % time.strftime("%H%M%S"))

with open(P, encoding="utf-8") as f:
    lines = f.readlines()

head = [l for l in lines if l.startswith("#") or not l.strip()]
body = [l for l in lines if not l.startswith("#") and l.strip()]

hdr = body[0].rstrip("\n").split("\t")
rdr = csv.DictReader([b.rstrip("\n") for b in body], delimiter="\t")
rows = [dict(r) for r in rdr]

SETTLED = {"DONE", "DONE_NEG", "NA"}
fixed = []
for r in rows:
    if r["status"] in SETTLED and str(r.get("done")) != str(r.get("count")):
        fixed.append((r["id"], r["status"], r.get("done"), r.get("count")))
        r["done"] = r["count"]

print("=== done-field fixes ===")
for f_ in fixed:
    print("  %-5s %-9s done %s -> %s" % f_)
if not fixed:
    print("  (none)")

# close R25 with this round's conclusion
for r in rows:
    if r["id"] == "R25":
        r["status"] = "DONE"
        r["done"] = r["count"]
        r["note"] = (
            "**W863 探测已做（一次重启，已恢复）**：`STRATA_HC_Q8=0`（bf16 读）的 hc 合计 "
            "7.46/7.69 ms，而同配置 Q8=1 的历史相位表在 5.34–8.61 之间跳（±30%）⇒ 落在噪声里，"
            "**无分辨力**。但字节翻倍几乎不改时间 ⇒ **不是带宽受限**；`down` grid=11×16=176 blocks、"
            "`up`=160 blocks，60 CU 下占用率仅约 37%/33%。见 `W863_SINGLE_STREAM_PLAN.md` §6。"
            "另修正：拿 hc 6.89 推「98 GB/s」是把噪声当精确值，字节 644 MiB 可信、带宽比值不可用。")
        print("\nR25 -> DONE (probe ran, conclusion recorded)")

if not any(r["id"] == "R27" for r in rows):
    rows.append({
        "block": "B1参数轴",
        "id": "R27",
        "item": "HC 读的并行度：down 176 blocks / up 160 blocks，60 CU ⇒ 占用率 ~37%/~33%",
        "source": "W863 §6（源码 grid 常量 + HC_Q8 探测）",
        "kind": "count",
        "count": "1",
        "done": "0",
        "status": "OPEN",
        "note": "`Q8_KC` 640→320 ⇒ `Q8_NKC` 16→32 ⇒ down grid 176→352，占用率≈73%。代价：chunk 变细，"
                "求和顺序改变（源码注释 output-changing），须过 KL/argmax。**先做秒级微基准**"
                "（q8_wave_lab 类），验证 blocks 翻倍时间是否下降，别直接重编 8-10 分钟。",
        "ref": "",
    })
    print("R27 added (OPEN)")

out = io.StringIO()
for l in head:
    out.write(l)
out.write("\t".join(hdr) + "\n")
for r in rows:
    out.write("\t".join(str(r.get(c, "")) for c in hdr) + "\n")

with open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(out.getvalue())
print("\nwritten: %s  (%d data rows)" % (P, len(rows)))
