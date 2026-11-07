> **AUDIT18 / A1（2026-11-01）—— 本文的「+4.0%」降级为「方向可信、幅度不可信」。**
>
> 用同一批原始数据（`166:w863/ab_20261101_144755.txt`）按 2×CV 判据重算：
> ARM T 48.60（CV **2.32%**）vs ARM B 46.75（CV **3.09%**），中位差 **+3.96%**；
> 而 2×CV = **5.41%**（pooled）/ **6.18%**（max）⇒ **落在噪声内**。
>
> 之前引用的「2.12% 阈值」来自**另一次** CV=1.06% 的 bench，套到这一次是错的。
> 仍成立的证据：两轮配对同向（+4.31% / +3.53%）、微基准 `q8_group_bench` 在 ncols=2 上 **1.156×**。
> 要证实幅度须按新方法重做（n≥12、丢 2 发、交错），代价约 20 分钟停服，暂不做（逐位等价、无害）。
>
> 详见 `deploy/AUDIT18_W863.md`。

# W863 · R23 上生产（0.1.55h）+ 同镜像 A/B

> 2026-11-01 14:2x–15:2x CST。机主当轮决定：按原计划上生产并 A/B。
> 本轮**改动了生产资产**（源码树 / 引擎二进制 / config 的 exe），逐项登记在 §5。

---

## 0 结果

| 项 | 结果 |
|---|---|
| 生产引擎 | `strata-0.1.55g` → **`strata-0.1.55h`**（md5 `9a2ff874…`，40,764,992 B） |
| R 表 | **已生效**（实测表，不是 W862 那条公式；理由见 `W863_WAVE_ROWS_TABLE.md`） |
| A/B（同镜像同二进制，只差 env） | **R 表 48.6 tok/s vs R=1 46.8 tok/s ⇒ +4.0%** |
| 健康 | `/health ok`、`loaded true`、VRAM 33,456,709,632 B（改前 33,470,955,520，−14 MB） |
| 权重账目 | `499 native projection matrices, 3619.14 MiB` —— 与改前逐字一致 |
| 逐位等价 | W862 已在真实 kernel 上验过 9 形状 `diff=0`；本轮未改数值逻辑（只改 R 的取值来源） |

## 1 先修掉一个真缺陷：`STRATA_MMVQ_WAVE_ROWS` 从来不存在

交接件与 W862 文档都写「运行期 `STRATA_MMVQ_WAVE_ROWS=1` 可回旧行为，不用重编」。
`[源码核实]` 全树 `grep STRATA_MMVQ_WAVE_ROWS` **只命中一行注释**（`native_mmvq.cu:2373`），
没有任何 `getenv`。也就是说：

- **回滚开关是假的**；A/B 按原计划根本做不了（同镜像换臂只能靠 env）。
- 只有 `native_mmvq_set_wave_rows(int)` 这个 C++ API（bench 在用），引擎里没人调。

⇒ 本轮补了 `wave_rows_env()`（进程内 static 读一次，见 §5 的 patch 2）。
`[实测]` 修前 `strings | grep -c STRATA_MMVQ_WAVE_ROWS` = **0**，修后 = **1**；`nm` 的 `wave_rows_for|kWaveRows` = **2**（旧二进制 0）。
判据按项目铁律走：**独有符号 + 独有字符串**，不看 CMake 选项。

## 2 构建方式（重要：`build.ninja` 不能重生成）

`gfx029-build` 的 configure 里有 `add_subdirectory("/llama.cpp/ggml")`（`CMakeLists.txt:1973`），
166 上没有这个 checkout ⇒ **任何 CMake 重生成都会失败**（`albus/w863/d7_cfgerr.sh` 有原文）。
而 ninja 每次都会先跑 `cmake -P VerifyGlobs.cmake`，确实有一个 glob 对不上 ⇒ 必然触发重生成。

⇒ 做法：**不重生成**，只跑 ninja 自己列出的三条命令（`ninja -t commands strata` 逐字取，不手抄任何 flag）：

| 步 | 命令 | 来源 |
|---|---|---|
| 1 | `clang++ … -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 … -c native_mmvq.cu` | `ninja -t commands` 第 72 行 |
| 2 | `llvm-ar qc libstrata_kernels.a …` | 第 105 行 |
| 3 | `clang++ … -o strata libstrata_engine.a … libstrata_kernels.a …` | 末行 |

- `build.ninja` md5 前后一致（`ced688a1…`），未被改写。
- 编译行里的 flag 与 `build.ninja` 的 `FLAGS/DEFINES/INCLUDES` 一致：
  `-O3 -DNDEBUG -std=c++20 --offload-arch=gfx906`、`-DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8`、
  `-isystem /src/include/strata/platform/hip_compat`（**不是** `include/strata/hip_compat`）。
- 单 TU 编译 ≈ **6 分钟**（两次合计 12 分钟），链接 ≈ 2 分钟。

## 3 A/B（同镜像 `0.2.9-101`、同二进制 `0.1.55h`，唯一变量 = env）

| 臂 | env | 说明 |
|---|---|---|
| **T** | 不设 | 实测表（本次上生产的形态） |
| **B** | `STRATA_MMVQ_WAVE_ROWS=1` | 旧行为 R=1 |

协议：`T B T B` 交错；每臂 `docker restart` → `/health` 轮询（实测 233–259 s）→ 丢前 2 个请求 → 3 次固定贪心长生成
（同一提示、`temperature 0`、`max_tokens 480`，提示命中缓存 ⇒ 只计解码）。

| 臂 | run1 | run2 | run3 | 中位 |
|---|---:|---:|---:|---:|
| T（第 1 轮） | 47.0 | 48.4 | 48.8 | **48.4** |
| B（第 1 轮） | 44.7 | 46.4 | 47.1 | **46.4** |
| T（第 2 轮） | 47.6 | 49.8 | 50.2 | **49.8** |
| B（第 2 轮） | 45.8 | 49.1 | 48.1 | **48.1** |

- **配对比**：第 1 轮 **+4.31%**、第 2 轮 **+3.53%**；全样本中位 48.6 / 46.8 ⇒ **+4.0%**。
- 两轮**同向**，且量级与预测（`W863_WAVE_ROWS_TABLE.md` §4：≈2.9%）相符并略高
  （head 也是多列、HC up 也在表内，微基准口径没算这两项）。
- **注意离散**：臂内极差 ±3%，全会话有单调上漂（T 48.4→49.8、B 46.4→48.1）⇒ 只能靠**配对**判，
  单臂绝对值（如 48.6 vs 47.0 那个跨会话对比）不可用。
- 顺带再证一次窗口长度：每臂 `drafts accepted ~200 of ~230` ⇒ **≈0.9 draft/窗口，T≈2**。

## 4 部署后状态（15:1x 现取）

```
容器   strata166-407  strata-gfx906:0.2.9-101  Up (restart 后)
引擎   /data/bin/strata-0.1.55h  (md5 9a2ff8742f9918f657a468a7baeb177c)
日志   engine started 2026-11-01 07:07:13 UTC
health {"status":"ok", ..., "loaded":true}
显存   33,456,709,632 B / 34,342,961,152 B
权重   499 native projection matrices, 3619.14 MiB
config exe=/data/bin/strata-0.1.55h，env 6 项（无 STRATA_MMVQ_WAVE_ROWS）
```

## 5 登记（改生产资产，按纪律逐项）

### 5.1 源码树 `pr/strata-fork`

`git status` = `M src/kernels/cuda/native_mmvq.cu` + 3 个未跟踪备份。

| 文件 | 内容 |
|---|---|
| `native_mmvq.cu` | patch 1 = 实测表（`patch_measured_table.py`）；patch 2 = `STRATA_MMVQ_WAVE_ROWS` 真读（`patch_env_switch.py`）。均幂等 |
| `native_mmvq.cu.w862bak` | **HEAD**（无任何 wave rows） |
| `native_mmvq.cu.w863bak` | W862 的公式态 |
| `native_mmvq.cu.w863bak2` | 实测表、但还没有 env 开关 |

回滚：
```bash
# 回到 HEAD（彻底无 R 表）
cd /home/albus/strata166/pr/strata-fork && git checkout HEAD -- src/kernels/cuda/native_mmvq.cu
# 或回到 W862 公式态（不推荐，它在 ncols=1 时 0.982×）
cp src/kernels/cuda/native_mmvq.cu.w863bak src/kernels/cuda/native_mmvq.cu
```

### 5.2 二进制

| 文件 | md5 | 字节 |
|---|---|---:|
| `/data/bin/strata-0.1.55g`（旧，保留） | `29b15bb4418bf15a` | 38,567,520 |
| `/data/bin/strata-0.1.55h`（新，现役） | `9a2ff8742f9918f657a468a7baeb177c` | 40,764,992 |

回滚（30 秒，不重编）：config 的 `exe` 改回 `/data/bin/strata-0.1.55g` → `docker restart strata166-407`。

### 5.3 config

`exe` 字段：`/data/bin/strata-0.1.55g` → `/data/bin/strata-0.1.55h`（**唯一改动**），
md5 `fe194fbaff93a6d3…` → `2fd30a353dd4b728…`。
备份：`data/strata-huihui-ud-iq4_xs.json.bak_w863_20261101_144303`、`…bak_w863ab_20261101_144755`。

**运行期回滚开关（这次是真的）**：config 的 `env` 里加 `"STRATA_MMVQ_WAVE_ROWS": "1"` → restart，即回 R=1。

### 5.4 未改

镜像仍是 `0.2.9-101`（`docker inspect` 已确认：`/data` 是 bind mount，**镜像不带运行中的引擎**，
`cp→.new→mv` + config 指路就是本项目的换二进制通道）。
服务不可用窗口：**6 次重启**（部署 1 + A/B 四臂 4 + 收尾 1），各 233–259 s，合计 **≈24 分钟**。

## 6 顺带查出的问题（建议进下次审计）

| 编号 | 问题 | 证据 |
|---|---|---|
| W863-1 | **`STRATA_MMVQ_WAVE_ROWS` 文档里存在、代码里不存在**；AUDIT17 没抓到 | `grep` 只命中注释；本轮已实现 |
| W863-2 | **`gen_config.py` 的 `META` 停在旧部署**：`exe=/src/build-906/strata`、tokenizer/PLE 指向 `huihui-ud-iq4_xs`（现役是 `ud-q4_k_xl`）⇒ 现在跑 `--write` 会把生产 config 写坏 | `deploy/params/gen_config.py:20-26` |
| W863-3 | `build.ninja` 无法重生成（`add_subdirectory(/llama.cpp/ggml)`，166 无此 checkout）⇒ **任何引擎重编都必须绕开 CMake** | `CMakeLists.txt:1973`，`d7_cfgerr.sh` |
| W863-4 | R23 的收益只能到 ≈4%（受 T≈2 限制）；**真正的大杠杆是草稿链长度** | `W863_WAVE_ROWS_TABLE.md` §4、`W863_R22_DENSE_BYTES.md` §5 |

## 7 复现

```bash
python albus/rs.py albus/w863/d13_deploy.sh   200   # 装二进制 + 改 exe
python albus/rs.py albus/w863/d14_restart.sh  560   # 重启 + 验证
python albus/rs.py albus/w863/d11_build3.sh   200   # 重编（改完源码后）
# A/B 由 albus/w863/d15_ab.sh 在 166 上 nohup 跑，输出 /home/albus/strata166/w863/ab_*.txt
```
本轮原始 A/B 记录：`166:/home/albus/strata166/w863/ab_20261101_144755.txt`
