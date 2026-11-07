"""W820: 把第一轮 A/B 的结果追加进 P146 的 verdict（只追加，不改已有文字）。"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"
ADD = (
    " 【W820 第一轮 A/B，2026-10-29 01:48-02:00，A(0.1.49.2)/B(0.1.52)/A2(0.1.49.2) 交错的补充证据】"
    "提示时间：1453/2498/4568 token 上 A 3.46/4.92/8.46 s、B 3.99/5.14/8.75 s、A2 4.13/5.19/8.74 s，"
    "**B 全部落在 A 与 A2（同二进制）之间的漂移带内**（漂移 19.4%/5.5%/3.3%）⇒ **0.1.52 在提示侧与生产不可区分**。"
    "启动 170/165/196 s 无差别；解码不可判（同二进制 A vs A2 差 38%，mt_gen 排在 3 次大 prefill 之后、每臂仅 3×128 token）。"
    "漂移来源已定位为**磁盘逐臂变慢**（竞技场载入 0.38/0.39/0.32 GiB/s），非二进制；"
    "三臂引擎状态一致（decode 缓存命中 93.8/93.8/93.9%，尾跳 10036/9861/9772）⇒ 不是 B 臂异常。"
    "下一轮必须：解码前置 + 细粒度 A/B/A/B + 加 STRATA_PREFILL_TIMING=1（本轮漏了，所以没有 ple/attn 相位）。"
)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
n = 0
for r in rows[1:]:
    if r and r[0] == "P146":
        r[10] = r[10] + ADD
        n += 1
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(rows[0])
    w.writerows(rows[1:])
print("updated", n, "row(s); total", len(rows) - 1)
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
print("cols_ok", all(len(r) == 11 for r in rows))
