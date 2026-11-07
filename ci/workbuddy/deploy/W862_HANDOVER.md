# W862 · 交接（新会话接手用）

> 生成 2026-11-01 14:3x CST。本次会话：W861 收尾（hipBLASLt 转 DONE_NEG + 推 GitHub）→ W862（单请求 decode 的 GEMV 带宽）
> → AUDIT17（审计 W856–W862）。**机主用法：自己一个人用，主要是单请求，明确要求"控制并发"。**

---

## 0 一句话现状

生产没坏、没停、没换二进制；**找到一个 1.52× 的 GEMV 改进，已实测、已逐位验证、已打进源码树，但还没部署**。
另外审计出上一轮（W861）的 decode 占比数字不能复现，已在原文加更正横幅，账本 `R22` 已标"口径作废"。

## 1 生产实况（2026-11-01 14:3x 现取）

| 项 | 值 |
|---|---|
| 容器 | `strata166-407`，`Up 11 hours`，镜像 `strata-gfx906:0.2.9-101` |
| 引擎 | `/data/bin/strata-0.1.55g --serve --pack /data`，`engine started 2026-10-31 19:31:55 UTC`（= 11-01 03:31 CST） |
| config | `/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json`，md5 **`fe194fbaff93a6d377c168c812d60c5e`**（注意：已不是 W775 记的 `ff8cb97…`） |
| 显存 | 33 470 955 520 B / 34 342 961 152 B ⇒ **只剩 ~870 MB** |
| `/health` | `{"status":"ok","max_context":262144,...}` |
| GPU | 空闲时 0%；`--spec 4` 开着 ⇒ 单请求 decode 走**投机验证窗口**（ncols≈6） |

## 2 本轮做了什么（W862）

1. **确认了单请求 decode 的真实形状**：`verify.cpp:1516` 把窗口 token 数当 `ncols` 传给 `native_mmvq`；
   `layer.cpp:179` 的普通路径才是写死 1。⇒ 「单请求」实际是 **ncols≈6**，不是 1。
2. **定位瓶颈**：ncols=6 时 Q8_0 wave kernel 每波只算 **R=1** 行 ⇒ 一个权重块的激活载入和 dp4a 不跨行共享；
   叠加 34 字节块（`qs` 在 +2）使每 8 字节要 **4 次 u16 载入**。
   已排除：**占用率**（VGPR 36–127，每 CU 8–28 waves）、**L1 激活重读**（激活只有 2.2 KB 时仍慢 3.3×）。
3. **改法 = 每波行数 R**（生产里 R 本来就是模板参数，只写死 `constexpr int R = 1`）。真实 kernel、生产 flags 实测：

| ncols=6 | R=1 | R 表 | |
|---|---:|---:|---|
| GDN qkv 2560→10240 | 153.4 µs | **85.3** | 1.80× |
| GDN gate 2560→6144 | 93.4 | **52.7** | 1.77× |
| QSA q 2560→12288 | 153.8 | **86.1** | 1.79× |
| out 6144→2560 | 86.8 | **53.7** | 1.62× |
| **整层（106.54 MB）** | **613.6** | **399.9** | **1.53×** |

整层连续发射 **622.6 → 409.1 µs**，原始权重带宽 **171 → 260 GB/s**。
**ncols=1 只有 1.01×（噪声内）** —— 收益全在多列路径，即单请求验证窗口。

4. **逐位等价已验证**：真实 kernel，ncols=1 与 ncols=6 各 9 个形状全部 `diff=0`。纯调度改动，不改数值。

## 3 源码树状态（**必读，这是本轮唯一没回收的状态**）

`/home/albus/strata166/pr/strata-fork` 里 **`git status` = `M src/kernels/cuda/native_mmvq.cu`**（R 表已打入）。

- 备份：`src/kernels/cuda/native_mmvq.cu.w862bak`
- patch 幂等：`albus/w862/patch_wave_rows.py`
- 运行期回退：env `STRATA_MMVQ_WAVE_ROWS=1`（= 旧行为，不用重编）
- **彻底回滚**：`cd /home/albus/strata166/pr/strata-fork && git checkout HEAD -- src/kernels/cuda/native_mmvq.cu`
- 风险：**任何用这棵树构建的新镜像都会静默带上 R 表**（AUDIT17 P1-3，处置待机主定）

选 R 的两条约束（都有实测支撑）：`R × NCOLS ≤ 12`（ncols=6 时 R=4 有 24 个累加器，实测 118 µs，比 R=1 还差）、
`n_out / (4R) ≥ 120`（640 行的小矩阵在 ncols=1 时 R=4 只有 40 block，10.8 µs 反而比 R=1 的 5.2 µs 慢一倍）。

## 4 未闭环（按优先级）

| 序 | 项 | 下一步动作 | 代价 |
|---|---|---|---|
| 1 | **R23 上生产** | 重建引擎 → 建新镜像（`0.2.9-102`）→ 停服 → 同镜像内用 env 做 A/B（默认 R 表 vs `STRATA_MMVQ_WAVE_ROWS=1`） | 停服 10–15 min |
| 2 | **R22 重算** | 从 pack manifest 逐层枚举真实 Q8_0 张量与字节（已知：36 GDN + 12 QSA；HC 的 Q8_0 日志实为 **0.63 GiB**；embedding 644 MiB 在 host 映射内存），再乘实测带宽 | 零干扰 |
| 3 | **R 表实测化** | `--group single` 扫 ncols 1..8 × 各形状，按项目 `IlRows` 格式（ncols × n_out 五档，0=普通 kernel，只留赢 ≥3% 的格子）出表 | 零干扰，需重编 |
| 4 | AUDIT17 P1-2/1-5/1-6 | 回填 W856「已解，见 W858 §1」；W861 §4 第三条理由改结构论证；制度加「改工作树=改生产资产」 | 文档 |
| 5 | AUDIT17 P1-1 | W857 的 ring 结论降级 UNRESOLVED，补 repeat | 需停服 |

## 5 铁律（本轮新增三条，其余见 `.workbuddy/memory/MEMORY.md` §1）

1. **手工重编必须逐字复制 `build.ninja` 的 `FLAGS / DEFINES / INCLUDES`**。
   实测代价：漏 `-DNDEBUG` 整份慢 **47%**；把 `include/strata/hip_compat` 当成 `include/strata/platform/hip_compat`
   整份慢 **45%**。两次都差点把 A/B 结论带偏。
2. **改 `pr/strata-fork` 工作树 = 改生产资产**：必须登记（改了哪个文件 / 备份在哪 / 怎么回滚）。
   原来的「停服许可制」只管进程，管不到源码树。
3. **每 token 折算必须写明除数**：除「接受 token 数（2.36）」与除「列数（6）」差 **2.54 倍**。
   W861 与 W862 一个用一个，结果 59% vs 16%，互相矛盾（AUDIT17 P0-1）。

## 6 坑（本会话踩过，别再踩）

- `native_mmvq.cu` 单 TU 重编 **8–10 分钟**。要筛方向就用 `albus/w862/q8_wave_lab.cu`（自足内核，**几秒编译**），
  但它基线比生产慢 4%，**只能筛方向、不能落数**。
- 显存只剩 ~870 MB：bench 的缓存副本数必须压（`min(8, 64MB/bytes)`，总 ~320 MB）；2.3 GB 的旧口径跑不起来。
- `albus/rs.py -c "..."` 有 **~200 s 硬超时**（sleep 也一样），长任务必须 `nohup ... &` + 轮询。
- shim 会吃引号/反斜杠：**脚本一律推文件再执行**，不要在命令行里写嵌套引号。
- 生产 `--spec 4` 开着；如果哪天关掉，R 表的收益会基本消失（ncols=1 只有 1.01×）。

## 7 文件索引

| 文件 | 内容 |
|---|---|
| `deploy/W862_GEMV_BANDWIDTH.md` | 本轮主文档：口径纠正、实测表、逐位等价、落地形态、外部三证 |
| `deploy/AUDIT17_W856_W862.md` | 审计 W856–W862（P0 3 / P1 6 / P2 5 / P3 1） |
| `deploy/AUDIT_INDEX.md` | 已加 AUDIT17 行 + 三条未结清项 |
| `deploy/W861_DECODE_BANDWIDTH.md` | **头部已加更正横幅**（§3 绝对数字作废） |
| `albus/w862/q8_wave_lab.cu` + `lab2_run.sh` | 自足内核（秒级编译），扫 R × 布局 × ncols，含逐位一致性检查 |
| `albus/w862/q8_group_bench.cpp` + `group_run.sh` | 链生产库的组/多流 bench（`--group single\|all\|same\|check`、`--cols`、`--rows`） |
| `albus/w862/patch_wave_rows.py` | 幂等 patch（带备份），把 R 表打进 `native_mmvq.cu` |
| `albus/w862/prod_build2.sh` | 用 **CMake 逐字 flags** 重编 + A/B 的脚本 |
| `.workbuddy/memory/2026-11-01.md` | 当日流水（W861 收尾 + W862 全部实测 + 编译 flags 陷阱） |
