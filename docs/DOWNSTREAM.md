# Downstream: gfx906 / MI50 维护说明

本仓是 [Niko1221/Strata](https://github.com/Niko1221/Strata) 的**下游厂商分支**：
我们跟随上游，但**不向上游提交 commit、不提 PR**。上游对本仓是只读的
（`remote.upstream.pushurl = DISABLED-no-push-to-upstream`）。

## 锚点

| 项 | 值 |
|---|---|
| 基于上游 | **v0.2.9** = `c62d5e3a15b40ea51c96aae9e8d36928965f53ab` |
| 长期分支 | `gfx906/mi50`（版本号不进分支名） |
| 发布 tag | `mi50-0.2.9-r1` |
| 生产引擎 | `strata-0.1.55h`（md5 `9a2ff8742f9918f657a468a7baeb177c`） |
| 与上游距离 | 落后 **0** / 领先 10（`git rev-list --left-right --count upstream/main...gfx906/mi50`） |

## 下游提交台账（rebase 时逐条重放；被上游吸收的立刻删）

| 序 | 提交 | 为什么 | 怎么验 |
|---|---|---|---|
| 1 | `docs: hipBLASLt on gfx906 (MI50) …` | 20 轮调查记录，结论 DONE_NEG（结构等价 + 上游路径未维护） | 文档 |
| 2 | `gfx906: replay the 0.2.8 local patches onto v0.2.9` | 0.2.8 线已验证的 gfx906 改动整体重放到 0.2.9（内容见下表） | 引擎起得来、48 层全 MMQ、decode 47 tok/s 量级 |
| 3 | `gfx906: rows-per-wavefront table for the Q8_0 wave kernel` | 单请求 decode 走投机验证窗口（ncols>1），wave kernel 每波只算 1 行，激活与 dp4a 不跨行共享 | 9 形状 × ncols 1/6 逐位 `diff=0`；同镜像 A/B **+4.0%** |
| 4 | `docs: downstream maintenance note` | 本文件 | 文档 |
| 5 | `serve/telemetry: keep the sampler thread references` | 我们的 PCIe 带宽补丁把 `self._thread = Thread(...)` 改成了匿名线程；v0.2.9 新增的 `test_responses.NoLeakedSampler` 读这个属性判"停服后采样线程结束"，属性为 `None` ⇒ CI 在每条 `gfx906/*` 上红（`main` 绿）。`close()` 现在 join 两个采样线程 | 容器内两臂：`.w863bak` **FAIL**（报错与 CI 逐字一致）/ 修复版 **OK**；CI 见 run 41288894503 |
| 6 | `ci: narrow the two push-triggered workflows` | 只在 `main` / `gfx906/mi50` / `ci/**` 上跑 push，加 `concurrency` 取消旧 run；tag push 不再触发（测的还是已测过的代码）。`paths` 未改，rebase 时最多 4 行冲突 | 见 `deploy/CI_CD_POLICY.md`；push 一次即可看到新触发生效 |
| 7 | `ci: add the downstream gate and the upstream watcher` | 新增 3 个文件（**不改上游任何文件**）：`ci/gate.py`（配置面检查）、`downstream-gate.yml`（每次改 `src/`/`include/`/`CMakeLists.txt` 就跑）、`upstream-watch.yml`（每日查上游差距，开/更新一个 issue） | `strata-ci check` 在 166 上 18 项全过；GitHub run 45cee350 **success** |
| 8 | `ci(watch): check out gfx906/mi50 explicitly` | `schedule`/`workflow_dispatch` 只跑**默认分支上存在**的 workflow，所以 `main` 上放了一份副本；副本必须显式 checkout 主线，否则它比较的是 `main`（永远 0 落后） | 手动 dispatch run 41291722718 **success**，日志 `BEHIND: 0` |

### 提交 2 里打包的历史通用修复（**已并入主线，来源分支已归档**）

| 原分支 | 内容 | 归档 tag | 现状 |
|---|---|---|---|
| `amd-monitor-name-consistency` | AMD 板名容量校验（`serve/telemetry.py`） | `archive/amd-monitor-name-consistency` | 逻辑已在主线（`telemetry.py` 读 `product_name` 并按显存校正容量） |
| `amd-monitor-pcie-link` | PCIe 代际识别（Monitor 图块） | `archive/amd-monitor-pcie-link` | 已在主线 |
| `gfx906-cpu-share-guard` | prefill 的 `arm_cpu_share` 误走 CUDA 分支 | `archive/gfx906-cpu-share-guard` | 已在主线 |
| `web-sparkline-axis-floor` | 迷你折线图纵轴下限 | `archive/web-sparkline-axis-floor` | 已在主线 |
| `gfx906-build-fixes-402` | q6_k MMQ 在 gfx9 下没编（CMake） | `archive/gfx906-build-fixes-402` | 上游重构 CMake 后 `_strata_mmq_types` 无条件含 `q6_k`；`libstrata_mmq.a` 里确有 `mmq-instance-q6_k.cu.o` |

> 这 5 条都不含硬件专属逻辑，本来该上游化；本仓不提 PR，所以靠「重放补丁」传递。
> **rebase 后必须逐条确认它们还在**（`git grep` 关键行即可），这是这套模式最脆的环节。

## 归档记录（2026-11-01，14 条 → 4 条）

| 删除的分支 | 归档 tag | 理由 |
|---|---|---|
| `gfx906/0.2.9-mi50` | `archive/gfx906-0.2.9-mi50` | 旧命名的副本（= `gfx906/mi50` 少一个 docs 提交） |
| `gfx906/0.2.8-mi50` | `archive/gfx906-0.2.8-mi50` | 上一条线，内容已并入主线 |
| `gfx906/hipblaslt-vega20` | `archive/gfx906-hipblaslt-vega20` | 实验已结（DONE_NEG） |
| `gfx906/mmq-plan-banner` | `archive/gfx906-mmq-plan-banner` | R17 诊断 banner，结论已拿到 |
| `gfx906/routed-stream` | `archive/gfx906-routed-stream` | R5/#4283 判否（REJECT） |
| 上面 5 条通用修复 | 各自 `archive/*` | 内容已在主线 |

保留：`gfx906/mi50`（主线）、`main`（上游镜像 + docs）、`bench-mi50-32gb-262k`（社区数据）、`rc/0.1.30`（上游的 rc）。

## 规矩

1. **只 fetch 上游，永不 push 上游**；分支与 commit 只在本仓。
2. **rebase，不 merge**：上游发新版就 `git rebase upstream/main`，保持薄补丁栈。
3. **分支名不带版本号**；版本信息进 tag（`mi50-<上游版本>-r<N>`）。
4. 补丁必须进本表；合并上游后逐条核对，能删的立刻删。
5. 二进制 / bench 副本 / `*.bak` **不进仓库**（放 `/home/albus/strata166/w863/`）。
6. 生产只跑「发布 tag 对应的 HEAD」；未打 tag 的提交不进生产。
7. **分支用完即归档删**：打 `archive/<名字>` tag 后删远端与本地，别让影子分支堆着。

## CI（GitHub Actions）

上游的 CI 是**租来的**：它替我们守"补丁有没有破坏上游行为"，代价是我们得让它跑得对。

- **会冒烟的两条**：`terminal-minimal-server`（服务端 Python 套件，1298 个用例）和
  `terminal-portable-monitor`（监控客户端，ubuntu + windows 矩阵）。
- **触发收窄**：`push` 只在 `main` / `gfx906/mi50` / `ci/**` 上跑；`tag` 不触发；
  `concurrency` 取消同分支的旧 run。要在一个实验分支上要 CI，就开 `ci/<名字>`。
- **红灯判据**（按序）：① `main` 绿而本分支红 ⇒ 我们的补丁，必修；② 失败在
  `Install pinned runtime requirements` ⇒ 依赖/网络，别改代码；③ 报错是
  `AssertionError: unexpectedly None` ⇒ 优先怀疑我们删了上游新代码依赖的属性。
- **不屏蔽、不 job 级重试、不删测试**：这个门是唯一能发现"改 `serve/` 改坏了"的机器证据。
- **未覆盖**：`src/` / `CMakeLists.txt` 不在任何 workflow 的 `paths` 里 ⇒ **引擎内核改动零 CI**。
  静态门（形状表 / `getenv` 存在性）可作为下一步；真机编译与逐位等价需要 self-hosted runner。

### 仓库设置层（不在 git 里，clone 看不到）

2026-11-01 把 6 个与下游无关的 workflow 设为 `disabled_manually`
（`PUT /repos/{owner}/{repo}/actions/workflows/{id}/disable`，一条调用可逆）：

| 禁用的 | 为什么 |
|---|---|
| `Docker images` | 推的是 `ghcr.io/niko1221/strata`（上游 namespace），fork 里无意义 |
| `Intake` | 上游 issue/PR 治理；**带每日 cron**，会在 fork 上每天扫一次 issue |
| `Reopen` / `Title area` / `Scripts test` | 同上，都是 PR/issue 流程，我们不发 PR |
| `Metal build` | macOS PR 构建，我们没有 mac 改动 |

保留 active：`Minimal serving runtime`、`Portable monitor client`。
恢复任意一条：把 `disable` 换成 `enable` 即可。

> **不要改成"删文件"**：删文件就是一个下游补丁，每次 `rebase upstream/main` 都要解冲突，
> 也收不到上游以后对这些 workflow 的改进。设置层才是 fork 管 CI 的正确位置。

> ⚠️ **不要打开**仓库设置里的 `sha_pinning_required`。上游全部 workflow 用的是 `@v7` / `@v4` tag，
> 一旦强制 SHA pinning，这两条测试 workflow 会立刻全红——而我们不改上游文件。
> 这是"看起来更安全、实际把自己锁死"的选项。

完整过程与反证数据：`deploy/CI_CD_POLICY.md`（工作区文档，不进仓库）。

### 自动化在哪里（2026-11-01 建好）

| 位置 | 做什么 | 入口 |
|---|---|---|
| GitHub（no GPU） | 配置面静态门：R 表形状/取值、`getenv` 真存在、`-DNDEBUG`、hip_compat 路径、备份文件、台账锚点 | `ci/gate.py --source-only`，workflow `Downstream gate` |
| GitHub（no GPU） | 每日 09:23 CST 比较 `gfx906/mi50` 与 `upstream/main`，有差距就开（或更新）一个 `upstream-watch` issue，追平后自动关闭 | workflow `Upstream watch`（`main` 上有副本，因为 schedule 只认默认分支） |
| 166 | 同一份门 + 构建树 + 生产 config，共 18 项 | `/home/albus/strata166/ci/strata-ci check` |
| 166 | 单 TU 编译 → 部署 → 重启 → 健康门 → 台账 | `strata-ci build` / `deploy --apply` / `rollback --last` |

**上游监视故意不自动 rebase**，三条理由都是硬约束：
① 用 `GITHUB_TOKEN` 推的 commit **不会触发任何 workflow**，CI 不会跑，分支会"看着绿其实没测"；
② 我们的 rebase 改写历史，推主线必须 force-push，无人值守做这件事就是在赌主线；
③ rebase 之后必须重编 + 逐位等价，而云端 runner 没有 GPU。
所以自动化只到"发现 + 提醒"，rebase 留给 `strata-ci watch && git rebase upstream/main`。

> 部署门用工具强制，不靠记性：`strata-ci deploy` 在 `HEAD` 没有 `mi50-*` tag 时直接拒绝（已实测）。

## 跟随上游（四步）

```bash
cd /home/albus/strata166/pr/strata-fork
git fetch upstream
git log --oneline upstream/main ^HEAD          # 看上游多了什么
git rebase upstream/main                       # 薄补丁栈整体上移
# 重编 + 验证（deploy/W863_R23_DEPLOY.md 的 d11/d13/d14）
git tag -a mi50-<新版本>-r1 -m "..." && git push origin gfx906/mi50 --force-with-lease && git push origin --tags
```

## 读模式探针（R30 / W863）

`ci/probe/read_probe.cpp` 回答一个方案里长期没答案的问题：**decode 的读，到底是被带宽卡住、
被并行度卡住、还是被访存宽度卡住**。做法是同字节、单变量：

  * `mode0` 每 34 字节 Q8_0 块发 17 条 2 字节 load（生产内核今天的样子）
  * `mode1` 同样的字节用 16 字节流式 load（LDS 中转的天花板）
  * `S` 把归约维切 S 份：字节数不变，只改块数

实测（gfx906，与生产同驻留）：

| 形状 | S | mode0 | mode1 |
|---|---:|---:|---:|
| HC down 10240->320 | 1 | 553 | 613 |
| | 4 | 621 | 826 |
| | 8 | 494 | 493 |
| GDN 2560->10240 | 1 | 566 | 763 |
| HC up 320->10240 | 1 | 125 | n/a（行 340 B 非 16 倍数） |

结论：split-K 给 +12%（膝盖 S=4），宽读给 +11..35%，**但生产 HC 只有 98 GB/s 而朴素 2 字节读
就有 553** —— 读模式最多解释 1.5 倍，剩下的 5.6 倍在融合内核的其它工作里。所以 R31（宽读）
降级，靶心转 R32（量清那 5.6 倍）。

### 后来补的两个模式（R32/R33）

`gemv` 把真实内核的算术加回来（Q8 反量化 + FMA，激活在 LDS），`pad` 只把 per-lane 步长从 32 float
改成 33（消 LDS bank 冲突）。同一批字节：

| 模式 | HC down 10240->320 (S=1) | GDN 2560->10240 (S=1) | big 85 MiB (S=1) |
|---|---:|---:|---:|
| read（只读） | 581 | 631 | 666 |
| wide（16 B） | 636 | 708 | 800 |
| gemv（+反量化+FMA） | 255 | 98 | 264 |
| pad（+33 步长） | 348 | 173 | 353 |

结论：**贵的是每字节约 2 条 ALU（32 cvt + 32 FMA / 32 字节），不是读**；宽读只在纯读时有用。
LDS 填充再回 36..76%。生产 HC 的 98 GB/s 与探针 gemv 的 98 吻合。

同一个探针也量到占用率（从生产汇编取 VGPR）：down T=2 用 119 VGPR = 25% 占用率，
T=3 涨到 140 越过后 128 的线 = 12.5%，**腰斩**；`_fast_` 变体只在 T=3 有用，T=2 无收益且 up 更差
（50% vs 62.5%），所以 `STRATA_TSUM=1` 不该开。

两个测量陷阱，写在文件头注释里，因为都真的踩过：
  1. 每遍重读同一批行 ⇒ 命中 L2 ⇒ 报出 1.5 TB/s（高于 HBM 屋顶）。改成每遍读**独立副本**。
  2. `if (result == 不可能值) store` 这种保活写法会被优化掉，**连带读一起消失**。改成每块
     都写一个数据相关的结果。

## 两笔已知欠账（AUDIT19）

| # | 欠什么 | 影响 | 什么时候清 |
|---|---|---|---|
| **A11** | 镜像 `/src/serve/telemetry.py` 仍是旧版（缺 `self._thread` 的 CI 修复，提交 `c3574d42`） | 仅显示层的线程引用，**不影响推理** | 下次重建镜像（`0.2.9-102`）时随镜像带上；用 `docker exec strata166-407 md5sum /src/serve/telemetry.py` 与主线比对 |
| **A12** | `deploy/params/gen_config.py` 的 `META` 停在旧部署，跑 `--write` 会写坏生产 config | 改 config 只能手工定点改 + 双备份 | 修 `META` 之前不要用它生成 |

**为什么记在这里而不是只记在工作区文档**：这两条都是「clone 下来会踩到」的东西，
跟着代码走才有人看得到。

## 屋顶探针（R29 / AUDIT19）

`ci/probe/stream_roof.cpp` 测这张卡的**可达读屋顶**，是所有「带宽利用率」的分母。

实测（2026-11-01，gfx906，与生产同驻留）：**读 884 GB/s（86.3% 规格，1024）**、拷贝 752 GB/s；
并行度曲线：1 block/CU 55% → **4 blocks/CU 86%（峰）** → 8 blocks/CU 82%。

```bash
bash ci/probe/stream_roof_run.sh      # 容器内编译+运行，~40 s，只用 <=256 MiB 显存
```

换卡或换 ROCm 大版本后重跑一次即可刷新分母；不要再用「约 700」这种没有出处的数。

## 已知限制

~~浅克隆~~ **已于 2026-11-01 16:0x 修复**：`git fetch --unshallow upstream` ⇒ `git rev-parse --is-shallow-repository` = `false`，
4933 个提交可达，`.git` 137 MB。历史类判断（落后/领先、merge-base）现在可信。

> 修复前的教训：浅克隆上 `rev-list --count` 把「落后 3528 个提交」算成「落后 1 个」，
> `merge-base` 直接报错，在 main 上 rebase 会把老提交当根整树重放。历史不全时一律用 GitHub API 交叉验证。
