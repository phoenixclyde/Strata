# W862 · 新会话开场提示词（直接复制横线之间的整段）

> 用法：新开一个 WorkBuddy 会话、工作区指向 `D:/workbuddy_space/strata_ws/`，把下面横线之间的整段粘进去。
> 生成 2026-11-01 14:5x CST。

---

接手 Strata 项目（W862 之后）。工作区 `D:/workbuddy_space/strata_ws/`，远程测试台 166（gfx906 / MI50 32GB）。

**第一动作（按序，别跳）**
1. 读 `deploy/W862_HANDOVER.md`（**运行期交接：§1 生产实况 / §2 本轮成果 / §3 源码树状态 / §4 未闭环 / §5 铁律 / §6 坑**）
2. 读 `deploy/AUDIT17_W856_W862.md`（刚审完 W856–W862，**3 个 P0**，其中 P0-1 会直接影响你要不要相信任何 decode 占比数字）
3. 读 `.workbuddy/memory/MEMORY.md`（长期记忆，3000 字符注入窗，现 2884）
4. 读 `.workbuddy/memory/2026-11-01.md`（当日流水，含 W862 全部实测与两次编译污染）
5. 涉及记忆件/压窗口时，**先加载技能 `routek-memory-slim`**，禁手改 MEMORY.md（机主已定死）

**机主用法（决定了主攻方向）**：自己一个人用、**主要单请求**、明确要求**控制并发**。
⇒ 别去搞多流/多实例/批量吞吐；单请求 decode 走的是**投机验证窗口**（`--spec 4` ⇒ GEMV 的 ncols≈6）。

**现状一句话**：生产没坏没停（`strata166-407` / `strata-gfx906:0.2.9-101` / 引擎 `strata-0.1.55g` / VRAM 33.5 of 34.3 GB /
`/health ok`）；找到一个 **1.52×** 的单请求 decode GEMV 改进，**已实测、已逐位验证、已打进源码树，但还没部署**。

**最该接的三件事（按序）**
1. **R23 上生产**：`pr/strata-fork` 里 `M src/kernels/cuda/native_mmvq.cu`（R 行数表已打入，备份 `.w862bak`，
   运行期 `STRATA_MMVQ_WAVE_ROWS=1` 可回旧行为，`git checkout HEAD -- <file>` 可彻底回滚）。
   要上就得：重编引擎 → 建新镜像（`0.2.9-102`，禁分批跳版）→ 停服 → **同镜像内用 env 做 A/B**（默认 R 表 vs `=1`）。
   **停服前先问机主**（W860 §5 停服许可制）。
2. **R22 重算**：AUDIT17 P0-1 已证「每 token 的 dense GEMV 字节数」两轮都算错（W861 59% / W862 16% 互相矛盾）。
   解法：从 pack manifest 逐层枚举真实 Q8_0 张量（已知 36 GDN + 12 QSA；HC 的 Q8_0 日志实为 **0.63 GiB**；
   embedding 644 MiB 在 host 映射内存），再乘实测带宽。**别再拿「9 个矩阵 × 48 层」当总量。**
3. **R 表实测化**：现在给的是公式（`R×NCOLS≤12`、`n_out/(4R)≥120`），只测了 ncols=1 与 6。
   项目惯例是实测表（`kIlRows_*` / `il_rows`：按 ncols × n_out 五档、0=普通 kernel、只留赢 ≥3% 的格子）。
   工具已在 `albus/w862/`（`q8_wave_lab.cu` 几秒编译；`q8_group_bench --group single --cols N`）。

**这个项目最容易踩的五个坑（血账）**
1. **手工重编任何 `.cu`，必须逐字抄 `build.ninja` 里的 `FLAGS / DEFINES / INCLUDES`**。
   实测：漏 `-DNDEBUG` 整份慢 **47%**；把 `include/strata/hip_compat` 当成 `include/strata/platform/hip_compat` 慢 **45%**。
   两次都差点把 A/B 结论带反。核对脚本：`albus/w862/prod_build2.sh`。
2. **`native_mmvq.cu` 单 TU 重编 8–10 分钟**。筛方向用自足内核（`albus/w862/q8_wave_lab.cu`），但它基线比生产慢 4%，
   **只能筛方向、不能落数**；落数必须回真实 kernel。
3. **显存只剩 ~870 MB**：bench 的缓存副本必须压到 `min(8, 64MB/bytes)`（~320 MB）。旧的 2.3 GB 口径跑不起来，
   W861 那张「279.5 µs / 22%」就是这么失效的。
4. **`albus/rs.py -c` 有 ~200 s 硬超时**（`sleep` 也一样）：长任务 `nohup ... &` + 轮询。
5. **shim 会吃引号/反斜杠**：脚本一律 `push_file.py` 推上去再执行，命令行里别写嵌套引号。

**纪律（本会话新立，已入 MEMORY.md §1）**
- 每 token 折算**必须写明除数**：除「接受 token 数（2.36）」与除「列数（6）」差 **2.54 倍**。
- 改 `pr/strata-fork` 工作树 **= 改生产资产**：须备份 + 给回滚命令 + 登记在案。
- 判「某功能在不在二进制里」只认 ①编译行的 `-D` ②独有符号/字符串 ③无条件横幅；不认 CMake 选项与 cache。

**汇报口径**：结论先行；数字要标清「实测 / 源码核实 / 推测」；同一轮别同时改两个变量；
不确定就去读源码或跑单变量实验，不要凭版本号或印象下结论。

---
