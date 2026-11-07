# 会话状态 · 2026-11-02 03:05（新会话先读这一页）

> 一页纸的「现在是什么状态」。细节在 `deploy/` 下各 W8xx 文档与登记表，这里只放**必须知道、且容易记错**的。

## 1 生产（唯一实例）

| 项 | 值 |
|---|---|
| 容器 / 端口 | `strata166-407`（166:8090），`--restart unless-stopped` |
| 镜像 | **`strata-gfx906:0.2.9-101`**（`sha256:d4afd5f5…`，15.07 GB；= 0.2.9t2 + `/opt/rocm` 10.1）：`/src` = v0.2.9 全树 8187 文件（含 12 补丁）+ `/opt/strata/components/engine/0.1.55-linux-x86_64-hip-gfx906`（234 文件，`--verify` ok）+ `/opt/strata/terminal`（Terminal 0.2.9 / build 0.1.55，自带 CPython 3.12.15）+ `/opt/strata/seed`（29 MB）+ `/usr/local/bin/strata`（wrapper，`PORT=8090`）。回滚：`0.2.9t`/`0.2.9`/`0.2.9s1`/`0.2.8p2` 四代容器都在 |
| 引擎 | **`/data/bin/strata-0.1.55t`**（md5 `e0c6f250d2ec2ea07f781ef3e7b2fe0c`，= 分支 `gfx906/mi50` @ `d963c791` / tag `mi50-0.2.9-r27`）。回滚链：`ci/rollback.sh --exe /data/bin/strata-0.1.55s --apply`（再往前 `r/q/p/o/n/j` 都在） |
| 参数 | **17 个参数 / 33 个数组项**（`--pack ud-q4_k_xl --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --kv k8v4 --max-context 262144 --expert-cache auto --conversation-cache-mib 4096 --vram-reserve-mib 832 --mtp-window 8192 --prefill auto --prompt-cache-every 8192 --vision` …） |
| 环境变量 | **config 10 项 → 运行时 17 项**：`HSA_OVERRIDE_GFX_VERSION=9.0.6`、**`STRATA_GFX906_TUNED=1`**（展开 7 项：`ATTN_QUERY_SWIZZLE GDN_PP=2 HC_Q8 SELECT_SIMT ROUTE_TAIL_SKIP=7 MMQ_KQ HIP_PROMPT_F16`）、`STRATA_PREFILL_CPU_SHARE=auto`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、`STRATA_RESIDENT_HEADROOM_GIB=0.5`（惰性，待 R45 清）、`STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt`（84 行）、`STRATA_CKPT_MOVE_PARK=1`、`STRATA_DECODE_TIMING=1`、`STRATA_SPEC_DEPTH=1`、`STRATA_VERIFY_NODES=1`（无用，待 R45 清） |
| 实测（11-02 03:05） | 显存 **33.46/34.34 GB**、专家缓存 **7463 槽 / 21.79 GiB（每槽 3.135 MB）**、decode **≈44.4 ms/窗口 / 3.14 token/窗口**、`/health` ok、进程内错误行 0 |
| 配置文件 | `~/strata166/data/strata-huihui-ud-iq4_xs.json` 的 `.bak-w839` 是切换前备份 |

**9 条 arch 变量现在由引擎自己设**（不再写在配置里）：`GDN_HEAD GDN_PP GFX906_ATTN_QUERY_SWIZZLE GFX906_ATTN_REDUCE12 HC_Q8 HIP_PROMPT_F16 MMQ_KQ ROUTE_TAIL_SKIP SELECT_SIMT`。
启动日志会打两行 `strata: gfx906 (MI50-class): …`——**看到这两行才说明入口真的跑了**。

## 1.1 现状的拼接态（W845/W846 核实，读方案前必读）

| 层 | 实际跑的 | 与源码树的关系 |
|---|---|---|
| 引擎 | `/data/bin/strata-0.1.55g`（md5 `29b15bb4…`） | **= `gfx029` HEAD `aef9d25` 的构建产物**，可对账 |
| serve | 镜像 **`0.2.9-101`** 内建 `/src/serve`（0.2.9，`server.py` md5 `b1aa1d36…`） | **= 树里 `gfx029/serve`**（含 telemetry/app 三补丁），逐文件 md5 已对 |
| userland | **ROCm 10.1.0 / HIP 7.16.26323 / rocBLAS 5.7**（社区 TheRock 构建，官方矩阵不含 gfx906） | 与 Strata 版本无关；重建镜像必须保留那两层（见方案 §6.12） |
| 模型包 | `--pack /data/packs/ud-q4_k_xl` | **UD-Q4_K_XL**，不是 iq4_xs；配置名 `…iq4_xs.json` 属历史遗留 |

⇒ 0.2.9 的 serve 侧能力（`COALESCE_PREFILL` / `PAR_COUNTERS` / `replicas`）**已可用但默认关**（W846 落产，行为不变）。
⇒ **W847 起已无拼接**：`/src` 是 v0.2.9 全树（8143 文件），`/opt/strata/components/engine` 是 0.1.55 的 hip/gfx906 包（`--verify` 通过）。
⇒ 镜像内非 0.2.9 的只剩 `/opt/rocm`（ROCm 7.14）。**W848 已补齐 Terminal / seed / wrapper**（五件套齐），`docker exec strata166-407 strata status` 可直接出 TUI 快照。见 `deploy/W847_FULL_029_IMAGE.md`、`deploy/W848_TERMINAL_ROCM_QA.md`。

## 2 源码与仓库（硬约束）

| 位置 | 角色 |
|---|---|
| `166:~/strata166/gfx906` | 旧工作副本。分支 `gfx906/0.2.8-mi50` @ `cc8a071`（**其树本来就是 v0.2.9**：`serve/replicas.py` 存在，与 `v0.2.9` 净差 12 文件 +265/−11）保留作回滚 |
| `166:~/strata166/gfx029` | **源码真相源**：worktree，分支 **`gfx906/0.2.9-mi50` @ `aef9d25`**；另有两支：`gfx906/hipblaslt-vega20 @ d9d6ab8b`、`gfx906/mmq-plan-banner @ ec368906`（= v0.2.9 `c62d5e3a` + 1 个补丁提交，12 文件 +267/−11），已推 `origin`（0/0）；`gfx029-build/` 树外构建（产物 `strata-0.1.55g`，md5 `29b15bb4…`）。**仓库已 unshallow（4930 提交可达），`git rebase upstream/main` 可用**，助手 `~/strata166/tmp/rebase_gfx906.sh` |
| `166:~/strata166/src028` | **构建树**（不是 git；`build-028r/` 是热构建目录，增量编译约 2 min） |
| `166:~/strata166/pr/strata-fork` | 推送工作仓库（带 `pre-push` 钩子） |
| GitHub `phoenixclyde/Strata` | 远端；**上游 remote 的 push URL 已被置为 `DISABLED-no-push-to-upstream`** |

**铁律**：① 源码只在分支改，改完 `bash ~/strata166/tmp/sync_gfx906.sh` 同步进 `src028`（9 个文件按 md5 + 1 个锚点补丁器）；
② **绝不向上游 push、不开 PR**（机主 2026-10-31 明令）；
③ 部署物必须与构建产物**当场核 md5**，并跑 `verify_patches.sh`（**17 项**，当前 PASS）。

④ **升级就一次升完整**（机主 2026-10-31 定，W847）：换上游版本时**引擎 + serve + 镜像内容 + 组件包一次到位**，不留"下次再补"。
   分步会留下版本混搭（W846 曾是 serve 0.2.9 而 `/src/src` 还是 0.2.8），每轮都要先问"这层是哪一版"，而且下次还得再跳一次。
   唯一例外：为验证某补丁能否生效而临时叠一层，须当场记账、当一个会话内收口。**验收三件套**：`/src` 关键文件 md5 == 树、
   组件 `package_engine.py --verify` 通过、门禁打印的 `img=` 就是运行中的镜像。
   **完整 = 五件套**（W848 定）：`/src` 全树 + 引擎组件 + Terminal + seed + wrapper；镜像的 `PORT` 必须对齐实际端口（我们 8090，不是 8080）。
⑤ **树里 ≠ 跑着的**（W845）：serve 在镜像内建，只有 `docker exec md5sum /src/serve/…` 算数；引擎从 `/data/bin` 挂载，可对 md5。
⑥ **门禁的 `IMG` 不能写死 tag**（W847）：换镜像后它会继续查旧镜像，`image:`/`served:` 三行就成了"验的不是跑的那份"。
   已改为默认 `docker inspect strata166-407 --format '{{.Config.Image}}'`。

## 3 关键结论（别重新推导，直接用）

1. **架构默认表原本是死代码**：`apply_arch_defaults` 的调用点在 `#if defined(STRATA_USE_HIP)` 内，而 gfx906 构建只定义
   `STRATA_HIP_GFX906`。补了专属调用后（`1309b1d`）才真正生效。**判据**：`nm … | grep apply_arch_defaults`、
   二进制里 `exact speed switches` 字符串、启动横幅。树里有 ≠ 二进制里有。
2. **`generate.cpp` 里还有 28 个 `STRATA_USE_HIP` 块对 gfx906 不生效**（38 个里 10 个已兼容）。**不能批量打开**
   ——W717/P23 实测全局开有副作用；只能逐块加 `|| defined(STRATA_HIP_GFX906)` 并单独 A/B。
3. **参数轴不是"最优"，是"两项判不出"**：`--spec-min-p` / `--pcie-frac` / `--pool-workers` 全部 **UNRESOLVED**
   （效应小于噪声底盘）；只有 `--adapt-*` 是"默认正确"。
4. **数值债只结清一半**：`GDN_HEAD` 位等价（EG.tsv 与 E0.tsv 的 md5 同为 `fadf1889…`），**`GDN_PP` 从未单测**（P229）。
   「0.029」只代表 5 项 / 45 个位置 / 不含 `MMQ_KQ`。
5. **移植收益模型已修正**：可达面 **24.19 ms（53.8%）**，30–50% 局部改善 ⇒ **−16%~−27%**（原写 33 ms/73%、−5~−10%）。
6. **测量纪律**：同配置复本之间就有 3.9–10.8% 离散（中位 6%），且**生成路径本身不可复现**（36 条同 prompt 同 seed
   贪心 → 36 个不同 sha）。⇒ 任何 <5% 的结论都要 n≥20 或改用与内容无关的量（`ms/win`、teacher-forced）。

## 3.1 GEMM 后端：hipBLASLt 与 rocBLAS 是两条路（W848 核实）

- **gfx906 没有 hipBLASLt 内核**：判据用「`TensileLibrary_lazy_gfx906.dat` 在 hipBLASLt 路径下不存在」+「`hipblasLtMatmulAlgoGetHeuristic` 返回 `status=3 algos=0`」（探针复跑留证 `data/w856_probe_hblt_101.txt`）。
  ~~旧判据「`/opt/rocm/lib/hipblaslt/library` 里命中 0」作废~~——那个目录**根本不存在**（W851 §6 自我更正，AUDIT16 P2-17）。
  **W858 又纠一条**：`/opt/rocm/lib/rocblas/library` 里 gfx906 **是有的**（在 `library/gfx906/` 子目录，含 `Kernels.so-000-gfx906.hsaco` 232,744 B）。
  早前"顶层 `grep -c gfx906` 得 0 ⇒ 没有内核"是看错了层级，那句作废。真正的结论是：**codegen 能做，rocblaslt 不认**。
- 我们吃的是 **rocBLAS 表**：现役 `/data/gfx906-rocblas-5.7.0.txt`（表头 `… gfx906 5.7.0.962d0059`，**84 数据行**/88 行文件）。历史 5.5 那份是 56 数据行/60 行文件（日志口径 `56 rows`）。
- **表头绑 rocBLAS 完整版本** ⇒ 换 ROCm（5.5 → 5.7）表即失效，必须重 tune，否则 prompt 路径退回默认解（瘦 N 桶历史差 1.27×）。

## 4 已知的坑（每条都真踩过）

- 本机 bash shim 会吞变量/引号/反引号：**脚本一律写成 `.sh`/`.py` 文件再跑**，不要内联长命令；路径用字面量。
- **`sync_gfx906.sh` 会 `git reset --hard origin/gfx906/0.2.8-mi50`** ⇒ **未 push 的 commit 会被当场丢掉**
  （2026-10-31 实测：本地 commit `cc8a071` 被 reset，靠 `git reflog` 找回）。**顺序必须是：改 → commit → push → sync**。
- 配置里的 `exe` **必须是容器内路径 `/data/bin/...`**；写宿主路径 `/home/albus/...` 会让 serve 启动器抛
  `FileNotFoundError` 并进入 `Restarting` 循环（同日实测，三臂全崩；`/data` 是目录挂载，容器内能看到，但启动器不做映射）。
- `rsh_run.py` 走流式发送，`$VAR` 在本地就被展开——远端脚本里别指望 shell 变量。
- `/proc/<pid>/environ` **不反映 `setenv`**（exec 时快照）→ 验证运行时 env 只能靠横幅/行为。
- 引擎 stderr 落在配置里的 `log` 路径（`/data/strata-huihui-ud-*.log`），**不在 docker logs**。
- shallow clone 里 `git show <tag>:<path>` 未 fetch 的 blob 会**静默返回空**，`grep -c` 得 0 → 会误判"上游没有这个词"。
  要核上游内容走 **GitHub raw/contents API**。
- 实验脚本必须内置"无论成败恢复生产"，否则会把 166 的 8090 留在测试容器上。
- 停服一次 ≈ 4 min 载入（load 到 `/health` ok 约 240 s），任何 A/B 都要把这段时间算进成本。
- **配置里的一切路径都是「容器内路径」**（W842 踩一次、W851 又踩一次）：`exe` 要 `/data/bin/...` 而不是宿主
  `/home/albus/strata166/data/bin/...`；`STRATA_ROCBLAS_TUNING` 同理要 `/data/gfx906-rocblas-*.txt`。
  写成宿主路径时引擎不报错、仍打印 `rocBLAS tuning enabled` 之外的状态 —— W851 四臂因此全部
  `cannot open rocBLAS tuning file (...)`，整轮 A/B 作废（两边都跑默认内核，差异全在噪声里）。
  **判据**：每臂启动后必须看到该臂期望的那一行（`84 rows` vs `56 rows`），且要用**启动前日志行数做 mark** 只读新行。
- **改了 `serve/` 不会自动生效**：`/src` 是镜像内建（挂载只有 `/models`、`/data`）⇒ 必须
  ① 重建叠层镜像（`FROM 当前镜像` + `COPY serve /src/serve` 等，秒级）→ ② **重建容器**（`restart` 不够，
  容器镜像在创建时固定）→ ③ `docker exec … md5sum /src/serve/server.py` 自证。W846 已踩过一遍，脚本 `albus/w846/swap.sh`。
- **门禁的 `IMG` 不能写死 tag**（W847 实测）：换镜像后它会继续查旧镜像，`image:`/`served:` 三行就变成"验的不是跑的那份"。
  已改成默认 `docker inspect strata166-407 --format '{{.Config.Image}}'`（取运行中的镜像）。
- **给门禁"造"产物 = 自证**：把部署二进制 `cp` 进树会让 `PROVENANCE` 恒真（W844 犯过）。门禁已改
  `find -L "$TREE" -maxdepth 3 -name strata`，比对树外构建目录的真产物；**树里不得放 `strata` 副本**。
- **`git remote add upstream` 会连 push 一起指向上游**（违反"绝不推上游"）。加完立刻
  `git remote set-url --push upstream DISABLED`。

- **所有臂共写同一个日志文件**（`/data` 是共享挂载）：A/B 里读日志必须"启动前算行数当 mark"，
  否则会把上一臂的 `version mismatch` 读成本臂的（W850 的 A2 段就混进了 B 臂的行，AUDIT16 P2-21）。
- **`wait copy` 不是"unpinned 主机拷贝"**（AUDIT16 P0-2 已查明）：埋点后跟 `wait_copied()` /
  `cudaStreamWaitEvent(m.copied[])`，GPU 等的是**专家 blob 的拷贝事件**；`prefill.cpp:3456` 是 D-5
  「issuer 线程已消除旧等待」的解释性注释（过去时）。查这条要看预取深度/发射节奏，不要先去改 pinned。
- **停服必须事先获批**（W860，`P242` / 方案 §6.13）：单卡 + 模型驻留 33.5/34.3 GB ⇒ 起不了第二实例，
  任何引擎级 A/B 都是"停服→换二进制→重启→测→再重启"。R4 两轮 A/B 触发 **4 次 engine started**
  = 4 次重载 ≈16 分钟空窗，把机主堵了约 10 分钟（日志 `81404` 显示 19:31:55 才回到生产）。
  ⇒ 默认只做读日志/读源码/限核 CPU 构建；停服先攒批、写清四项、等获批。
- **自己起的 git checkout 会挂很久**（W860 实测 4 小时 20 分还在 blobless fetch）：`git read-tree`/
  `checkout HEAD -- .` 在 blobless+sparse 的仓库里可能长期不退出。跑完要 `ps` 确认，并 `git config gc.auto 0`
  防止 `gc --auto` 再触发 repack 抢 CPU/磁盘。
- **内层 `bash -lc '...'` 里不要出现单引号**（W858）：`print('x')` 会把外层单引号串截断，
  后面的命令一条都不执行，只报 `unexpected EOF while looking for matching "`。内层一律用双引号。
- **PyPI 直连会读超时**（W858）：293 kB 的包也 `ReadTimeoutError: files.pythonhosted.org`。
  必须 `-i https://mirrors.aliyun.com/pypi/simple --timeout 90 --retries 6`；
  **清华源缺包**（`scikit-build-core` 报 `from versions: none`），只能作备选。
- **改 env 的脚本不能从"基线配置"重建**（W857 实测）：`setenv()` 每次从 `/tmp/*_cfg_base.json` 重建，
  会把上一臂改过的 `exe` 和别的 env 一起冲掉（B 臂因此丢了 `STRATA_PREFILL_TIMING`）。
  ⇒ 多键要一次改完，或基于**当前**配置改。
- **`docker stop/start` 后 serve 可能第一次起引擎失败**（W857：第一次没到 ready 就退了，docker `restarts=0`、
  无 traceback，第二次才起来，整体 ≈14 min）。`wait_health` 余量给 ≥900 s，并打印第几次尝试。
- **查"当前策略"类日志必须 `tail`**：`grep -m2 'ple-io'` 会抓到 10 月 20 日的 `--ple-io mmap` 旧行，
  让人误判生产策略（本轮自己踩了一次）。

## 5 文档地图

| 文件 | 内容 |
|---|---|
| `deploy/W839_ARCH_ENTRY.md` | **本轮**：入口接线、三臂验证、落生产、28 死块清单、同步/门禁 |
| `deploy/W858_HIPBLASLT_FINAL.md` | **hipBLASLt 支线收束**：能生成 gfx906 VALU kernel（hsaco 已产出）、rocblaslt 拒收（连原厂库也拒）、收益不成立 |
| `deploy/W858_THREE_LINES.md` | **本轮**：R5(#4283) 判否（1K +7.6%）、R6 roofline 结案（45%→70%）、hipBLASLt 卡 stinkytofu |
| `deploy/W860_BLOCK_AND_REAL_TRAFFIC.md` | **本轮**：堵点时间线（实验臂 19:26–19:31）、真实流量 5356 条分档（短档贵 9.5×）、R20 自查证伪、**停服许可制** |
| `deploy/W857_R17_MMQ_AND_R15.md` | **本轮**：48/48 层 MMQ（`dequant` = gather+q8 量化）、ring 深度不是约束、R5 升第 1 序 |
| `deploy/W856_TRIPLE_LINE.md` | **本轮**：R16 撤回（MMQ 选项≠定义）、hipBLASLt P0 = BLOCK、R17 banner 支线已编译 |
| `deploy/AUDIT16_W844_W853.md` | **最新审计**（W844–W853）：P0 4（**P0-4 已撤回**）/ P1 9 / P2 10 / P3 3 + §11 误判复盘 |
| `deploy/AUDIT13_W832_W839.md` | 审计 W832–W839：P0 3 / P1 8 / P2 6，撤回 3 |
| `deploy/AUDIT_INDEX.md` | 审计链 AUDIT6→13 覆盖表 + 未结清清单 |
| `deploy/AUDIT_LEDGER.tsv` | 42 条结论台账（AUDIT12 26 条 + AUDIT13 16 条） |
| `deploy/params/PARAM_REGISTER.tsv` | **226 行**，P001–P229；改参/判决的唯一账本 |
| `deploy/patches/LOCAL_PATCHES.tsv` | 9 条本地补丁（文件 / 标记 / commit） |
| `deploy/W836_BRANCH.md` | 分支与 10 个 commit、同步脚本边界、两条方法错误 |
| `deploy/W835_GFX906_PORT_FEASIBILITY.md` | gfx906 可移植性判定（KI / llama.cpp / Strata 自身） |
| `deploy/W832_OPT_PLAN_V2.md` | **唯一方案权威**（§0.0）：队列 / 判据 / 停机条件 / 执行记录（§4.1–4.6） |
| `deploy/W828_UPSTREAM_028_PORT.md` | 0.1.54 升级与 decode/prefill 全套测量（§6.x） |

## 6 下一步

**队列不写在这里。唯一权威是 `deploy/W832_OPT_PLAN_V2.md`**（§0.0 定权，§2 队列，§4 执行记录，§5 改源码项）。
本节只记"当前在建哪一条"，避免两处各持一份队列（2026-10-31 已因此分叉过一次：本节旧版把 P227 列 #1，
而权威件 §4.1 已把该轴判 UNRESOLVED 关账）。

- 已结：**R1 `SELECT_SIMT=2` 判否**（`deploy/W842_SIMT2.md`：=2 生效但无收益；生产留 n4 + 配方 =1）。
- 已结：**R2 / X1 / M5 / X15 / X17 / X18**（W849/W852/W853）。下一枪 = **R16 打开 `STRATA_PREFILL_MMQ` 的 gfx906 构建门**（`CMakeLists.txt:145`，AUDIT16 P0-4）：生产走 FP16 专家路径，dequant+GU+down 占 45–52%，而 MMQ 是唯一能整体拿掉 dequant 的路径。
- 其后：**R6 roofline 三条（不停服）** → **R3 移植 #3987（decode top-k split，见 `#3987` 正文才有解码窗口口径）** → **R4 #4158**。
- 仍在等的：**P1-c / P227 `pcie_frac_auto`**（§2；证据 `albus/w841/W841_P227_PLAN.md`），但它要先让位给上面两条纯配置项。
- **源码面总台账 = `W832_OPT_PLAN_V2.md` §6**（R1–R13 + 28 死块 + 分支事实 + 上游 gfx906 160 条里的 13 条要点）。

## 7 每轮汇报口径（2026-10-31 立）

三节固定顺序：**生产情况 → 落产情况 → 方案进度**。不要手写数字，跑一条命令：

```
python tools/round_report.py --write      # 生成 deploy/STATUS_<日期>.md
```

| 数据源 | 作用 |
|---|---|
| `deploy/PROGRESS.tsv` | **进度的唯一分母**（9 块 / 72 条；`count` 为权重，死块池算 28 条） |
| `deploy/PROD_BASELINE.tsv` | 落产指纹（exe md5 / cfg md5 / image id / started）；不一致就说明本轮动过生产 |
| `166:~/strata166/tmp/state_q.py` + `verify_patches.sh` | 生产实况与门禁，每次现取 |
| `tools/plan_lint.py` | **待办是否都进了方案**（四向：PROGRESS/登记表/正文/方案 R 号），exit 0 才算收工 |
| `tools/audit_recheck.py` | **审计整改是否真改完**（跑最新审计件 §10 的复核命令，全 PASS 才算） |
| `166:~/strata166/tmp/verify_tip.sh` | **“生产是否就在分支顶端”的唯一检查**（W849）：branch/HEAD/tree、工作区、与 origin 一致、**/src 逐文件 md5 == HEAD 树**（5319 文件）、引擎二进制 == 构建产物、门禁；全过才打印 `TIP-OK` |

**铁律（机主 2026-10-31 立）**：任何一轮识别出的待办必须在**同轮**进 `PROGRESS.tsv`（`ref` 指回 P 号），
并在收工前跑 `python tools/ledger_audit.py` —— **exit 0（欠账 0）才算闭环**；登记表结论出来就改 `status`。

两条规矩：**"已结"包含判否与不适用**（有结论就算结，否则分母会虚高）；**死块池 28 条单列**，
避免"28 个选做项"把主线进度压成假象（主线 44 条才是真实进度）。

## 9 明天从哪开始（2026-11-02 03:05 收工）

> **【AUDIT27 更正 2026-11-07】** 本节标题写的是「2026-11-02 收工」，下面这行队列是**当时的快照**，不是现行队列；本件按 `W832 §0` 的规矩**不自持队列**。现行队列只读 `deploy/W832_OPT_PLAN_V2.md §0.1`（AUDIT27 校正为 R51 → R95 → R94 → R91 → R89 → R46 → R49 → R50）。

**队列（`W832 §6.5`，唯一排序处）**：`R59`（精度账）→ `R61`（MMQ PMC 口径，决定 R60 做不做）→ `R60`（stream-k，已编译通过）→ `R58`（MMQ 三段计数）→ `R49`（per-file `max-ilp`）→ `R50`（router GEMV）→ `R30′` → `M3`

**R51 已结 DONE_NEG（2026-11-03 02:1x，`W904`）**：原题（移植 iacop 向量载入）作废——我们早已是 128-bit；按「解包 ALU 是瓶颈」改 Q4_K 内核后 **prefill 慢 6–10%**（8936→9449 ms @6440 tok），无溢出。教训：微基准必须含被调函数的完整固定成本（R55 同错）。后继 **R58** 先拆段计数再动码。

**R55 已结 DONE_NEG（2026-11-03 01:3x，`W902`）**：`ds_swizzle` 与 `__shfl_xor` 置换逐位等价（W902 实测），`qsa_select` 的 ISA 翻转 −73% bpermute，但 `qsa_block_topk` 在 32K/131K/262K **±0.4%**（ids 全等）⇒ 该核不是交换受限；微基准 3.14× 不可外推。分支 `exp/R55-swizzle` 保留。

**R52 已结 DONE（2026-11-03 01:1x，`W901`）**：32-lane 是**契约**（垫片默认宽度 32，硬件实测成立）⇒ 无缺陷；真正的债只有 mask 被丢弃（HIP 7.14 要求 64 位）。波槽：router GEMV 85%、megakernel 20%、top-10 仅 0.17%。

**R54 已结 DONE_NEG（2026-11-03 01:1x，`W899 §7.10`）**：wave64 版与生产 T=1…8 逐位相等、T≥4 快 11–16.6%，但生产 `avg T 2.8–3.7`，端到端窗口更贵（51.1 vs 47.9 ms）⇒ 不进生产。分支 `r54-port` 保留（`STRATA_MK_GDN` 默认关）。

**W895 校准（2026-11-02 22:3x，23:2x 按单流口径改）**：同卡同模型（MI50 32G / Qwen3.8-Flash-Next 177B MoE）把重打包+DPP+QSA 融合+稀疏 decode+并行 top-k 全做完后，**单用户 decode 62→62 持平**，收益全在 prefill（8K 887→1251、32K 867→1561）。⇒ **验收只认 prefill，decode 只守不劣化**；多流数字只作背景（引擎支持但本项目不做，R57 已撤）。

**W893 新增（2026-11-02 21:4x，零停服）**：`ki` = `KIntegrated/vllm-gfx906-mobydick`（166 上 `routeK/base/ki030-main` @6ccbb03），是 gfx906 专用 vLLM；上游 vLLM 明写 gfx906 不受支持。CK（`ROCm/composable_kernel` @d84d8e2）的 `GPU_TARGETS` **不含 gfx906**、全仓库 0 处 gfx906 引用 ⇒ 无 CK 可移植路径。**wave64 是补上的漏项**：64 lane/波、40 波/CU，我们按 `WARP=32` 记账的全部波数要重算；`ki` 实测半波块 ≈ 全波块 2×。`max-ilp` 开关在本机 clang 上已验证改代码生成（汇编差 66 行），但 `build.ninja` 当前 0 条 `-mllvm`。

**W892 §8 外部源码复核**：分享会话的“Strata 无 gfx906 内核 / 全部借旧 MMQ / iacop 有 tiled+v_dot8”三条均被源码否决；17 个仓库已落 `albus/w895/forks/`。真候选只有 R50（router）、R46 的 Castagna QSA 外证、R51（prefill MMQ load 移植）。

**W892 V6.1 历史复核**：R47 `EXPERT_V2K` 是误重开——W824 已三次无差异、P153 已 REJECTED，且当前 s27 源码相对当时 0 diff，故 DONE_NEG、**不重启**。R48 锁频同已关闭；分享会话只新增 R49 一条零停服探针。

**R36 已结（W873 §5）**：路由阶段 3.895 ms/8.29% 成立，但 top-k 只 0.46 ms；真靶是 router BF16 GEMV **2.09 ms / 60.2 GB/s**，故转 R50。

**今晚连折两条「新序第 1」，都是过期派生量**：
- **R38**（HC）→ DONE_NEG：`STRATA_TSUM=1` A/B 实测 down −19.5%、up +26.1%，净 **+2.8%**；down 全部只占窗口 6.4% ⇒ 原「2.7×」物理上不可能。
- **R37**（专家读）→ DONE_NEG：实测 **411 GB/s = 46.4% 屋顶**，对纯读探针 487 是 **0.84×**；原「1.65×」来自 T=1.79 的旧口径 + 每槽 2.99 MB（算错，真值 **3.135**）。

**硬规矩（已写进 `W832 §6.5`）**：任何条目要写 GB/s / 倍数 / 占比，**先跑 `python3 ~/strata166/ci/derived_check.py` 并把输出贴进条目**，不许手算、不许抄上一轮。

**动手前先看**：`W887`（prompt attn 只跑到 FP32 峰的 11–16%，fp16 是第二步）、`W888`（KV 质量门只到 128k、今日已在现役权重补测 32k 3/3 + 128k 1/1）、`W889/W890`（HC 结案）、`W891`（专家读结案）。

**未做且需要窗口的**：①`R44` 剩下约 5 件 W7xx 原文抽查（零成本）；②`R46` 要看内核隔离吞吐需一次重建录 `STRATA_QSA_DUMP`；③`R45` 清两个惰性 env（`RESIDENT_HEADROOM_GIB`、`VERIFY_NODES`）——下次重启顺手删。
