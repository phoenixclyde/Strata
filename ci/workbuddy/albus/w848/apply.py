# -*- coding: utf-8 -*-
"""W848：把现状页/进度账/基线更新到 0.2.9t2（终端+seed 已装）。用文件跑，避免 heredoc 被 shim 吃掉。"""
import io

ROOT = "D:/workbuddy_space/strata_ws/deploy/"

# ---------- SESSION_STATE ----------
p = ROOT + "SESSION_STATE.md"
s = io.open(p, encoding="utf-8").read()

old = ("| 镜像 | **`strata-gfx906:0.2.9`**（`sha256:7905395d…`，7.71 GB）：`/src` = **v0.2.9 全树 8143 文件**（含 12 补丁）"
       "+ `/opt/strata/components/engine/0.1.55-linux-x86_64-hip-gfx906`（234 文件，manifest `02166a3d…`，`--verify` ok）。"
       "回滚：`0.2.9s1`（容器 `pre-w847`）、`0.2.8p2`（容器 `pre-w846`） |")
new = ("| 镜像 | **`strata-gfx906:0.2.9t2`**（`sha256:40305cad…`，8.17 GB）：`/src` = v0.2.9 全树 8187 文件（含 12 补丁）"
       "+ `/opt/strata/components/engine/0.1.55-linux-x86_64-hip-gfx906`（234 文件，`--verify` ok）"
       "+ `/opt/strata/terminal`（Terminal 0.2.9 / build 0.1.55，自带 CPython 3.12.15）+ `/opt/strata/seed`（29 MB）"
       "+ `/usr/local/bin/strata`（wrapper，`PORT=8090`）。回滚：`0.2.9t`/`0.2.9`/`0.2.9s1`/`0.2.8p2` 四代容器都在 |")
assert s.count(old) == 1, "image row anchor %d" % s.count(old)
s = s.replace(old, new, 1)

old4 = "组件 `package_engine.py --verify` 通过、门禁打印的 `img=` 就是运行中的镜像。"
new4 = (old4 + "\n   **完整 = 五件套**（W848 定）：`/src` 全树 + 引擎组件 + Terminal + seed + wrapper；"
        "镜像的 `PORT` 必须对齐实际端口（我们 8090，不是 8080）。")
assert s.count(old4) == 1
s = s.replace(old4, new4, 1)

anchor = "## 4 已知的坑（每条都真踩过）"
block = (
    "## 3.1 GEMM 后端：hipBLASLt 与 rocBLAS 是两条路（W848 核实）\n\n"
    "- **gfx906 没有 hipBLASLt 内核**：`/opt/rocm/lib/hipblaslt/library` 里 gfx906 命中 **0**（ROCm 7.14 与 10.1 都是 0）"
    "⇒ 那条路在 gfx906 上不可用，`stage_tuning.py` 报 `plain hipBLAS there` 属正常。\n"
    "- 我们吃的是 **rocBLAS 表**：`/data/gfx906-rocblas-5.5.0.txt`"
    "（首行 `STRATA_ROCBLAS_TUNING_V1 gfx906 5.5.0.cd957402309`，60 行）。\n"
    "- **表头绑 rocBLAS 完整版本** ⇒ 换 ROCm（5.5 → 5.7）表即失效，必须重 tune，"
    "否则 prompt 路径退回默认解（瘦 N 桶历史差 1.27×）。\n\n"
    + anchor
)
assert s.count(anchor) == 1
s = s.replace(anchor, block, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("SESSION_STATE ok")

# ---------- PROGRESS ----------
p = ROOT + "PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read().rstrip("\n")
rows = []
if "X15" not in s:
    rows.append("\t".join([
        "B10环境与版本", "X15", "ROCm 7.14 升 10.1.0 / HIP 7.16（rocBLAS 5.5→5.7）", "W848", "count", "1", "0", "OPEN",
        "本机 routek-base:gfx906-rocm101-hip716 已有 ROCm 10.1.0 + HIP 7.16.26323 + rocBLAS 5.7 + gfx906 内核；"
        "soname 同名（libamdhip64.so.7 / librocblas.so.5）⇒ 现二进制可直接加载。代价：rocBLAS 表失效须重 tune；"
        "需过 KL 与 read 六档/decode 门槛 3%。官方 10.1 矩阵无 gfx906（TheRock/社区构建）", "W848-2"]))
if "X16" not in s:
    rows.append("\t".join([
        "B10环境与版本", "X16", "Terminal + seed + wrapper 装进镜像", "W848", "count", "1", "1", "DONE",
        "package_terminal.py --commit aef9d256 → 96MB tar（CPython 3.12.15 pin 走 gh-proxy，sha256 对上）；"
        "镜像 0.2.9t2 装 terminal/seed(29M)/wrapper 且 ENV PORT=8090；容器 52a5d5c7b587 health 243s；"
        "strata status 在容器内可用。更正：此前终端根本不存在（上轮说 0.2.4 产物是错的）", "W848-3"]))
if rows:
    s += "\n" + "\n".join(rows) + "\n"
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("PROGRESS 新增 %d 行" % len(rows))

# ---------- 基线 ----------
p = ROOT + "PROD_BASELINE.tsv"
b = io.open(p, encoding="utf-8-sig").read()
b = b.replace("image\tstrata-gfx906:0.2.9", "image\tstrata-gfx906:0.2.9t2")
b = b.replace("image_id\tsha256:7905395debb90dd059d1e2b4207cd147e6c4b15aea67854937ed8580fcd678c7",
              "image_id\tsha256:40305cadf60f03ceb0b37edb61402ce338144a5f5fa5cf13f17eff7738bd8307")
b = b.replace("started\t2026-10-31T12:18:29.476214245Z", "started\t2026-10-31T12:46:00.172688628Z")
b = b.replace("recorded\t2026-10-31T20:28:00+08:00", "recorded\t2026-10-31T20:55:00+08:00")
b = b.replace("src_files\t8143", "src_files\t8187")
if "\nterminal\t" not in b:
    b = b.replace("component\t0.1.55-linux-x86_64-hip-gfx906 (234 files, manifest 02166a3d)",
                  "component\t0.1.55-linux-x86_64-hip-gfx906 (234 files, manifest 02166a3d)\n"
                  "terminal\t0.2.9 build 0.1.55 (tar sha256 0c5dd7a1, seed 29M, wrapper PORT=8090)")
io.open(p, "w", encoding="utf-8", newline="\n").write(b)
print("baseline ok")
