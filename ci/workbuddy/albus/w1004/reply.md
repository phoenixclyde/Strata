# W1004 收尾

**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native …/unsloth-UD-Q4_K_XL-00001-of-00004.gguf --expert-profile /src/data/expert-profile.bin --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --expert-profile-save /data/profiles/q4kxl-learned.bin --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` = unlimited；`VmLck`: 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致 |

**二、主线**

gfx906/mi50 @ 2d07550f · tag `mi50-0.2.10-r32-14-g2d07550f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行 · 远端一致（API：`2d07550fd4af`）。

**三、本次落生产**

改动 0；重启 0 次；停机 0；回滚件未用。代码面 0 个提交（本轮只动 `deploy/` 权威件与本机工具，非 git 面）。

**四、进度 + 队列**

222 条 / 已结 143 / 64.4%；主线 184 / 143；死块池 0/28。
队列：R95 → R86（仅 down，条件启动）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 审计：两天里有七处该入而未入

方法：把 `W955`–`W1001` 逐个在 W832 里 grep 轮次号，再与 `PROGRESS`/`PARAM_REGISTER` 对照。结论不是「轮次号没出现」，而是两类：**账本改了、方案正文没改** 与 **方案里根本没有**。

| # | 缺口 | 证据 | 处置 |
|---|---|---|---|
| 1 | `R94`/`R95`/`R96` 只有队列里一句话，§6.2 无定义行 | `grep "新2[9-9]"` 无；队列第 5/6 行是唯一出处 | §6.2 新增 **新29/新30/新31** |
| 2 | `R88` 定义仍是「异步分阶段拷贝」 | 账本已改靶为「首块重叠」，W990 又证伪（缝隙 15 ms） | 新23 备注写明证伪 + 转 R95 |
| 3 | `R90` 定义仍写 `b12099` / `build-r28` / 「旧树一律不动」 | 生产实为 v0.9.0（`cd959bae`、ggml 0.29.0、`-090`、r32） | 新25 备注写明已上线 + 降 PARTIAL + 指纹策略 |
| 4 | `R93` 定义仍写「待重标」 | W987 三值齐（16K 用 8192 掉 5.75%，维持 16384） | 新28 备注写结案 |
| 5 | 参数轴表写 `--pool-workers = 0（=20）· 无差异` | 生产 args 37 里是 **10**；W989 实测 +2.49%@2K（band 1.00%） | §4.5 表改现值与判词，附 W989 段 |
| 6 | `X1` 表写 OPEN「最被低估的一条」，账本是 NA；`X2` 写 OPEN「锁不住」，实测 memlock 已 -1 | W976（ram≡mmap、已显式 mmap）、W977（VmLck/VmPin=0） | 两行改 NA 并写实测 |
| 7 | 判据区缺两条：token 序列可比性、三个 regime | W958（7/64 相同）、W969/W978（`t≈1.3 s+n/785`） | 判据区各加一条 |
| 8 | 两份「执行序」并存，旧表第 1 序还是 R97 | §6.5 V3.9 表 vs W1003 新表 | 旧表标 SUPERSEDED，注明别按它排期 |

## 号

| 号 | 内容 |
|---|---|
| **P291** | 判据改写：两臂 token 序列不可比，验收改六长度档 + 对金标 KL/top-1 |
| **P292** | 三个 regime（冷读/热读/带复用）+ 冷读拟合 `t ≈ 1.3 s + n/785` |
| **P293** | v0.9.0 版本真相（`cd959bae` / ggml 0.29.0 / `-090` / r32）+ 按 CUDA 目录指纹重建 |
| **P265（参数册新行）** | `--pool-workers 10` ADOPTED；P26 的 REJECTED 只针对 21 这个值 |
| **X2** | OPEN → NA（memlock 已 -1、决定不锁） |

## 顺带查出的门缺口

`mirror_check` 只比 **2** 件（W832、PROGRESS）。实测 166 的 `params/PARAM_REGISTER.tsv` 停在 **2026-11-02 22:02**，`ID_MAP.tsv` **根本不存在** —— 同一类「有两份、没人比」在参数册上又发生一次。已扩到**四件**，`--sync` 逐件推（支持子目录），负向自测 4/4。

四件现状（双侧逐字节）：`W832` `729599306465f8cbc87f0340b882cecd`（143,176 B）、`PROGRESS` `51ea8f457a36359b8b9415672ef9db3d`（185,544 B）、`PARAM_REGISTER` `0f1efc3e4ed617f9d870749def3d6067`（335,422 B）、`ID_MAP` `81891d72f4b7bdb8188b8d14f3a6d3b4`（1,743 B）。

## 边界（什么没入，以及为什么）

- **NVMe 迁移（W972/W975）与门的三次修正（W980/W983/W984）** 只入账本（`P260`/`P261`）与判据区，不单开方案条目——它们是基础设施与流程，不是调优条目。
- **`W959/965/967/968/971`** 近乎空转（0–1 件产物），无可回写。
- **语义差没有机械判据**：`plan_lint` A–D 查「有号→有账」「方案有号→账本有行」，查不出「账本对、正文错」。这次不加判据（无法机械化），改为回写时把**被改写的既有条目**单列成表——W1004 块最后那张表就是模板。
