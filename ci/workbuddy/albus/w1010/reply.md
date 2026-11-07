**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（**未换**） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9（**已被改过一次并逐字节恢复**） |
| 3a | args 明细 | 未变（37 项同前） |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072`（**恢复后**）`STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` ok、`loaded:true`、StartedAt 2026-11-05T15:33:28Z（**本轮手动重启 2 次**；restarts=0（docker restart 不计入，StartedAt 已更新）） |
| 5 | 资源隔离 | `ulimit -l` unlimited；`VmLck` 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、VRAM free 待满载后复测 |
| 7 | 回滚件 | `strata-0.1.56-080`；**本轮实际用到**：`cp /data/strata-huihui-ud-iq4_xs.json.bak_w1010 /data/strata-huihui-ud-iq4_xs.json`（md5 回到 `e62685e6…`） |
| 8 | 本轮改动 | **config 被改过一次（CPU_SHARE_MAX 3072→1024，23:32）并已恢复**；引擎、镜像、args 未变；disk = build = running = `eea5ea37…` |

**二、主线** gfx906/mi50 @ c409936f · tag `mi50-0.2.10-r32-17-gc409936f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 **1 处（已回滚）**；重启 2 次；停机约 1 分钟；回滚件 `…bak_w1010` 已用并校验。
**四、进度** 245 条 / 已结 165 / **67.3%**；队列 R95（plan-ahead 方向）→ R98 → R94 → R91 → R89 → R46。

---

## 一、先报事故

我用 `nohup … &` 把一个 A/B 脚本挂到 166 上跑，ssh 一退出进程就被杀；**但它已经执行到「改 config + `docker restart`」那一步**。结果：**23:32–23:33 生产带着 `CPU_SHARE_MAX=1024` 跑了约一分钟**。我发现后立即恢复：`cp .bak_w1010` → md5 回到 `e62685e6…`（与改前逐字节相同）→ 重启 → `health ok`、引擎 md5 `eea5ea37…` 未变。**没有数据丢失、没有换二进制、config 逐字节回原值。**

两条纪律已写进方案：① 远端长任务**禁止 `nohup`/`&`** 脱管；② 改 config 的脚本必须把「备份 + 写 + 重启 + 校验」做成**原子块**，被杀时自动回滚——这次能恢复，是因为只改了一处且备份就在旁边。

## 二、这个实验本身：开工前被源码否掉了

原计划：`CPU_SHARE_MAX` 3072→1024，看 2K 是否因为落在 1024–3072 区间而走了 staged 路径。读源码后不成立：

- `prefill.cpp:2872`：`if (applies && cpu_share_on()) g_stream_min_share = cpu_share_max();` —— 只有 CPU share **armed** 时它的上限才变成 `stream_all_min`；
- 日志横幅逐字：*“the CPU share is ON by default for prompt chunks **below 1024 tokens**”*，`kStreamAllMinDefault = 1024`；
- 2084 与 16375 都在 1024 之上 ⇒ **2K 与 16K 走同一条 stream-all 路径**，改这个值对 2K 零效果。

**也就是说：这次重启换来的信息量是零。** 事故与无用功是同一件事的两面，我把它记成一笔。

## 三、读出来的真东西：`host grouping` 是「没被盖住的等」

六长度数据里 2K 的 `host grouping` = 92 ms，而 4K 以上按线性外推只该有 ~23 ms。按层折算：2K 1.9 ms/层、16K 1.3 ms/层 —— **主机每层的成本近似恒定，2K 只是 GPU 活少、盖不住它**。

⇒ R95「两轴之外的 40%（≈110 ms）」里至少有一部分是**暴露的主机时间**，不是新增成本。对应解法不是核，是**把下一层的组计划提前到本层计算期间**（plan-ahead）。历史上的 `LAYER_MAJOR`「不发车」结论（`W775delta_W24`）是在 0.1.x 树上、以「本机不激活」为由下的，现在是 0.2.10 全树，**需要按源码重核一次**，不能直接引用。

## 四、门

`plan_lint` / `pointer_lint` / `plan_retired` / `AUDIT_INDEX` / `kernel_curve` / `mirror_check` 六项全绿；六件权威件双侧逐字节一致。
