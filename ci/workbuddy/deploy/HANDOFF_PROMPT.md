# 交接提示词（复制下面 fenced 块到新会话）

> 用法：新开会话，把 ```text 里那一整段粘进去。它自包含：项目、现场、约束、结论、下一步、坑。
> 深材料在 `D:\workbuddy_space\strata_ws\deploy\SESSION_STATE.md`（一页纸）与各 `W8xx`/`AUDIT13` 文档。

```text
你接手的是 Strata 引擎在 AMD MI50（gfx906）上的调优项目。工作区 D:\workbuddy_space\strata_ws，
远程 166（192.168.50.166，用户 albus）。先读 deploy/SESSION_STATE.md 再动手，它是现状的一页纸。

【第一件事】报生产量化现状（不要只看定性）：镜像、引擎二进制、args 条数、env 条数、显存占用、
专家缓存槽位、提示路径借用、预热带宽、/health。取数用 bash ~/strata166/tmp/state_q.py（在 166 宿主上跑），
门禁用 bash ~/strata166/tmp/verify_patches.sh（17 项，必须 PASS）。

【当前现场】容器 strata166-407 / 镜像 strata-gfx906:0.2.8p2 / 引擎 /data/bin/strata-0.1.54n3 /
33 args / 6 个 env（含 STRATA_GFX906_TUNED=1）/ 显存 33.5 中的 34.3 GB（约 97.6%）/ 7463 槽 21.79 GiB /
借用 1578 槽 4.62 GiB / decode 约 51 tok/s / health ok。回滚件：配置 .bak-w839 + 旧二进制 n2 + 旧镜像 0.2.8p1。

【硬约束，不可违反】
1. 源码只在分支改：166:~/strata166/gfx906，分支 gfx906/0.2.8-mi50（head 9ac564f，ahead 10 / behind 0）。
   改完跑 bash ~/strata166/tmp/sync_gfx906.sh 同步进构建树 src028（9 个文件按 md5 + 1 个锚点补丁器）。
2. 绝不向上游 Niko1221/Strata 推送、不开 PR。上游 remote 的 push URL 已被置为 DISABLED；写入只到 phoenixclyde/Strata。
3. 部署物必须当场核 md5（build 产物 vs /data/bin），并跑门禁；树里有 ≠ 二进制里有。
4. 每次停服实验脚本必须内置"无论成败恢复生产"；一次载入约 240 s，成本要算进去。
5. 本机 bash shim 会吞变量/引号/反引号：脚本一律写成 .sh/.py 文件再跑，路径用字面量。
   验证运行时 env 不能用 /proc/<pid>/environ（它是 exec 快照，setenv 不回写），只认启动横幅/行为。

【已确认的结论，不要重新推导】
- gfx906 的架构默认表原本是死代码：apply_arch_defaults 的调用点在 #if defined(STRATA_USE_HIP) 内，
  而 gfx906 构建只定义 STRATA_HIP_GFX906。补了专属调用（commit 1309b1d）后才生效，
  判据是启动日志两行 "strata: gfx906 (MI50-class): ..."。
- generate.cpp 里还有 28 个 STRATA_USE_HIP 块对 gfx906 不生效（38 个里 10 个已兼容）；
  不能批量打开（W717/P23 实测全局开有副作用），只能逐块加 || defined(STRATA_HIP_GFX906) 并单独 A/B。
- 参数轴不是"最优"：--spec-min-p / --pcie-frac / --pool-workers 全部 UNRESOLVED（效应小于噪声底盘），
  只有 --adapt-* 判"默认正确"。不要再写"已调到最优"。
- 数值债只结清一半：GDN_HEAD 位等价（EG.tsv 与 E0.tsv 的 md5 同为 fadf1889…），GDN_PP 从未单测（P229）。
  「0.029」只代表 5 项 / 45 个位置 / 不含 MMQ_KQ。
- 移植收益模型已修正：可达面 24.19 ms（53.8%），30–50% 局部改善 ⇒ −16%~−27%（旧文档写 33 ms/73%、−5~−10%，已改）。
- 测量纪律：同配置复本之间就有 3.9–10.8% 离散（中位 6%），且生成路径本身不可复现
  （36 条同 prompt 同 seed 贪心 → 36 个不同 sha）。任何 <5% 的结论都要 n≥20 或用与内容无关的量（ms/win、teacher-forced）。

【下一步，按价值排】1) 单块放开 STRATA_PCIE_FRAC_DEFAULT=auto / pcie_frac_auto（P227 候选，唯一可能改 decode 的死块）；
2) GDN_PP 单臂 KL（P229，约 6 min）；3) decode_defaults_arch_ok() 这块；4) 把"分支→同步→增量编译→部署→门禁"串成一条命令。

【文档地图】deploy/SESSION_STATE.md（先读）；deploy/W839_ARCH_ENTRY.md（本轮）；deploy/AUDIT13_W832_W839.md（最新审计，
P0 3 / P1 8 / 撤回 3）；deploy/AUDIT_INDEX.md（审计链 AUDIT6→13）；deploy/params/PARAM_REGISTER.tsv（226 行，P001–P229，
改参与判决的唯一账本）；deploy/patches/LOCAL_PATCHES.tsv（9 条补丁 + commit）；deploy/W836_BRANCH.md；
deploy/W835_GFX906_PORT_FEASIBILITY.md；deploy/W832_OPT_PLAN_V2.md（W832–W834 执行记录）。

【沟通习惯】结论先行、数字要能说清是实测/源码核实/推测；不要展示文件（不调用 present_files）；
产物写进 albus/<轮次>/ 子目录；能自主判断就连续做完，别每步问。
```

---

## 落盘清单（本轮真正写进磁盘的东西）

| 文件 | 变化 |
|---|---|
| `deploy/AUDIT13_W832_W839.md` | **新建**（审计报告） |
| `deploy/SESSION_STATE.md` | **新建**（一页纸现状） |
| `deploy/HANDOFF_PROMPT.md` | **新建**（本文件） |
| `deploy/AUDIT_INDEX.md` | 增 AUDIT13 行、合计改 9/51/58/3、未结清清单重写 |
| `deploy/AUDIT_LEDGER.tsv` | +16 行（AUDIT13），共 42 行 |
| `deploy/params/PARAM_REGISTER.tsv` | 226 行；8 条改状态、2 条新增（P228/P229）、清掉第 220 行空行 |
| `deploy/W832_OPT_PLAN_V2.md` | 7 处就地修复 |
| `deploy/W835_GFX906_PORT_FEASIBILITY.md` | 3 处（33ms/73% → 24.19/53.8%、−5~−10% → −16~−27%、3.9× → 4.40×） |
| `deploy/W836_BRANCH.md` | 6 处（时点标注、find_dependency 语义、banner 来源、门禁项数） |
| `deploy/W839_ARCH_ENTRY.md` | 4 处（第 9 个 commit、门禁 17 项、预热 12820 vs 12739） |
| `.workbuddy/memory/2026-10-31.md` | 追加 W839 与 AUDIT13 两段 |
