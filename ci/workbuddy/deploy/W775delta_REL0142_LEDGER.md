# W775delta -- v0.1.42 release note 逐条台账（全量 60+ 条，非分类）

**生成**：2026-10-11 04:2x ｜ **判据源**：`deploy/tmp/_rel0142.md`（release note 原文 23,126 字符，UPSTREAM）
**口径**：判定分四档 -- **命中** / **○通用** / **x不适用** / **▲改答案（触项目一票否决，封口）**
**条目数（上游原结构，据实）**：`##` **7 节**；`-` **bullet 共 40 条**（Faster 3 · Fixes 17 · New opt-ins 11 · **Setup and server 0**（一整段散文）· Answers can differ 6 · Not fixed 3 · Updating 0）。
本台账另外收录**若干非 bullet 结构**：Faster 节的一张**总表 F-T**、`Setup and server` 散文拆出的 18 个子句、`Updating` 的 U-1、致谢段。**故本表行数 = 64，但那不是上游条目数** -- 上一轮把 64 当条目数是**口径错误**，已更正。

> 说明 1：上表把 `## Setup and server` 那**一整段无 bullet 的散文**按 `Setup:` / `Server:` / `Web app and Monitor:` / `Engine start:` / `On Windows` 五个锚拆成 18 条 -- 这是前一轮「6 组」归类漏掉的主体。
> 说明 2：**release 页面原文第 83 行末被 GitHub 截断**（`... among them a Radeon Pro VII (gfx906), 2x T... [truncated]`）。现取 API body = 23,126 B / md5 `48de549e4d37d15e7553b09346bbd023`，与本地存档**逐字节一致** => **是上游原文如此，非我方存档残缺**。后半段（社区报告清单）改从 0.1.42 镜像 `bench/results/` 实读补齐（见 S-18）。
> 说明 3：**上游原文两处数字不一致** -- `Setup and server` 段写 *"Twenty-one community benchmark folders"*，而致谢段写 *"whose thirteen folders are in this release"*。**据实并列，不擅自裁一个**。

## Faster

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| F-1 | STRATA_ROUTE_TAIL_SKIP=7（CUDA 默认开，PR #1668） | x 不适用 / ▲ 改答案 | 上游逐字 off on AMD and Intel；且 off when every expert is in VRAM。本机 9761 槽驻留绝大多数专家，两条都排除。它改答案（KL 0.0032-0.0058 / top-1 97.7-98.2%） | 封口，登记 P57。**【W775delta 更正 2026-10-11 12:1x】** **本条判错**：实测本机 ON(default) 且在动作（生产日志 12/12；skipped N 达 672,855）=> 不属封口；转 W16 + W17。见 `W775delta_RTS_TAILSKIP_FINDING.md` |
| F-2 | PCIe share 改为按 CPU 实测自适应（CUDA 单卡，无 --pcie-frac） | x 不适用 / ▲ 改答案 | 上游逐字 off on a layer split, with --batch, a peer GPU, every expert in VRAM, and on AMD and Intel。本机是 AMD，且已显式 --pcie-frac 0.20（该 flag 永远优先） | 封口 P57；注：我们 P25 的 0.20 是 calibrate 实测解，不受影响 |
| F-3 | gfx12 prompt switches 默认开（GDN_HEAD/GDN_PP=2/GDN_CONVL2/GDN_NOY/CVEC_FUSE，#1478） | x 不适用 | 上游逐字 on for gfx1200/gfx1201 cards。本机 gfx906 | 封口 P57 |
| F-T | **「Final build against 0.1.41」总表**（不属任何单条 bullet；8 机型 x 3 列 story/code/4K） | * 命中（**全篇唯一负值**） | 关键行：`Tesla P100, IQ3_XXS (start-up PCIe probe, default flags) \| -3.6% \| -2.1% \| 0.0%` -- **这是全篇唯一"默认配置下 decode 变慢"的地方**；下一段点名归因：*"The P100 and A750 default-flag swings come from the start-up PCIe probe (see Answers can differ); with the share fixed they are inside noise."* | **印证 P25 的处置**：显式 `--pcie-frac 0.20` 给死值 => 绕开 probe 抖动。该表里 R9700/RX/Arc 多行为 ±0.0x%~±0.1% => 说明非 CUDA 平台上 0.1.42 基本平坦 |
| F-4 | 标题卖点：13-16% faster decode（NVIDIA 单卡或层切分） | x 不适用（据实） | 构成该卖点的三条（F-1/F-2/F-3）上游逐字全部排除 AMD => 对本机不兑现。这是「没有收益」不是「有损失」 | 已写入 W750 §0.5；升级理由仍成立（净修复+零回归） |
## Fixes

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| X-1 | 卡序保留（#1576/#1590/#1760） | x 不适用 | 多卡自动层切分的卡序重排问题；本机单卡 | 封口 |
| X-2 | 自动切分不再产生 1-2 层 stage（#1616） | x 不适用 | 上游逐字「we have no rig of that shape」；本机单卡无层切分 | 封口 |
| X-3 | Windows AMD（HIP）：--prefill auto 停在 6144 tok（#1630）+ commit 守卫 + 对话缓存取 min(free RAM, free commit)（#1607）+ 16GB 卡保留 2560 MiB（#1709） | x 不适用（我们 Linux） | 上游逐字「We have no Windows AMD box: these are guards that compile and pass their tests, not seen on a card」。但**#1607 的 min(free RAM, free commit) 语义与 #1601 同族** => 见 W14 | 封口；#1607 归入 W14 连带口径 |
| X-4 | AMD 2+ GPU：104K-token prompt 的默认 checkpoint save 不再失败 | x 不适用 | 本机单卡 | 封口 |
| X-5 | CPU prompt share on RTX 5090（用户报告）-> 0.1.42 跳过条件（free RAM < buffers+3GiB / Windows commit / experts 是 RAM 装不下的文件页）+ #1595（every expert in VRAM 不武装） | * 命中（机制同源） | 这正是 #1729 的修复面，也是我们 P23 的同族。**对我们的直接含义**：gfx906 已在编译期被 #1732 排除（见 X-16），故这层守卫对本机是**第三重保险** | 已由 W15 核（banner 零打印） |
| X-6 | 上下文末端（#1700, midagedev）：4094-token prompt + --max-context 4096 --max-new 2 --spec 4 报 ran out of context | ○ 通用 | 通用边界修复，对本机无害（我们 max-context 262144，不触发该边界） | 无需动作 |
| X-7 | Intel：无 --mtp 退出崩溃（#1642）/ 镜像专家答 !!!!（#1721）/ 层切分 verifier 队列（#1555/#1589，#1440）/ --batch-mtp draft-vocab head（#1121/#1790） | x 不适用 | Intel SYCL 专属 | 封口 |
| X-8 | Pascal/Volta 小显存 prompt（#1757）：BF16 产物走 FP32 转换缓冲；装不下则分 tile 转换 | x 不适用（本机非 Pascal/Volta 且显存够） | MI50 是 Vega20/gfx906，非 Pascal/Volta 的 cuBLAS 路径 | 封口 |
| X-9 | Windows 层切分卡住（#1740/#1741）：pipelined decode 每 poll 切 CUDA device | x 不适用 | Windows + 多卡 + CUDA | 封口 |
| X-10 | cuBLAS FP16 fallback（#1650/#1659） | x 不适用 | 需 Turing+Pascal 混合或 cuBLAS 12.4；本机 HIP 构建 | 封口 |
| X-11 | 取消的请求保留其恢复的会话（#1620）：追问复用 1834/1851 而非 1523 | ○ 通用 / 可能有益 | 与 P31（--conversation-cache-mib）同族：恢复的会话复用率提高 => 对我们多轮追问场景**方向有利**。本机 P31 已验证机制（追问 TTFT -88~90%） | 观察项：下次追问实测可顺带记 cache_n |
| X-12 | STRATA_STAGE_PIN=1 曾腐蚀答案（#1237）：页锁定缓冲在拷贝完成前被复用；已修，仍 opt-in | * 命中（已知缺陷已修） | 该 opt-in 本机可及（我们未用）。修复值得记：说明「page-locked buffer 复用」这类缺陷在本项目的 opt-in 面存在过 | 登记为「已知缺陷已修」；不启用 |
| X-13 | 并行请求（#1603）：请求可能既不运行也不排队、永久等待；slot 记账改为跟踪 owner + 回收孤儿 | ○ 通用 | 上游逐字「We did not reproduce the exact hang」。本机单用户单并发，暴露面小 | 无需动作 |
| X-14 | Thinking budget（#984）：预算 >= max_tokens 余量时永不触发，回复中途截断 | ○ 通用 / ▲ 改答案（仅在有预算时） | 仅在使用 thinking budget 时改变行为；本机 config 无该设置 | 无需动作（我们不用 budget） |
| X-15 | 内存守卫 in containers（#1601, noon-at-cgn） | * 命中（本机是容器部署） | parking 与 session SAVE 读 min(MemAvailable, cgroup room, --memory-limit-mib − use)。上游逐字「not with docker」=> 须自证 | **W14 已核：在位但不触发**（memory.max=max => 受 MemAvailable 约束；无拒绝行/重试行；76 GiB 预算未变） |
| X-16 | #1732：gfx906 构建不再武装 CUDA-only CPU prompt share | * 直接命中 = 我方 PR | relnotes 逐字 the gfx906 build no longer arms the CUDA-only CPU prompt share (#1732)。机制 = prefill.cpp:1868 补第二合取项 && !defined(STRATA_HIP_GFX906)，整块编译期不存在 | **W15 已核：生效**（banner 零打印 / environ 仍 =0） |
| X-17 | 无 AVX2 的 CPU（#1701/#1697/#1699）：Q2_0 与 i-quant 行的 128-bit AVX 内核 | x 不适用（本机 CPU 有 AVX2） | 本机 Xeon E5-2696 v4（AVX2，无 AVX-512）。上游逐字「No real CPU of that age was tested」 | 无需动作 |
| X-18 | Smaller：keep-alive/503（#1619/#1527）/ 错误前缀（#1615）/ 层切分 --batch（无 slot 时空转）/ GCC 10（#1488）/ 无张量首分片（#1611）/ **gfx906 不再武装 CUDA-only CPU share（#1732）**/ CUDA MMQ 错误报告 + HIP 替身目标链接（#1812） | ○ 通用 + * 其中 #1732/#1812 命中 | 「Smaller」是打包段：其中 #1732 是重复提及（见 X-16）；**#1812（HIP stand-in targets link cleanly）对我们有价值** -- 本机是 HIP 构建 | 封口；#1812 记为 HIP 构建健康度改善 |
## New opt-ins

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| O-1 | gfx12 融合 int8 prompt 专家（STRATA_PF_FUSED=1，#1570） | x 不适用 | 上游逐字 gfx1200/1201；且 Q2_0 不用这些内核；IQ3_XXS 因 KL 不达标保持 opt-in | 封口 P57 |
| O-2 | 层切分 3+ stage 的 --pipeline-windows 2（#1656） | x 不适用 | 多卡（4x R9700 实测）；本机单卡 | 封口 |
| O-3 | --batch-mtp on layer split（#1636） | x 不适用 | 多卡 + 上游实测在专家全驻显存时反降 21.9% | 封口 |
| O-4 | 数据并行 replicas（replicas: 2 / --replicas N） | x 不适用 | 多卡；上游逐字 Costs two copies of the model in RAM；core pinning 仅 Linux | 封口 |
| O-5 | 多卡附加项（--aux-cpus / STRATA_SPLIT_MTP_BATCH / STRATA_SPLIT_RING，#1600） | x 不适用 | 多卡；SPLIT_RING 的价值在 104K prompt 的文件读取（98.3->34.5 GB） | 封口 |
| O-6 | 更多路由开关（改答案）：STRATA_ROUTE_PRIOR=0.5 / STRATA_ROUTE_RESIDENT=0.5 / _MTP=1 | x 不适用 / ▲ 改答案 | 上游逐字 change answers（ROUTE_PRIOR KL 0.017 mean）；ROUTE_RESIDENT 场景是 22 GiB RAM 预算（与我们 76 GiB 不同） | 封口 P57（触项目一票否决） |
| O-7 | Intel A 系 prompt（STRATA_PF_XMX=1/2，#1711）+ 三个 opt-in（VERIFY_STEPPED / SYCL_A770_FAST / DOORBELL_CHECK） | x 不适用 | Intel Arc 专属；上游逐字「We have no A770, so its claims are unverified」 | 封口 |
| O-8 | Sessions：--session-save-reclaim（#1573）/ --conversation-cache-min-tokens N（#1597） | ○ 可用未测（* 与 P31/P33 同族） | --session-save-reclaim：SAVE 失败时释放保留 K/V、旧 parked 会话、非 pinned checkpoint 后重试（420 MiB 空闲下测过）；min-tokens：只 park >= N 的会话。**本机 /metrics 实读 min_tokens=0（吃默认，不筛）** | 观察项；与 W14/RAM 守卫同族 => 若将来 park 失败，这两个是解法 |
| O-9 | 其它 opt-in：STRATA_STAGE_PIN=1（now exact）/ STRATA_MMQ_RESIDENT_SORT_NE（#1660）/ helper-cache prefill（#1649）/ pipelined commit guard（#1674） | ○ 部分可用未测 | 上游逐字 output identical at 4K and 20K, speed claims are the authors'。**MMQ_RESIDENT_SORT_NE 与我们 gfx906 的 MMQ 路径相关**（本机是 HIP MMQ） | 观察项（低优先） |
| O-10 | * gfx906：STRATA_GFX906_ATTN_QUERY_SWIZZLE=1（#1661）/ STRATA_GFX906_ATTN_REDUCE12=1（#1718，依赖前者）；构建拒绝 wave32 卡（#1728） | * 命中 = 我们的 P55 / P56 | 上游逐字「gfx906 (no MI50 here, so speed is the author's claim)」。W775_VERSION_SYNC §3.1 镜像内穷举证实两宏在 0.1.42 各命中 8/5 文件（0.1.41 = 0） | **W12**（CANDIDATE）：W774 首测 prefill 中性、decode 弃权 => 需 5+ runs |
| O-11 | * STRATA_HEAD_MIX_MULTI=1 + STRATA_ONE_TOKEN_COMMIT=1（#1479） | * 命中 = 我们的 P59 / P60 | = 我们 #1479 的发现被上游采纳为代码（署名 co-author，维护者逐字 Added as HIP opt-ins (your patch, you are credited as co-author)）。上游实测 answers identical / decode 不可区分 | **W12**（CANDIDATE）：与 P55/P56 同车；P59/P60 是同一 patch 两半 => 必须同臂 |
| O-12 | 配置键与 API：prevent_sleep / reasoning_effort / /metrics/prometheus / logit_bias（HIP 采样也支持，-100 硬禁） | ○ 可用未测 | prevent_sleep 是 Windows；reasoning_effort 是默认思考档；/metrics/prometheus 需 API key；**logit_bias 在 HIP 采样生效且只对发送该字段的请求生效** => 与 P29（无采样用法）不冲突 | 观察项；logit_bias 若将来需要可即用 |
| O-13 | 工具（仅测量）：STRATA_LOOKAHEAD_STATS=1 + tools/replay_cache_policy.py | * 命中（对我们价值最高的一条） | 上游逐字 record and replay the expert-cache policy offline; they do not change decoding。**它把专家缓存策略变成可离线复放的对象** => 直接对口我们 W769「驻留伪影不可分离」的困局 | **W13**（零发车，待做） |
## Setup and server

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| S-1 | Setup：损坏的 llama.cpp 源码包会重新下载（#1797/#1801） | ○ 通用（setup 面） | 本机已 setup 完成；仅在重装/升级时相关 | 无需动作 |
| S-2 | SYCL setup 从源码读引擎版本（#1794/#1817） | x 不适用 | SYCL/Intel | 封口 |
| S-3 | 无 CUDA 的机器重新找到 Visual Studio（#881/#1792） | x 不适用 | Windows + CUDA 探测 | 封口 |
| S-4 | 层切分下 quant RAM 预算保留（#1564） | x 不适用 | 多卡层切分 | 封口 |
| S-5 | 引擎更新只为你模型用到的卡编译（#1485） | ○ 通用（升级面） | **与我们升级路径相关**：升级编译的卡选择。本机是 gfx906（我们自己在容器内构建） | 无需动作 |
| S-6 | --gpus 在 AMD-only PC 上能命名 AMD 卡（#1594） | * 命中（我们就是 AMD-only） | 上游逐字。本机单 MI50，未用 --gpus（走全部可见设备） | 登记为可用；我们不设 --gpus（P/B02 已判缺省同效） |
| S-7 | 损坏的 cmake/ninja 被跳过（#1605）；CC/CXX 到达 CMake（#1645） | ○ 通用（构建面） | 本机构建走容器内 cmake -G Ninja；CC/CXX 传递对我们自建镜像有价值 | 无需动作 |
| S-8 | swift 家族接受 IQ3_S（#1651） | x 不适用 | 模型族不同（我们是 Qwen3.8-Flash-Next / UD-IQ4_XS） | 封口 |
| S-9 | 统一内存 APU 上 setup 写专家缓存数字而非 auto（#1715） | x 不适用 | 上游逐字 conservative, no Strix Halo box here；本机非 APU | 封口 |
| S-10 | Server：重排后的工具集保持首次出现顺序（prompt cache 存活，#1624） | ○ 通用 / 可能有益 | 与我们 P31/P34（prompt cache / conversation cache）同族：工具集顺序变化会破坏 prompt cache | 观察项 |
| S-11 | Server：类型错误的采样字段是 400 并指明字段；数字字符串被转换（#1663）；未读的 content part 被丢弃而非 400（#1664） | ○ 通用 | 上游行为改进（对我们这类直连 API 的自用场景降低踩坑） | 无需动作 |
| S-12 | Server：接受 llama.cpp 的 repeat_penalty / repeat_last_n（#1819） | ○ 通用（本机贪心，不用） | 本机 config 无 sampling 段（P29），不显式传 temperature => 贪心 | 无需动作 |
| S-13 | Server：effort_position end 在 Intel 引擎启动脚本后找到选项（#1781/#1782） | x 不适用 | Intel | 封口 |
| S-14 | Server：reasoning_loop_recovery 开启时，写成单个长词的循环（如循环数字串）能被捕获（#1753/#1777） | ○ 通用 | 仅在该 recovery 开启时相关；本机未开 | 无需动作 |
| S-15 | Web app 与 Monitor：favicon + AMD 卡在 Linux 的 PCIe tile（#1733）+ sparkline 不再按自身噪声缩放（#1731） | * 两条命中 = 我方 PR | = 我方 #1733 / #1731 已合入 0.1.42（维护者逐字致谢）。**实测生效**：/metrics gpu_pcie_gen=3 / width=16 / path=4/4 | 封口（已落地，W775 已核） |
| S-16 | Engine start：PLE 探针（<0.6s）在 <15,000 rows/s 时把 --ple-io direct 切成 mmap；STRATA_PLE_PROBE 关掉它（#1425/#1549/#1629） | * 命中（升级引入的行为变化）--**[更正 2026-10-14] 原判「已核不可达」作废：实为已动作** | 生产日志实读：`PLE on, table 320001536 rows` 38 次、`--ple-io direct measures slow here (14560 / 13268 rows/s): using --ple-io mmap instead` 2 次（serve 启动行 L2714 之后）。即 PLE 表已加载、探针已执行、`--ple-io` 已被自动切成 mmap。原「无 PLE rows/s 行」系过窄 grep 造成。仍成立：它是抑制开关；慢盘自动切 mmap 仅在未显式给 --ple-io 时发生 | **[撤回] 待办重开**：`--ple-io direct` 对照车（0.1.42 内置） |
| S-17 | Windows：resident RAM 模式用非缓冲读构建 RAM 副本（#1696） | x 不适用 | Windows；本机 Linux 容器 | 封口 |
| S-18 | bench/results 收了 21 份社区报告（含 Radeon Pro VII (gfx906)、2x Tesla P40 131K、RX 9060 XT、RX 9070、RTX 5060 Ti；docs 里还有 Arc A770 decode 调查 #1765） | * 命中（gfx906 报告 = 我们的参照面） | W775_VERSION_SYNC §3.3 已实读 7 份 AMD/gfx906 目录。**最重要两份**：(1) 2026-10-08-gfx906-qsa-query-swizzle（2x Radeon Pro VII，直接实测我们的 P55：组件 +14.65%、整模型 prompt +1.185%、输出逐位相同）；(2) 2026-10-09-community-radeon-pro-vii-16gb（有 0.1.40.4->0.1.41 的 gfx906 needle+speed 对照） | W713 §6.4 #11（吸收上游 gfx906 报告）；#9（P55/P56 复测参照） |
## Answers can differ

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| A-1 | STRATA_ROUTE_TAIL_SKIP=7 在 CUDA 默认开（KL 表：3060 mean 0.0058 / A4000 0.0032；noise floor 0.0007）；=0 + PREFILL_CPU_SHARE=0 才等于 0.1.41 精确答案 | x 不适用（AMD 不生效） | 上游逐字 off on AMD and Intel。**但这条给了我们一个通用锚**：0.1.42 的「精确 0.1.41 答案」条件是 ROUTE_TAIL_SKIP=0 + PREFILL_CPU_SHARE=0 => 我们已显式 =0，且 gfx906 已被 #1732 排除 | 封口；「精确答案条件」记为口径。**【W775delta 更正 2026-10-11 12:1x】** **本条前提判错**：`ROUTE_TAIL_SKIP` 在本机默认开且在动作 => 该「精确旧答案」条件**我们只满足一半**（`PREFILL_CPU_SHARE=0` OK）。见 `W775delta_RTS_TAILSKIP_FINDING.md` |
| A-2 | 实测 PCIe share（CUDA 单卡，无 --pcie-frac）：移动 share 时 CPU 计算的专家变化；STRATA_PCIE_FRAC_DEFAULT=old 或 --pcie-frac N 保持旧行为 | x 不适用 / ▲ | AMD 不生效；我们已显式 --pcie-frac 0.20 | 封口 |
| A-3 | CPU prompt share（0.1.41 的变更）在 RAM/commit 不足的机器上被跳过；那里的答案等于 PREFILL_CPU_SHARE=0 | * 命中（与 X-5/X-15/X-16 同族） | 上游逐字。**对本机：gfx906 已在编译期排除，且我们显式 =0** => 三重保险 | 已由 W15 核 |
| A-4 | Thinking budget 高于 max_tokens 减其保留值时提前关闭思考（#984） | ○ 通用 / ▲ 仅在有预算时 | 本机未用 budget | 无需动作 |
| A-5 | 重排回来的工具集保持首见顺序（#1624）：带工具集的首个请求逐字节等于客户端所发 | ○ 通用 | 与本机自用直连 API 场景相关（降低 prompt cache 破坏） | 无需动作 |
| A-6 | 标记 changes answers 的 opt-in（route prior / route-resident / fused prompt experts / XMX / split MTP batch）仅在你打开时改答案 | x 不适用（我们全不打开） | 上游逐字（... only when you turn them on） | 封口（P57 已登记） |
## Not fixed

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| N-1 | Arc A750：--batch 报 out-of-host-memory（0.1.41 也有） | x 不适用 | Intel Arc | 封口 |
| N-2 | Arc Pro B70 + STRATA_VERIFY_NO_HOST=0 + 自适应 swap：约 31->58 tok/s 但遇一次 GPU hang => 不推荐 | x 不适用 | Intel Arc | 封口 |
| N-3 | Windows AMD + KV streaming（65536 上下文）：draft 层 prompt pass 报 unspecified launch failure（#1644）；上游无法测 Windows AMD | x 不适用（我们 Linux） | 但**机制面值得注意**：draft 层 prompt pass 在 KV streaming 下的失败 => 我们不用 KV streaming（--kv-grow 已 REJECTED / kv_resident=0） | 封口；注：与本机 P32（--kv-grow REJECTED）方向一致，不启用是安全的 |
| N-4 | Open，求日志：#1723（park 超大会话时 Windows 崩溃）/ #1682 / #1683 / #1686 / #1703 / #1648 | ○ 观察（未解决） | **#1723 与我们相关**：park 超大会话 => 与 P31/P33/会话缓存同族。我们 `--conversation-cache-mib 4096` + snapshot 305-677 MB/会话（W713 B3）=> 需留意超大会话 park | 观察项：登记为上游 open 缺陷（与本机 P31 面相邻） |
## Updating

| 编号 | 条目 | 判定 | 依据（逐字/实测） | 行动项 |
|---|---|---|---|---|
| U-1 | UPDATE.bat / ./update.sh；模型与配置不动。NVIDIA 上要精确旧答案：env 段放 STRATA_ROUTE_TAIL_SKIP=0 + STRATA_PCIE_FRAC_DEFAULT=old + STRATA_PREFILL_CPU_SHARE=0 | ○ 通用（升级口径） | **对本机**：三条里我们已显式 STRATA_PREFILL_CPU_SHARE=0；另两条 AMD 不生效 => **我们天然满足「精确旧答案」条件**。这也解释了为何 W774 实测 prompt 侧与 0.1.41 无差异 | 已写入 W750 §0.5/A-1。**【W775delta 更正 2026-10-11 12:1x】** **更正**：三条里「另两条 AMD 不生效」对 `ROUTE_TAIL_SKIP` 不成立（本机默认开且在动作）=> **我们并非天然满足「精确旧答案」**。见 `W775delta_RTS_TAILSKIP_FINDING.md` |

## 汇总计数

| 档 | 条数 |
|---|---|
| *命中 | 12 |
| ○通用 | 19 |
| x不适用 | 33 |
| **合计** | **64** |

**命中 逐条**（这是我们真正要处理的）：X-5 · X-12 · X-15 · X-16 · O-8(部分) · O-10 · O-11 · O-13 · S-6 · S-15 · S-16 · S-18 · A-3


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `ca7467977e71f7fe71458392cac7c776`（字节 22136）。
