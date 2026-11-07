# -*- coding: utf-8 -*-
"""修 P141 的 verdict（上一版经 shell 时反引号被当成命令替换吃掉了）。"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"
V = (
    "**CANDIDATE（W814 确认车已跑完，未进生产）**。交错 A/B/A（生产 / ram / 生产，同一语料 2330 与 2191 token）："
    "生产 4641/4787 与 4429/4336，ram **4280 / 3705** ⇒ **-9.2% / -15.5%**；"
    "与 W812 的 RD 臂（-14.0% / -14.7%）、W813 的 RR 臂（-4.3% / -13.7%）合并：**-12% ± 4%**，"
    "规律是**启动后第一个请求收益最小**。"
    "门槛面：`expert_slots=9873`、`vram_free=668` 与生产逐字相同，解码 48.38 对 48.94（-1.1%，噪声内）；"
    "显存归零无残留（引擎 33.72 GB → `docker stop` 5 s 后 10.85 MB → 重启 33.719 GB，进程占用逐字节相同）。"
    "**代价**：启动 +192~197 s（表 touch 85 s + 之后载权重变慢）、常驻 26.8 GiB、"
    "`mlock` 拿不到（`ulimit -l=8 MB`）、**要求启动时页缓存干净**（否则表被挤掉、退化成 W810 的 C 臂 0%）。"
    "**未决**：答案等价性在本构建上**判不了** —— 逐字指纹显示**同配置两次启动（生产 vs 生产）就已经不一致**"
    "（6 个样本 6 个 sha256，长度 1171/1140/1169 对 1140/1132/1183），根因是 0.2.5 之前「按时钟猜提示路径」"
    "（上游 0.2.5 发布说明逐字：The old timing guess changed answers between runs）。"
    "⇒ 要判只能走统计口径（36 题 / 多次采样），或先升到 0.2.5 让路径确定。"
)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], rows[1:]
n = 0
for r in body:
    if r and r[0] == "P141":
        r[10] = V
        n += 1
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)
print("fixed", n, "rows", len(body), "len", len(V))
for r in body:
    if r[0] == "P141":
        print(r[10][:200])
