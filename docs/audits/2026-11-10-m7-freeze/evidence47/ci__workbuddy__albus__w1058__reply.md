# W1058 回执：R91 P0–P4 全过门（P1 逐位 / P3 等价+ISA 5184→0 / P4 均值口径）——dot8 收益定位在布局侧，P2 待占比侦察

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）· restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件（本轮全部工作在 scratch 容器 / 单 TU 编译，生产二进制零触碰） |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（未动）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--pcie-frac 0.20` `--spec 4` `--kv k8v4` `--prefill auto:16384` `--kv-grow` 等，与 W1057 同表） |
| 3b | env 明细 | 13 项逐名未动（含 `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_GFX906_ATTN_LDS_PAD=1`，与 W1057 同表） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T09:39:51Z`（W1057 末次 trap 还原的冷启动，本轮未动过容器） |
| 5 | 资源隔离 | `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 884 MiB（生产态）；expert cache 8301 槽 / 24,807 MiB；borrows：metrics 未暴露该键（W1055 读数 2609 槽 / 7.62 GiB；本轮生产未动） |
| 7 | 回滚件 | 生产未动 ⇒ 无需回滚；本轮唯一被改过的共享文件是构建树头 `vecdotq.cuh`（llama-master 副本 + overlay 副本），**双份已还原 md5 `9e0da3cb` 复测一致**（`albus/w1058/isa_ab.log`） |
| 8 | 本轮改动 | 换件 0 / config 改 0 / 装机 0 / 回滚 0 / **重启 0 次 / 停机 0 s**；disk=build=running 三方未动 |
| 9 | ROCm（容器内） | `.info/version` **10.1.0** · HIP runtime **7.16.26323-0000000** · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | **b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`** + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc`（镜像未换 ⇒ pin 未变） |

**二、主线** — `gfx906/mi50` @ e181bda5（tag `mi50-0.2.11-r33-14`）本轮未动，上游未重算，**领先 0 / 落后 0**，脏 0 行；生产树 `pr/k10` 头 **`bd47cf05d`**（W1056 提交）→ 本轮新增 W1058 provenance 提交（见 §5）。新证据件：`albus/w1058/`（`r91_p1p3.cu` P1+P3+微基准一体件、`run_p1p3.sh`/`run.log`、`p3_vecdot_patch.py`、`isa_ab.sh`/`isa_ab.log`、`pp_test.sh`）。

**三、本次落生产** — 换件 0 / 装机 0 / **重启 0 次 / 停机 0 s** / 回滚 0。R91 的 P1/P3 全部在 scratch 语境完成（一次性容器编译 + 单 TU ISA 断言），P4 用 R74 窗口实测数据组合判定（无需新窗口）。

**四、进度** — **537 条 / 已结 450 / 83.8%**（+5 条 `P585`–`P589`；`R91` 保持 OPEN——P2/P5 待裁决）。队列（代码+前置优先）：**R91（P0–P4 已结；P2/P5 待 x_qs 流量占比侦察）→ R101 → R85/R46 > R64 > R60 → R89 → R95 → R86 →（治理）R80 → R79 → R81**（`W832 §0.1`）。

---

## 1. R91 P0–P4 四道门全过（`P585`–`P588`）

| 门 | 判据 | 结果 | 判 |
|---|---|---|---|
| P1 量化器 | 与 CPU 参考逐元素一致 | BlockA4（`albus/w1058/r91_p1p3.cu:41`）4096 块含 tie/饱和边角 **mismatch=0**（codes/d 位/sa 全同） | **PASS** |
| P3 vec_dot | 恒等式 + ISA 断言 | `sdot8(q^0x88888888,a)+8·Σa`（`r91_p1p3.cu:127`）三臂 81920/81920 **逐位等价**；真 Q4_K 实例 **v_dot4 5184→0、v_dot8 0→2528** | **PASS** |
| P4 精度门 | KL ≤0.005 / argmax ≥99%（W913 均值口径） | 组合：R74 logits **KL mean 0.002295 / top-1 100%** + P1↔a4sim 公式同一 + P3 整数等价 ⇒ 真 W4A4+dot8 数值=门测仿真数值 | **PASS** |
| P2 前置微基准 | 同访问面 >1.3× | A_dp4a 0.83 TMAC/s / B_repack **0.962×** / C_packed **1.570×**（3 run×5 trial，CV 6–7%，`run.log`） | **C 过门 / B 判否** |

- **P1 口径钉死**（`r91_p1p3.cu:41`）：BlockA4 = {half d; int16 sa; uint8 qs[16]}，scale=amax/7、roundf、clamp [−8,7]——**逐字对齐 a4sim（`P583`/R74 门测式）**；**sa 是裸整数 Σcodes**（刻意区别于 Q8_1 的 d·Σq fp16 头：sdot8 重定心 `+8·Σa` 在 int32 域需要裸整数）。「Σa 与 kernel 现算一致」由 P3 等价性闭合（kernel 现算的 sa8 与块头 sa 同源同值）。
- **P3 的 ISA 断言超预期达成**（`isa_ab.log`）：判据「Q4_K 实例内 v_dot4 减半且 v_dot8>0」——实测 **v_dot4 5184→0**（全部 dot4 都在 vec_dot 内环，替换后清零）、**v_dot8 0→2528**（5184/2528=2.05:1，正是 2×dp4a→1×sdot8 的密度比）。预处理证明变体真的被编入（pp_builtin_sdot8=1），编译命令逐字抄 `ninja -t commands`。P519 的外证（sdot8→v_dot8_i32_i4，MI50 实测 2× 吞吐）在自家工具链复现（fatbin 管道：harness 里 v_dot4 16 / v_dot8 16）。
- **P4 max-KL 复核裁决**（`P583` 遗留项）：max 0.006704（req3）按 **W913/R59 注册口径**收口——R59 结案原文「mean 0.002005（median 0.000704，**max 0.011209**）⇒ 过（均值口径）」，max 仅记档；本项 max 0.0067 < R59 自己放行过的 0.0112 ⇒ **记档不判死，P4 过门**。W951「P4 大概率是终点（rel_l2 0.0648 预示 KL 过不了）」的预判被 R74+W1058 的实测推翻——rel_l2 0.0648 是合成数据的层输出指标，与真实激活分布的 logits KL 不同量纲。

## 2. 收益定位：纯指令密度≈0 转化，收益全在布局侧（`P587`/`P589`）

三臂微基准的结构结论（与 R116 的「密度 4× 只转化 1.26×」互证成第二例）：

| 臂 | 内容 | 时间 | vs A | 结构含义 |
|---|---|---|---|---|
| A | 现役 dp4a（W4A8，int8 容器） | 2.02 ms | 1.00× | 基线（权重行 LDS 缓存，修掉 w947 原型的 8× 流量缺陷） |
| B | sdot8 + 现场 repack（**不改布局**） | 2.10 ms | **0.962×** | **纯指令替换 ≈0 转化甚至倒亏**（repack 开销吃掉密度收益） |
| C | sdot8 + int4 打包（**P2 形态**，激活字节减半） | 1.29 ms | **1.570×** | 收益来自**布局流量减半**，不是指令 |

⇒ ①「换更强指令」不改数据布局 = 白干（第二例证）；② P2（tile int8→int4 打包）才是收益载体，其前置门（≥1.3×）**过**；③ 但 W943 的 −2.05% 端到端上限是指令口径（dot4 占 kernel 指令 30% × 减半 × 67.1% VALU × 20.4% gate/up）——该口径的「密度转化」假设已被 B 臂证伪，**真候选收益在布局/流量侧而真核 x_qs 流量占比未量**；④ P5 验收门（|Δ|≥2×CV=3.2%）对 1.5–2% 效应不可检（W914 纪律③记「未测出」而非「无收益」）。**预注册下一步：先做 x_qs 流量占比侦察（rocprof PMC / LDS 计数）再裁 P2 立项**；若要 P5 可检须 A/B 重复 ×4–5 把 CV 压到 ≤0.75%，或改层级指标验收。

**接线陷阱（重要，已入账 `P586`）**：`mmq-instance-*.cu` 用**相对 include** `#include "../mmq.cuh"` 直读 **llama-master 树**副本，build overlay 的 `-I` 只对直接编译的 TU（如 W1057 的 `quantize.cu`）有效——**打 overlay 头文件对 mmq 实例 TU 是 no-op**（第一轮 A/B 就是这么拿到「全同」假象的）。改内核头必须打 llama-master 树副本（或双份同改 + md5 配对还原）。

## 3. 下一步

1. **R91 P2 立项侦察**（预注册）：量 x_qs 流量/ LDS 读占 Q4_K mmq kernel 时间的比例（PMC/LDS 计数）——≥25% 才立项 P2 tile 手术（LDS 重排 + `prefill_mmq_tab_test` 逐位）；否则 R91 收在「P0–P4 全过、P2 不立项」。
2. **R101**：#31247 cherry-pick + `quantize.cu` DS4 分支同步（队列第二）。

## 4. CI/CD 与门

provenance 提交（`ci/w1047-coverage`，本轮证据件 + 账本 + 方案回写）+ Downstream gate + GPU gate 双绿（按 W1056 新坑流程：push 后先同步 runner 镜像再等 GPU gate），run id 登记 `deploy/CI_RUNS.tsv`。收尾 `round_close.py` HARD 门全绿后交件。（run id 见文末补记。）
