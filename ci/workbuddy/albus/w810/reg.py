# -*- coding: utf-8 -*-
"""W810-W814 的 register 落账：P138 定案 + 新增 P139/P140/P141/P142。"""
import csv
import shutil
import time

P = "deploy/params/PARAM_REGISTER.tsv"
bak = P + ".bak_w810_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy(P, bak)

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr = rows[0]
assert len(hdr) == 11, hdr
body = rows[1:]

V138 = (
    "**REJECTED（W810/W812/W813 实测 2026-10-26 23:15 - 10-27 00:3x）**。表 = **320,001,536 行 × 90 B = 26.8 GiB**"
    "（`ple_reader.hpp:1-14` 逐字），一个 token 要 **16 行、落在 16 个不同的 4 KiB 页**。五臂 × 6 个 fresh 提示"
    "（1132/1453/2498/2777/4568/4840 token，跨臂逐字同一段文本）：`mmap` **-1.7%**（六格方向全对，但 A/A2 地板 0.2-1.4%）；"
    "`ram` **+0.03%** —— 表被页缓存回收（跑完 `RssFile` 只剩 986 MB，宿主 `Cached` 78.6→43.8 GB；容器 `ulimit -l=8 MB`，"
    "`mlock` 必失败 => `locked=false`，页只是普通文件缓存，被引擎自己 59.7 GB anon 挤掉）。"
    "**`ple` 的 93.6% 是等盘**：唯一一次「表真在内存」的样本（C 臂第 1 个请求）主机侧 PLE **15.8 ms/1k**，常态 **250 ms/1k**；"
    "折合 **68k rows/s = 280 MB/s 的随机 4 KiB = 68k IOPS**，SATA（Fanxiang S100Pro）队列已满。"
    "上游 #4104 同证（`--ple-io ram` 的逐页 touch 是 90 MB/s 的软件成本，盘本身 979 MB/s），#4105 是修法，**两条都还 open**。"
)

V139 = (
    "**REJECTED（W812 的 K4/K2 臂）**。`ple_reader.hpp:5-14` 逐字 \"a chunk's reads can run while the previous chunk computes\" "
    "=> 只有**第一个 chunk** 付 PLE，`--prefill auto`(8192) 对 1.5-6K 的提示只有一个 chunk。"
    "实测 PLE 确实按机理掉：4568 token 上 `ple` 从 **14.7%**（8192）→ 12.2%（4096）→ **6.8%**（2048），绝对 1186 → 597 ms；"
    "但**总时间反而涨**：4096 **+8.9%**、2048 **+5.3%**（4840 上 +6.2% / +3.3%）。chunk 边界那些按块重新起跳的相位"
    "（hc read / qsa attn / gdn）比省下的 PLE 更贵。与上游 0.2.5 发布说明一致："
    "「NVIDIA cards under 16 GB now read prompts in chunks of 4096 … a cold 8K prompt is 9% slower」。"
    "=> 「小 chunk」这条路封死，同时**证实了 PLE 的重叠机理**。"
)

V140 = (
    "**REJECTED（W810 的 D 臂）**。4,194,304 行（380 MB）与生产 1,048,576 行（95 MB）**逐格重合**（六格差 <1%）。"
    "拐点在 1M 以内：把行缓存设 0 才掉 15-20%（E 臂 2777：793 对 691 ms；4568：1263 对 1186 ms）。"
    "=> 命中率受「一个提示内部 20-34% 的重复」限制（`ple_reader.hpp:26-30` 自己的实测），与容量无关，**1M 就是正确值**。"
)

V141 = (
    "**CANDIDATE（待 W814 确认车）**。RD 臂（启动前 `drop_caches` 再启 `--ple-io ram`）：表稳定在 **25.0-25.6 GiB**"
    "（`PLEMAP` 按 VMA 聚合），2493 → **4296 ms**（生产 4997，**-14.0%**）、2560 → **4334 ms**（生产 ≈5080，**-14.7%**）。"
    "W813 门槛：`expert_slots=9873` / `vram_free=668` 与生产逐字相同，解码 48.38 对生产 48.94（**-1.1%，噪声内**）"
    "=> **解码无代价、槽位没少**。代价：启动 **+216 s**（表 touch 85 s + 之后载权重变慢）、常驻 26.8 GiB、"
    "`mlock` 拿不到（`ulimit -l=8 MB`，上游 INTEL.md:723 明确建议**不要**给 `memlock=-1`）、"
    "**要求启动时页缓存干净**（否则表被挤掉、退化成 C 臂的 0%）。上游 #4105（O_DIRECT 读进 page-locked RAM，23.7 s）"
    "只解启动、不解稳态。"
)

V142 = (
    "**REJECTED（W812 的 RDN 臂）**。`--ple-io ram` + `--no-ple-prefetch` 在 2560 token 上 **4396 ms** 对 RD 的 4334 ms"
    "（**+1.4%**，噪声内）=> ext4 上 `gather_batch` 里那 16 次/token 的 `MADV_WILLNEED` 不要钱。"
    "上游 #2918 的收益只在 ZFS（每次 hint 变成 ARC 预取，16K 提示每轮 17-18 GB 的额外盘读）；本机不是 ZFS。"
)

new = [
    ["P139", "CLI", "--prefill 4096|2048", "auto(8192)", "prefill/chunk", "REJECTED",
     "-", "-", "P138",
     "`src/prefill/prefill.cpp:2500-2504` 的相位口径 + `ple_reader.hpp:5-14` 的 chunk 流水；`ab_p42.sh` 的 K4/K2 臂",
     V139],
    ["P140", "CLI", "--ple-row-cache", "1048576(缺省)", "prefill/ple", "REJECTED",
     "-", "-", "P138",
     "`generate.cpp:482`（缺省 1<<20 行，90 B/行）；`ple_reader.hpp:26-30`（1M 行服务 ~82% 的读，提示内重复 20-34%）；`ab_p40.sh` 的 D/E 臂",
     V140],
    ["P141", "CLI", "--ple-io ram + 启动前 drop_caches", "未启用", "prefill/ple", "CANDIDATE",
     "宿主 RAM >= 表 26.8 GiB + 引擎 59.7 GB + 余量；启动脚本先 sync+drop_caches", "-", "P138",
     "`src/kernels/ngram.cpp:356-410`（ram = WILLNEED + 16 线程逐页 touch + 整段 mlock）；`ab_p42.sh` 的 RD 臂；`ab_p43.sh` 的 P/RR/P2 三臂",
     V141],
    ["P142", "CLI", "--no-ple-prefetch", "未设(即开 hint)", "prefill/ple", "REJECTED",
     "-", "-", "P138",
     "`generate.cpp:997` 帮助逐字；上游 #2918「On POSIX, `--no-ple-prefetch` turns off only this hint」；`ab_p42.sh` 的 RDN 臂",
     V142],
]

out = []
for r in body:
    if r and r[0].strip() == "P138":
        r = list(r)
        r[5] = "REJECTED"
        r[10] = V138
    out.append(r)

have = {r[0].strip() for r in out}
for r in new:
    if r[0] not in have:
        out.append(r)

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(out)

print("backup", bak)
print("rows", len(out))
for r in out:
    if r[0] in ("P138", "P139", "P140", "P141", "P142"):
        print(r[0], r[5], r[2], "|", len(r), "cols")
