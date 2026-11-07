# -*- coding: utf-8 -*-
"""W848：STATUS 追加第七节 + 当日记忆追加。"""
import io, datetime

p = "D:/workbuddy_space/strata_ws/deploy/STATUS_2026-10-31.md"
s = io.open(p, encoding="utf-8").read().rstrip()
s += """

## 7 本轮（W848）：三问答 + Terminal 从零装好

### Q1 「gfx906 没有 hipBLASLt 调优表」vs「我们用 rocBLAS 表」——是两条路，不是两种存法

源码 `src/prefill/gemm.cu` 里同时有两套：`hipblaslt`（`hipblasLtMatmulAlgo_t`、`hipblaslt::TuningTable`，第 51/193/201 行）与
`rocblas`（`RocBlasState`，第 449-473 行，表由 `STRATA_ROCBLAS_TUNING` 给）。

- **gfx906 上没有 hipBLASLt 内核**：`/opt/rocm/lib/hipblaslt/library` 里 `gfx906` 命中 **0**（7.14 与 10.1 都是 0）⇒ 那条路在这个卡上不可用；
  `stage_tuning.py` 打 `plain hipBLAS there` 是客观事实，不是我们漏配。
- 我们吃的 rocBLAS 表：`/data/gfx906-rocblas-5.5.0.txt`，`STRATA_ROCBLAS_TUNING_V1 gfx906 5.5.0.cd957402309`，60 行；
  启动日志 `rocBLAS tuning enabled (56 rows, 47 with a solution, gfx906, rocBLAS 5.5.0.cd957402309)`。
- **"并到第一个"做不到**：并进 hipBLASLt 的前提是它有 gfx906 的 Tensile 内核，AMD 从未出过 ⇒ 硬做只会拿到"无可用 algo"。
  **现在的做法是唯一可行且有实测收益的**（P107/P108：瘦 N 320x10240 桶 1.27×）。
- 代价要记住：表头绑 **rocBLAS 完整版本**，换 ROCm 表即失效。

### Q2 ROCm 有更新版：10.1.0 / HIP 7.16，本机 `routek-base` 里就有

| 来源 | ROCm | HIP | rocBLAS | gfx906 内核 |
|---|---|---|---|---|
| 生产镜像 | 7.14 | 7.14.60850 | 5.5.0.cd957402309 | 有 |
| **`routek-base:gfx906-rocm101-hip716-*`** | **10.1.0** | **7.16.26323** | **5.7** | 有 |
| `routek-vllm:…rocm721-devbase` | 7.2.1 | 7.2.53211 | 5.2.70201 | — |
| mixa3607 公开镜像（最新） | 7.14 | 7.14.60850 | 5.5 | — |

上网核实：AMD **官方 ROCm 10.1.0 兼容矩阵里没有 gfx906** ⇒ 10.1 的 gfx906 支持来自 TheRock/社区构建；
mixa3607 的公开镜像目前仍是 7.14。soname 两代同名（`libamdhip64.so.7`、`librocblas.so.5`、`libhipblaslt.so.1`）⇒ 现二进制可直接加载。

**所以升级不是"换一下"**：rocBLAS 5.5→5.7 会让 60 行表作废（必须重 tune，否则 prompt 路径退回默认解），还要过 KL 与 read 六档。
已登记 **`X15`（OPEN）**，判据与顺序写在 `PROGRESS.tsv` 与 `deploy/W848_TERMINAL_ROCM_QA.md §2`；**没有擅自切换**。

### Q3 Terminal / seed：**上一轮我说错了——它们根本不存在**，本轮从零装好

`docker exec strata166-407 ls /opt/strata` 只返回 `components`；0.2.8p2 base 里连 `/opt/strata` 都没有。
所以不是"升级旧终端"，是"没有终端"。

| 步 | 结果 |
|---|---|
| 打 Terminal 包 | `package_terminal.py --commit aef9d256` → **96 MB** tar（`strata-terminal-0.1.55-linux-x86_64`），sha256 `0c5dd7a1…` |
| CPython | pin `3.12.15+20261009`；github 直连超时，走 `gh-proxy` 下载，**sha256 与 pin 逐位相同**（`5864001b…`） |
| 装进镜像 | `0.2.9t2`：`/opt/strata/{terminal,seed}` + `/usr/local/bin/strata`；seed **29 MB**（应用 + 裁剪 llama.cpp：`gguf-py/ggml/CMakeLists.txt`） |
| 修的坑 | 镜像 `PORT=8080`、生产 8090 ⇒ wrapper 的 `STRATA_URL` 指错端口，`strata status` 报 URLError；加 `ENV PORT=8090` 后正常 |
| 功能自证 | `docker exec strata166-407 strata status` → `[LIVE]`，`Model … READY`、`GPU 0 Radeon Instinct MI50 31.2/32.0 GiB`、`Completed 4` |

### 落产与状态

镜像 `0.2.9` → **`0.2.9t2`**（`sha256:40305cad…`，8.17 GB）；容器 `8225132ac038` → **`52a5d5c7b587`**，health **243 s**，restarts=0，
门禁 **PASS**（`img=strata-gfx906:0.2.9t2`），`/health` ok、`slots=7463 vram_free=920 pcie=0.20`；
回滚件四代容器 `pre-w848b`(0.2.9t)/`pre-w848`(0.2.9)/`pre-w847`(0.2.9s1)/`pre-w846`(0.2.8p2)。

**"完整"的定义升级为五件套**（已写进 `SESSION_STATE §1 铁律④`）：`/src` 全树 + 引擎组件 + Terminal + seed + wrapper，
且镜像 `PORT` 必须对齐实际端口。进度 **10 块 / 95 条 / 已结 36（37.9%）**。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("STATUS §7 ok")

m = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md"
t = io.open(m, encoding="utf-8").read().rstrip()
t += """

## W848 三问答 + Terminal 从零装（20:33–20:55）

- **hipBLASLt vs rocBLAS 是两条路**（gemm.cu 里两套）：gfx906 **没有 hipBLASLt 内核**（hipblaslt/library 里 gfx906=0，7.14/10.1 都 0），
  所以只能用 rocBLAS 表 `/data/gfx906-rocblas-5.5.0.txt`（`STRATA_ROCBLAS_TUNING_V1 gfx906 5.5.0.cd957402309`，60 行）。
  "并进 hipBLASLt" 不可能（AMD 从未给 gfx906 出 Tensile 内核）。**表头绑 rocBLAS 完整版本** ⇒ 换 ROCm 表即失效。
- **ROCm 有 10.1.0 / HIP 7.16**：本机 `routek-base:gfx906-rocm101-hip716-torch215-tv030-df1` 里就是（rocBLAS 5.7，带 gfx906 内核）；
  官方 10.1 矩阵**无 gfx906**（TheRock/社区构建）；mixa3607 公开镜像仍 7.14。soname 同名 ⇒ 现二进制可加载。
  升级代价：表作废须重 tune + 过 KL/read 门 ⇒ 登记 `X15` OPEN，未擅动。
- **更正上轮错误**：`/opt/strata/terminal`、`seed`、`/usr/local/bin/strata` **本来就不存在**（不是"0.2.4 旧产物"）。
- **Terminal 已装**：`package_terminal.py --commit aef9d256` → 96MB tar（sha256 `0c5dd7a1…`）；CPython pin 3.12.15+20261009
  走 gh-proxy 下（直连超时），sha256 与 pin 逐位相同 `5864001b…`。
  镜像 `0.2.9t2`（`40305cad…`，8.17GB）：`/opt/strata/{terminal,seed(29M)}` + wrapper；**必须 `ENV PORT=8090`**，
  否则 wrapper 的 `STRATA_URL` 默认 8080 → `strata status` 报 URLError。
  容器 `52a5d5c7b587` health 243s；`docker exec … strata status` 出 `[LIVE]` 面板（MI50 31.2/32.0 GiB）。
- **"完整"= 五件套**（写进 SESSION_STATE 铁律④）：/src 全树 + 引擎组件 + Terminal + seed + wrapper，且 PORT 对齐。
- 进度：10 块 / **95 条** / 已结 **36（37.9%）**；主线 67 条 53.7%；台账欠账 0。
"""
io.open(m, "w", encoding="utf-8", newline="\n").write(t + "\n")
print("memory ok")
