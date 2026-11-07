# W848 · 三问答：hipBLASLt 表 vs rocBLAS 表 / ROCm 10.1 / Terminal 装起来

> 2026-10-31 20:33–20:52。对应机主三问 + 一条动作。**其中一条是我上一轮说错了，先更正。**

---

## 0 先行更正：`/opt/strata/terminal` 与 `seed` 根本不存在，不是我说的"0.2.4 时代产物"

W847 我写"terminal + seed 是 base 的 0.2.4 时代产物"——**没核**。实测：

```
docker exec strata166-407 ls /opt/strata   →   只有 components
docker run --rm strata-gfx906:0.2.8p2 du -sh /opt/strata/*  →  （空，路径都不存在）
```

也就是说镜像里从来没有终端，`/usr/local/bin/strata` 也没有。所以"我要用的"这件事，**不是升级，是从零装**。本轮已装好（§3）。

---

## 1 "gfx906 没有 hipBLASLt 调优表" 与 "用 rocBLAS 表" 是什么意思

引擎的 prefill 稠密 GEMM 有**两条后端路径**，源码在 `src/prefill/gemm.cu`：

| 路径 | 源码位置 | 表 | 面向 |
|---|---|---|---|
| hipBLASLt | `#include <hipblaslt/hipblaslt.h>`（51-52）、`hipblasLtMatmulAlgo_t`（193）、`strata::prefill::hipblaslt::TuningTable`（201） | `tools/hip/` 下按 **(arch, hipBLASLt 版本)** 组织的表，由 `packaging/stage_tuning.py` 装进包 | 新架构（gfx12xx） |
| rocBLAS | `#include <rocblas/rocblas.h>`（60）、`RocBlasState`（449-473） | **`STRATA_ROCBLAS_TUNING`** 指向的 `STRATA_ROCBLAS_TUNING_V1 <arch> <rocBLAS 完整版本>` 文件，行是 `type N K ldy T solution` | 通用/老架构 |

**一句话**：它们是两个不同库的调度表，不是同一件事的两种存法。

- ~~在 gfx906 上 **hipBLASLt 根本没有内核**：`/opt/rocm/lib/hipblaslt/library` 里 `grep -c gfx906` = **0**~~ **判据作废（W851 §6，AUDIT16 P2-17）**：该目录**根本不存在**，"命中 0"是空目录的产物。结论仍成立，正确判据见下：`TensileLibrary_lazy_gfx906.dat` 在 hipBLASLt 路径下不存在 + `AlgoGetHeuristic` 返回 `status=3 algos=0`。所以 hipBLASLt 那条路在 gfx906 上无法使用——`stage_tuning.py` 直接打印
  `no hipBLASLt table for gfx906 with hipBLASLt 100401 (the repo has: none): plain hipBLAS there`，这是**客观事实**，不是我们没配。
- 我们实际吃的是 rocBLAS 表：`/data/gfx906-rocblas-5.5.0.txt`，首行 `STRATA_ROCBLAS_TUNING_V1 gfx906 5.5.0.cd957402309`，60 行，覆盖 prompt 路径 FP16-out GEMM 的各个 `(N,K,T)` 桶；启动日志会打 `prefill gemm: rocBLAS tuning enabled (56 rows, 47 with a solution, gfx906, rocBLAS 5.5.0.cd957402309)`。

**"并到第一个"能不能做？不能。** 要并进 hipBLASLt，前提是 hipBLASLt 有 gfx906 的 Tensile 内核；AMD 从未为 gfx906 出过（10.1 里也没有）。硬做只能得到"没有可用 algo"的错误。**所以现在的处理方式就是唯一可行的**，而且它带来的是实测收益（P107/P108：瘦 N 320x10240 桶 1.27×）。

**但注意一个耦合（这是 §2 的关键）**：rocBLAS 表头写着**完整 rocBLAS 版本** `5.5.0.cd957402309`，换了 rocBLAS 版本这张表就作废（引擎会打印为什么没用，然后退回 rocBLAS 默认解）。

---

## 2 ROCm 有更新版：**10.1.0 / HIP 7.16，本机就有**

| 来源 | ROCm | HIP | rocBLAS | gfx906 内核 |
|---|---|---|---|---|
| 生产镜像 `0.2.9t2` | 7.14（`ROCM_BUILD=7.14.0-gfx906+20260802001858`） | 7.14.60850 | 5.5.0.cd957402309 | rocblas/library/gfx906 在 |
| **`routek-base:gfx906-rocm101-hip716-torch215-tv030-df1`** | **`/opt/rocm/.info/version = 10.1.0`** | **7.16.26323** | **5.7**（librocblas.so.5.7） | rocblas/library/gfx906 在 |
| `routek-vllm:0.28.0-gfx906-rocm721-devbase` | 7.2.1 | 7.2.53211 | 5.2.70201 | — |
| `docker.1ms.run/mixa3607/llama.cpp-gfx906:v0.5.0-rocm-7.14` | 7.14 | 7.14.60850 | 5.5 | — |

**上网核实（不是猜）**：
- AMD 官方 **ROCm 10.1.0 兼容矩阵里没有 gfx906**（列出的是 gfx950/gfx942/gfx90a/gfx908/gfx1201/gfx11xx/gfx1030/gfx1151…）⇒ 10.1 的 gfx906 支持来自 **TheRock/社区构建**，不是 AMD 官方发行版。我们的 `routek-base` 正是这种构建（4 周前自己做的 vLLM 基座），HIP 7.16 + rocBLAS 5.7，**带 gfx906 的 rocblas 内核**。
- 公开社区镜像 mixa3607 目前仍是 **7.14**（`v0.6.0-rocm-7.14-cuda-13.4.2`，6 小时前更新），没有 10.1。
- soname 兼容：`libamdhip64.so.7`、`librocblas.so.5`、`libhipblaslt.so.1` 在两代里**同名** ⇒ 现有 0.1.55g 二进制理论上能直接加载，不必重编。

**升级代价与判据（不是"换一下就行"）**：
1. 换 ROCm 就换 rocBLAS 5.5 → 5.7，**我们的 60 行表立刻失效** ⇒ 必须重新跑 tune，否则 prompt 路径退回默认解（历史实测默认解在瘦 N 桶差 1.27×）。
2. 换 userland 可能引入数值差 ⇒ 要过 KL/逐位门（提示侧 KL ≤ .0139 那套标尺）。
3. 因此这是**一轮实测**，不是一次配置：候选镜像（0.2.9t2 + `/opt/rocm` 换成 10.1）→ A/B read 六档 + decode → 若 ≥3% 再 tune 新表 → 再过 KL。

已登记 `PROGRESS X15`（OPEN），判据与顺序写在那里；**没有擅自切换**，因为生产刚稳定、且要占停服窗口。

---

## 3 Terminal / seed：从零装好并落产

### 3.1 造 Terminal 发行包（按上游 `packaging/package_terminal.py`）

- 需要 pinned 的独立 CPython：`cpython-3.12.15+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz`。
  github 直连 **被墙**（`curl: (28) Connection timed out`），走 `gh-proxy.com` 下到本地缓存，**sha256 逐位等于 pin** `5864001b…af63`。
- 打包时先被拒一次：`the commit of these sources is unknown (no .git here, no --commit, no STRATA_COMMIT)` ⇒ 加 `--commit aef9d256…`（= 分支 HEAD）后通过。
- 产物：`strata-terminal-0.1.55-linux-x86_64.tar.gz`，**96 MB**，sha256 `0c5dd7a1…`；锁文件 `packaging/locks/runtime-linux-x86_64-cp312.txt` 全部按 hash 装入自带解释器。

### 3.2 装进镜像（与上游 Dockerfile 的 terminal stage 同构）

```
FROM strata-gfx906:0.2.9
COPY term.tar.gz /tmp/ ; 解包 → /opt/strata/terminal
seed：/src 的应用文件 + 裁剪后的 llama.cpp（只留 gguf-py / ggml/CMakeLists.txt / LICENSE）→ /opt/strata/seed
/usr/local/bin/strata ← docker/strata-wrapper.sh
ENV PORT=8090        ← 这一层是必须的，见 3.3
```

成品：`strata-gfx906:0.2.9t2`，id `sha256:40305cad…`，**8,170,906,109 B（8.17 GB）**，`/src` 8187 文件。
`/opt/strata` 现在三件齐：`components`（引擎组件 0.1.55）+ `seed`（29 MB）+ `terminal`。

### 3.3 踩到的坑：镜像 `PORT=8080` 而生产在 8090

wrapper 是这么定地址的：

```sh
STRATA_URL="${STRATA_URL:-http://127.0.0.1:${PORT:-8080}}"
```

镜像默认 `PORT=8080`，而我们的 serve 是 `--port 8090` ⇒ `strata status` 报
`strata: cannot reach Strata server: URLError`。**加一层 `ENV PORT=8090`** 后：

```
docker exec strata166-407 strata status
  STRATA  Overview    [LIVE]
  Model qwen3.8-flash-next-ud-q4_k_xl-abliterated  READY
  First engine token 1.079 s    Completed 4
  Hardware  GPU 0  Radeon Instinct MI50 31.2/32.0 GiB  0%  47 C  17 W
```

即"我要用的"这条通了：容器内 `strata status` / `strata monitor --once` 直接可用，不需要手输地址与 key。

---

## 4 本轮落产

| 项 | 切换前 | 切换后 |
|---|---|---|
| 镜像 | `0.2.9`（无 terminal/seed） | **`0.2.9t2`**（`sha256:40305cad…`，8.17 GB） |
| `/opt/strata` | 只有 `components` | `components` + `seed`(29 MB) + `terminal` |
| `/usr/local/bin/strata` | 不存在 | 存在，`strata 0.2.9 (build 0.1.55; python 3.12.15)` |
| 容器 | `8225132ac038`（0.2.9t） | **`52a5d5c7b587`**，health **243 s**，restarts=0，PORT=8090 |
| 门禁 | — | **PASS**，`img=strata-gfx906:0.2.9t2` |
| 服务面 | — | `/health` ok、`slots=7463 vram_free=920 pcie=0.20`、read 2575 tok 4.56 s、decode 128 tok 38.9 tok/s（冷） |
| 回滚 | — | 容器 `pre-w848b`(0.2.9t) / `pre-w848`(0.2.9) / `pre-w847`(0.2.9s1) / `pre-w846`(0.2.8p2) 全在 |

## 5 现在的"完整"清单（W847 的三件套升级为五件）

| 成分 | 状态 |
|---|---|
| `/src` 全树 | v0.2.9 + 12 补丁，8187 文件 |
| 引擎组件 | `0.1.55-linux-x86_64-hip-gfx906`，234 文件，`--verify` ok |
| Terminal | 0.2.9（build 0.1.55），自带 CPython 3.12.15 + 锁定的 wheels |
| seed | 29 MB（应用 + 裁剪 llama.cpp），`strata install` 离线用 |
| wrapper | `/usr/local/bin/strata`，`PORT=8090` 对齐生产 |
| ROCm | 7.14（**唯一还没升的一项**，见 §2 与 `X15`） |
