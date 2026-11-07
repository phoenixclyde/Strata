# W713 升级记录 ---- Strata v0.1.40.4 -> v0.1.41（gfx906 / MI50），含升级闸门

> 写于 2026-10-08 22:4x CST。上游 `Niko1221/Strata`。
> 本件 = 本波做了什么、怎么自证；方案与全量账见 `deploy/W713_PLAN.md`；审计见 `deploy/W713_AUDIT.md`。
> 环境声明：全部现场读数 **Z0=off（省电档）**；分辨力 预填 1.2-1.7% / 解码 9.5-15%。
> CR=0，不含禁用码位。

---

## 0 一页速览

| 项 | 值 |
|---|---|
| 新版 | `v0.1.41`（2026-10-08 12:14:59Z = 20:14 CST） |
| 源码指纹 | `strata-src-0.1.41.zip` = 18,961,076 B / **sha256 `e5e9a45ed42536c792157654b4d98309565f2d3797d1819c5cebe61c4d94d611`**（本机与 166 **各自下载、哈希相同**） |
| **补丁面** | **归零**（`patched=0 / verified=6 / failed=0`，构建日志实测打出 **`PATCH_SURFACE_ZERO`**）---- 补丁器降级为**纯验证 / 回归闸门** |
| 依赖 | `LLAMA_CPP_COMMIT` 未变（`3cf03257...`）=> llama.cpp 包继续复用 |
| 新镜像 | `strata-gfx906:0.1.41` / `c45268e786e1` / 6.57 GB；引擎 binary **24,982,264 B / md5 `160611838796d4b172ec3a642ccd988d`** |
| 新容器 | `strata166-405`（**现役**，22:34:28 起） |
| 切换 | 22:34:22 停 `-404` -> 22:34:28 起 `-405` -> **22:35:03 ready（35 s）**；旧容器 `Exited (0)` 保留 |
| 升级闸门 | **已跑**：服务面 7 项全过 + 中性矩阵 3 档 x 2 轮（见 §3） |
| 判定 | **中性**：三档 `reused` 与上一版**逐格相同**，冷预填 / 温 TTFT 差 **<=1.4%**（落在 1.2-1.7% 分辨力内） |

---

## 1 本版与我们相关的变更（判读按 **卡 / CPU 分开**，机主提醒后重列）

**① 补丁面归零（本次升级的实质变化）**：H1-H6 六处**上游全部已修**，其中 **H5/H6 就是我们 PR #1396 的原文**
（独立复核：`CMakeLists.txt:1270` = `if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)` 带我们写的注释；
`strata_hip.h:52` = `#define cudaEventBlockingSync hipEventBlockingSync`）。
=> 从 0.1.41 起，gfx906 构建**不需要改一行上游源码**；补丁器只做验证，上游哪天再改坏形态它会 fail-closed。
**注意证据等级**：release note 明示 "a gfx906 build that compiles again (#1396)" + 源码逐字相同 = **强旁证**；
但 **PR 的 merged 徽章 / 合并时刻 / 提交哈希未取到**（页面 JS 渲染，三路审计都试过）。

**② 可能改我们读数的三条 ---- 实测结论：都没有改变我们的数**

- **#1353「专家已在 RAM 时的 prompt reader 路径」**：官方称对某些机器曾慢 4-7 倍；我们**正是**"全专家驻 RAM + GGUF in place"场景。
  实测（§3）：冷预填 530 档 482.8 / 482.6 tok/s vs 0.1.40.4 的 481.0 / 479.7 => **+0.6%，落在分辨力内**。
  => 与官方在 4x R9700 上"无变化"的观察一致。**新候选 P35 `STRATA_STAGER_SSD`（强制走哪条路）仍留在账上**，用于判定我们走的是哪条。
- **#1454/#1465 省 320 MiB 显存**：本波只跑服务面读数（未比对启动日志的专家槽位数）=> **未测**，留在账上。
- **tokenizer 缓存**（89K prompt 0.32 -> 0.07 s）：本波未单测 => 留在账上。

**③ 与我们无关的（判读按卡/CPU 分开后）**：`--batch-groups auto`（多卡）· 短 prompt CPU 助算默认
（官方明写 "layer splits, batch and AMD are as before" => **AMD 卡不受影响**；P23 在 AMD 仍属 opt-in，候选有效）·
`STRATA_GDN_CHUNKED`（要 128 SM，我们 GPU 侧 60 CU）· `STRATA_FS_SLOTS` · `STRATA_ROUTE_RESIDENT`（改答案）·
`STRATA_STAGE_PIN`（有答案损坏报告，仅测量用）· `STRATA_SM70_TABLE`（V100）· Q2_0 档（要 AVX-512 快速内核）。

**④ CPU 侧（Intel Xeon E5-2696 v4 / 44 逻辑核 / AVX2 全有 / AVX-512 全 0，22:1x 实测）**：
- 引擎日志自认 `this CPU has no AVX-512: the expert kernels run on AVX-2` + `participating threads: 22`。
- **#795「CPU 无 AVX-512 时崩溃」**（官方措辞 hardening）=> 我们正是那一类；本版新增的构建期检查
  （反汇编内核 + Intel SDE 跑 CPU 测试，让"AVX2 路径上的宽指令"直接编译失败）对**从源码自建**的我们是白拿的保障。

**⑤ 运维**：`strata --version` 实测输出 `strata 0.1.41`；`STRATA_ENGINE_STALL_S`（挂死引擎自动重启，镜像已装 psutil）；
`STRATA_HTTP_BACKLOG=256`；`--api-key` 支持逗号分隔多键。

---

## 2 升级实施（六步）

1. **源码取证**：`gh-proxy` 下载 0.1.41（本机 9.37 MB/s），sha256 `e5e9a45e...`；全树比对 vs 0.1.40.4：
   **2,262 -> 2,422 文件（新增 160 / 改 75 / 删 0）**，新增多为 `bench/results/community-*`。
2. **补丁面复核**：对**原始树**跑补丁器 = `patched=0 / verified=6`（第二遍同，幂等）。
3. **166 侧上下文**：166 自行下载（两侧 sha256 相同）；复用 `llama.cpp-3cf0325.tar.gz`。
4. **镜像构建**：`Dockerfile-0.1.41`（新增"补丁面归零断言 + 六处复核 grep"）；构建日志实测 `PATCH_SURFACE_ZERO`。
5. **建容器**：`docker create strata166-405`（`--restart unless-stopped` / `--device /dev/kfd,/dev/dri` / `--group-add video` /
   `--ipc=host` / `--ulimit memlock=-1` / `-e HSA_OVERRIDE_GFX_VERSION=9.0.6` / `-p 8090:8090` /
   `-v data:/data` / `-v weights:/weights:ro`）---- 参数**逐项抄 -404**。
6. **切换（通用脚本）**：`deploy/scripts/switch_strata.sh <新容器>`（旧容器自动探测；300 s 轮询；失败自动回滚）。
   实测 OLD 自动识别为 `-404`，35 s 就绪，rc=0。

> **脚本升级**（本波顺手做的方案优化）：切换脚本从"一次升级一个专用脚本"改成**通用参数化脚本**；
> 另新增 `deploy/scripts/upgrade_gate.sh`（升级闸门，见 §3）。

---

## 3 升级闸门（首次实跑，判据固定、跨版本可对齐）

### 3.1 服务面（7 项，全过）

| # | 检查 | 实测 |
|---|---|---|
| 1.1 | `/v1/models` | **http=200** |
| 1.2 | models body | `loaded` / `n_ctx 262144` |
| 1.3 | 引擎版本 | **`strata 0.1.41`** |
| 1.4 | 引擎 cmdline（`docker exec` 读 `/proc`） | 三项现役参数均在（`--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192`） |
| 1.5 | LIVE config md5 | **`d2b10f0c4e8293ba010614c7acc70bea`**（未改参数） |
| 1.6 | 容器 | `-405:Up` / `-404`,`-402`,`-401`,`strata166` 均 `Exited` |
| 1.7 | 0.1.41 新增的 "lend coverage" 告警计数 | **0** => 该观察项**当场关项**（我们不走短借覆盖不足那条路） |
| 附 | 本机 `verify_config.py`（第 4 数据面含 Cmd/Binds 判定） | **PASS=16 / FAIL=0**，容器自动识别 `strata166-405` |

### 3.2 中性矩阵（3 档 x 2 轮，Z0=off）---- 与 0.1.40.4 同口径逐格对比

| 档（实测 token） | **0.1.41** 冷 -> 温 / `reused` | 0.1.40.4（B1 A 臂）冷 -> 温 / `reused` | 差 |
|---|---|---|---|
| 100（4,593 / 4,604 对 4,589 / 4,600） | 10.80 -> **10.463 s** / **0** | 10.83 -> 10.472 s / 0 | -0.3% / -0.1% |
| 220（9,993 / 10,004 对 9,989 / 10,000） | 22.84 -> **5.786 s** / **8192** | 23.10 -> 5.866 s / 8192 | -1.1% / -1.4% |
| 530（23,943 / 23,954 对 23,939 / 23,950） | 49.67 -> **16.836 s** / **16384** | 50.10 -> 16.990 s / 16384 | -0.9% / -0.9% |

冷预填（引擎自报 tok/s，每档四条全给）：100 档 **427.4 / 441.8 / 442.6 / 443.6**（首读最慢）；220 档 438.3 / 440.0（两次冷读）；530 档 482.6 / 482.8。上版（b1.log）对应：100 档 426.8 / 442.7 / 443.5 / 442.3、220 档 434.4 / 435.6、530 档 479.7 / 481.0。
530 档 **482.6-482.8**（上版 479.7-481.0）。

**口径披露（第二轮审计 P1 更正）**：上表对照列**统一取自 `b1.log` 的 A 臂（0.1.40.4）**，两侧 prompt 长度差 4 token（同脚本不同批），故严格说是「同脚本同参数、非逐字同 prompt」。

**判定：中性成立。** 三档 `reused` **逐格相同**（机制未被改动）；冷预填 / 温 TTFT 的差全部 **<=1.4%**，
落在预填分辨力 1.2-1.7% 内。**样本量声明**：每档 2 轮（n=2），故本条只判"**差小于分辨力**"，
**不判**"两版完全等价"（同 W712 §3 的边界口径）。

---

## 4 现场状态与回滚

- 现役：`strata166-405` / `strata-gfx906:0.1.41` / 端口 8090 / `--restart unless-stopped`。
- 回滚（三条旧容器任选）：`bash /home/albus/strata166/w712/switch_strata.sh strata166-404`
  （或 `-402` = 0.1.40.2）。旧容器全部保留、均 `Exited`。
- 镜像现有 5 个（0.1.39 / .40.1 / .40.2 / .40.4 / .41）；容器 5 个（-401/-402/-404/-405 + `strata166`）。
  **保留策略待定**（账上 C3；走 `docker-disk-truth` 技能）。

## 5 产物索引

| 类别 | 路径 |
|---|---|
| 本件 | `deploy/W713_UPGRADE.md` |
| 方案 / 审计 | `deploy/W713_PLAN.md` · `deploy/W713_AUDIT.md` |
| Dockerfile | `deploy/docker/Dockerfile-0.1.41`（补丁器仍为 `patch_gfx906_402.py` v3，本版**未改源码**） |
| 通用切换 / 闸门脚本 | `deploy/scripts/switch_strata.sh`（md5 `c49d8164976ac2fdce102490a0d640db`）· `deploy/scripts/upgrade_gate.sh`（md5 `ec2a0050ed4cd13e28ba273c20af15ea`） |
| 源码包 | `deploy/transfer/strata-src-0.1.41.zip` |
| 全树比对 / release 全文 | `deploy/tmp/_w713_tree_diff.txt` · `deploy/tmp/_w713_relnote.txt` |
| 补丁面 dry-run | `deploy/tmp/_w713_dry411_run1.txt` |
| 闸门原始输出 | 166 `/home/albus/strata166/w712/gate.log`；本机副本 `deploy/tmp/_w713_gate_remote.log` |
| 切换日志 | 166 `/home/albus/strata166/w712/switch.log` |
