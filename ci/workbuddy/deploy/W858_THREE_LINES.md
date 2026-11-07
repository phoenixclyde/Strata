# W858 三线并行：routed stream 判否 / gfx906 roofline / hipBLASLt 卡在 stinkytofu

> 2026-11-01 01:07–01:55。机主令：「多线并行推进」。
> 三条线互不冲突：A 走源码（编译+停服 A/B）、B 走构建（CPU-only）、C 走测量（表驱动 + 微基准）。
> 生产全程只用一次停服窗口，收尾已恢复（`0.1.55g` / env 6 / md5 `29b15bb4` / restarts 0）。

## 0 结论先行

| 线 | 结论 | 一句话证据 |
|---|---|---|
| **A** routed stream（上游 #4283） | **判否（REJECT）** | 1K 档 **+7.6%**（唯一超出噪声的回退）；8K 只 **−2.2%**（低于 3% 门槛）；`wait copy` 每 token 反而从 0.269 涨到 0.347 |
| **A'** depth 扫描（16→256） | **回退减半但仍不采纳** | 1K 从 +7.6% 降到 **+3.8%**，`wait copy` **0.347→0.313**（单调）⇒ 预取深度是 wait copy 的主因，drop 逻辑本身无收益 |
| **B** hipBLASLt codegen | **已跑完 → 能力已证、加载器不通、收益不成立** | 见 `W858_HIPBLASLT_FINAL.md`：gfx906 的 hsaco 生成成功，但 rocblaslt 连原厂 gfx906 库也拒收 |

> **口径统一（AUDIT17 P3-1，2026-11-01 15:2x 由 W863 补）**：本行与 `W858_HIPBLASLT_FINAL.md` L4 的说法统一为
> 「**结构等价 + 上游路径未维护**」——gfx906 无矩阵指令 ⇒ 只能 VALU ⇒ 与 rocBLAS 同构；non-MI 的 17 个 `MI*` 字段
> 无维护 ⇒ 即便全通也不会更快、还可能静默算错。**不要再用当时那组 decode 占比数字当理由**（已作废，见 AUDIT17 P0-1/P0-2）。
| **C** gfx906 roofline | **拿到硬基线** | rocBLAS 在本模型 14 个形状上：**T=256 → 12.0 TFLOPS（峰值 45%）**，T≥4096 → **18.5（70%）** |

**由 C 引出的新杠杆（已登记 R18）**：prefill GEMM 的算力利用率**由 chunk 大小决定**（45%→70%）。
这不是 kernel 问题，是"一次喂多少 token"的问题——而我们的 `chunk auto` 从未按这条量过。

---

## 1 A 线：移植与实验

### 1.1 移植（干净）

```
git fetch upstream pull/4283/head   → fcb0e399
git worktree add -B gfx906/routed-stream gfx-routed aef9d256
git cherry-pick -x 3956b94a  → ee597b19
git cherry-pick -x fcb0e399  → f2c5e412
```

- 5 文件 **+665/−8**（`CMakeLists.txt`、`docs/DETAILS.md`、`include/strata/prefill/routed_stream.hpp`(新,160)、
  `src/prefill/prefill.cpp`、`tests/prefill/routed_stream_test.cpp`(新,410)）。
- **单测先跑**（header-only、no-GPU）：`routed_stream_test: OK`，随机 12 个种子 + 6 组线程走查。
  每个种子的丢弃比例 **49–93%**（例：`seed 39 entries 518 unrouted 344 dropped 244 (71%)`）。
  ⇒ 移植没走样，且"未路由专家"确实占大头——这是它看起来该有收益的原因。
- 引擎：`ninja` **164/164**，`strata 0.1.55`，md5 **`9924f3a0`**，38,571,360 B。

### 1.2 四臂（同一停服窗口内做完）

| 臂 | exe | env | depth |
|---|---|---|---|
| A | `strata-0.1.55g` | `TIMING=1` | — |
| B | `strata-0.1.55-routed` | `+ROUTED_STREAM=1` | **16**（默认） |
| A2 | `strata-0.1.55g` | `TIMING=1` | — |
| B256 | `strata-0.1.55-routed` | `+ROUTED_STREAM=1` | **256** |

每档 2 预热 + 1 实测，**只用每档最后一条**（`P231`）。四档约 290 / 1100 / 2100 / 7900 token。
`ready` 分别 274 / 376 / 274 / 237 s。

### 1.3 结果（引擎自己的 `prefill timing … wall`，归一成 ms/1k token）

| 档 | A | A2 | **基线(A+A2)/2** | B@16 | B@256 |
|---|---:|---:|---:|---:|---:|
| ~290 tok | 4359 | 4027 | 4193 | **4010 (−4.4%)** | **3969 (−5.4%)** |
| ~1.1K | 2113 | 2127 | 2120 | **2280 (+7.6%)** | **2201 (+3.8%)** |
| ~2.1K | 1742 | 1763 | 1753 | 1769 (+0.9%) | 1848 (+5.4%) |
| ~7.9K | 1412 | 1342 | 1377 | 1347 (−2.2%) | 1345 (−2.3%) |

**噪声地板 = 5%**：A 与 A2 是同二进制同配置，8K 档差 **5.0%**（1412 vs 1342）。所以只有 1K 档的 +7.6% 是硬回退。

### 1.4 相位给出机制（这是这轮最有用的一条）

`wait copy` 归一成 **ms/token**：

| 臂 | 1.1K 档 | 2.1K 档 |
|---|---:|---:|
| A / A2（生产） | 0.250 / 0.269 | 0.153 / 0.150 |
| B@depth16 | **0.347** | 0.173 |
| B@depth256 | **0.313** | 0.163 |

⇒ ① `wait copy` **随预取深度单调下降**（16→256 少了 10%），说明它确实由"拷到多前面"决定；
② 但**即便 256 也回不到基线** ⇒ 发布路由/放行判断本身另有成本；
③ 所以「少拷未路由专家」这条收益，在我们这套流水线上**被预取变浅的代价吃掉了**。

> 这条与 W857 的 ring 负对照合起来才完整：`STRATA_PREFILL_RING=8`（改 ring 槽位）对 read 毫无影响，
> 而 `ROUTED_STREAM_DEPTH`（改**在途拷贝数**）有明显影响 ⇒ **wait copy 由"在途拷贝数"决定，不由 ring 槽位数决定。**
> R15 原来把这两件事混在一起看，现在分开。

### 1.5 判否的边界

- 判据写的是「read ≥3%（同实例）且 8K 回退 ≤2%」。实测：**没有任何一档 ≥3% 的改进**（最好 −5.4%，但那是 290 tok 档、
  且在噪声内），1K 档 **+7.6% 回退**。⇒ **REJECT**。
- 不采纳不等于白做：它**把 wait copy 的自变量定位到了"在途拷贝数"**，这是 R15 一直缺的那条。

---

## 2 C 线：gfx906 roofline（不讲故事，只用可溯源数）

### 2.1 表驱动：rocBLAS 在本模型真实形状上的实测算力

调优表每行都带实测（`# a ms -> b ms`）。按 `2·T·N·K` 反算 14 个形状的合计：

| T（token） | 行数 | rocBLAS 合计 ms | 实测算力 | 占峰值(26.6 TFLOPS) |
|---|---:|---:|---:|---:|
| 256 | 14 | 4.59 | **12.0 TFLOPS** | **45.0%** |
| 512 | 14 | 7.84 | 14.0 | 52.7% |
| 1024 | 14 | 13.19 | 16.7 | 62.6% |
| 2048 | 14 | 24.37 | 18.0 | 67.8% |
| 4096 | 14 | 47.58 | 18.5 | 69.5% |
| 8192 | 14 | 94.88 | 18.5 | 69.7% |

**读法**：同一批 kernel，**只因为 M 从 256 变到 8192，算力利用率从 45% 涨到 70%**（1.54×）。
这是"短 chunk 天生吃亏"的直接量化，也是 R18 的依据。

### 2.2 自写微基准（`albus/w858/bench_gfx906.cpp`，10.1 镜像内 hipcc 交叉编译）

| 项 | 实测 | 参照 | 读法 |
|---|---|---|---|
| HBM 读 | **711 GB/s**（3 次 304→605→711，首轮是升频） | spec 1024 | 69%；这是 gather/blob 拷贝的地板 |
| LDS 无冲突 | **1490 GB/s** | — | — |
| LDS 32 路冲突 | **388 GB/s** | — | **3.84×** ⇒ G8(padding) 的天花板，**前提是 kernel 真的 LDS-bound** |
| fp32 FMA | 4.3–6.1 TFLOPS | peak 13.3 | **不可用**：只有峰值 1/3，手写依赖链没打满 |
| int8 dot4 | 16.5 TOPS（1 链）/ 9.0（4 链） | peak 53 | **不可用**，同上 |
| fp16 pkFMA | 被常量折叠成 0.026 ms | — | **作废**（已加 `threadIdx` 依赖仍未逃掉 DCE） |

> **纪律**：手写"峰值"基准只在打满流水线时才有意义。这三项没打满，**不进任何结论**；
> 算力参照一律用 §2.1 的 rocBLAS 实测（它才是"可达上限"）。

---

## 3 B 线：hipBLASLt codegen（**已被后续跑完，见 `W858_HIPBLASLT_FINAL.md`**）

> 本节记录的是"卡在第 2 层（stinkytofu）"时的中间态。后续把五层依赖全部打通后，
> 结论升级为：**能生成 gfx906 的 VALU kernel；但 rocblaslt 没有 gfx906 的加载路径；且收益结构上不成立**。

依赖链一层层剥开，每层都留了证据：

| 层 | 现象 | 处置 |
|---|---|---|
| ① Python 包缺失 | 镜像只有 `_rocisa.abi3.so`，`import rocisa.rocIsa` 失败 | 从源码装 |
| ② 构建后端 | `scikit-build-core` / `nanobind` 缺 | **清华源没有该包（`from versions: none`），阿里云可用** |
| ③ origami | rocisa CMake 找 `../../../../shared/origami` | `git sparse-checkout add shared/origami`（12 个 hpp） |
| ④ **stinkytofu** | `CMakeLists.txt:162` → `FATAL_ERROR "stinkytofu not found via find_package or sibling directory"` | **无开关可关** ⇒ 这就是当前墙 |

- 这层墙是**构建依赖**，不是 gfx906 能力问题。要继续就得再拉 `shared/stinkytofu`（可能连带 LLVM 开发件），
  成本未知 ⇒ 先记 BLOCK，不再盲投。
- 顺带两个工具坑（都写进 `SESSION_STATE §4`）：
  ① PyPI 直连读超时（293 kB 的包也超时），必须给 `-i` 国内源 + `--timeout 90 --retries 6`；
  ② **内层 `bash -lc '...'` 里出现单引号会截断整段脚本**（`print('x')` 让后面的命令全没跑，只报 `unexpected EOF`）。

---

## 4 顺手回答的一个 UI 疑问（机主 01:25 截图）

截图：Decode "—"、Prefill "666 t/s"。都不是抓取坏了：

- **666 = 真值，但只是最后一条请求**：`prompt 8245 tokens … read in 12373 ms (666.4 tok/s)`。
  同一轮其它档：253 tok → 165 tok/s、1919 → 513。卡片只显示最后一条。
- **Decode "—" = 我的探针 `max_tokens=1`**（`mt_read.py:54`）：1 个 token 没有相邻间隔，算不出 t/s。
  引擎侧一直有值：`1 generated in 26 ms (38.4 tok/s)`。
- 收尾后补了一次**真解码**（`max_tokens=240`）：**240 tokens / 5102 ms = 47.0 tok/s**，
  drafts accepted **128/153（83.7%）**，客户端墙钟 6.39 s（含 1.28 s prefill）。
  ⇒ 现在这张卡会显示 47.0。

---

## 5 三节汇报

**生产（现取）**：`strata166-407` / `0.2.9-101`(`d4afd5f5`) / 引擎 `0.1.55g`(`29b15bb4`) / ROCm 10.1.0 / 表 84 行 /
args 33 / **env 6** / `started 17:49:01Z` / **restarts=0** / `/health` ok。
唯一变化：`started` 因本轮三次重启前移（17:38:56 → 17:49:01），其余一字未动。

**落产**：**0**。四个臂全部回滚；多出来的两个二进制 `/data/bin/strata-0.1.55-routed`(9924f3a0)、
`strata-0.1.55-banner`(a10af384) 留在原处作证据，配置里都没引用。

**方案进度**：见 `PROGRESS.tsv` 实跑（R5 判否、R6 结案、新增 R18）。

---

## 6 改动清单

- 新增本件；`albus/w858/{build_a.sh,build_b1.sh,ab_routed.sh,ab_depth.sh,bench_gfx906.cpp}`。
- 远端：`gfx906/routed-stream @ f2c5e412`（已推 origin）；
  `166:data/w858_build_routed.log`、`w858_ab_0138xx.txt`、`w858_depth_*.txt`、`w858_hblt_b1.log`。
- 账本/方案/登记表/状态页本轮同步（见 §5）。
