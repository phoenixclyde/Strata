## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `6c88738761fa0b8f50495c570fbd9d86`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 8** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` **`--pool-workers 10`（本轮新增）** |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:36:16Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **1 项**：`--pool-workers 10`（+2.49% @2K，见 §六）；门修 2 处；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 16** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **1 项**（pool-workers）；**重启 4 次**（两个中间臂被判不显著/回退 + 最终落库），各 ≈45 s，**停机合计 ≈3 分钟**；回滚件同上。

## 四、进度 + 队列

**188 条 / 已结 113 / 60.1%**；主线 **160 / 113**；死块池 **0/28**。
队列：**R88 → R94 → R89 → R91 → R86 → R87 → R46**（P266 采样通道、P239/P244/P48/P33 穿插进行）。

---

## 五、R88-1 的结论：采样通道不可用，但因果判别给出了别的答案

**采样通道（P266，OPEN）**：三条都试过——

| 尝试 | 结果 |
|---|---|
| `gdb -p` 默认 | 全是 `??`：进程在容器里，`/proc/PID/exe` 的宿主路径不存在 |
| 显式给二进制 | 主程序符号可解（热点 `ggml_vec_dot_q4_K_q8_K`、`ExpertPool::worker`） |
| 采样质量 | 60/95 个栈顶落在 libc 的 syscall 包装（`ioctl`/`read`/`nanosleep`）——**是 attach 暂停造成的伪影**：4 s 的请求被拖到 **17.4 s** |

⇒ 结论：**gdb 采样的分布不能当判据**。要拿首块归因，必须出 `-g` 专用构建或加引擎内计时（P266 的解除条件）。

**换因果实验**：把 CPU 池砍一半（`--pool-workers 10`）——若 1.3 s 是"CPU 出专家不够快"，时间该变差；结果是**变快**。

## 六、`--pool-workers 10` 落库（+2.49% @2K）

| 指标 | 20 workers（基线 w987-base） | **10 workers（w989c）** | Δ | 2×CV 带宽 |
|---|---:|---:|---:|---:|
| prefill @2K | 511.73 | **524.45** | **+2.49%** | 1.00% |
| prefill @8K | 704.32 | 705.88 | +0.22% | 0.46% |
| TTFT 2K | 4.074 s | **3.992 s** | **−2.0%** | 2.00% |
| decode | 36.23 | 36.53 | +0.8% | 13.4% |

**含义**：20 worker（每物理核一个）是**过订阅**——减半反而更快。所以 R88 的 1.3 s **不是"CPU 算不动"**，而是争用/带宽或串行依赖；这直接改写了 R88-2 的假设（见 §八）。

## 七、门又暴露两个 bug（本轮修掉）

| bug | 现象 | 修 |
|---|---|---|
| `--lengths` 只判退化 | 2K **+1.74%** 的提升被当成"无显著"→ 自动回退 | 补 `better = True` |
| 随后的赋值把 `better` 覆盖 | 修了上一条仍回退：`better = dd > band_d or dt2 < -band_t` 在循环之后重写 | 改 `better = better or …`（提交 `0856e14e`） |

⇒ 这也是为什么 `pool-workers=10` 被跑了三次：前两次都是**门自己**把结果吞了。数据在 `ci/state/cfg/w989b|w989c.json` 里可复核。

## 八、方案 V3.2：R88 的假设改写

| 旧假设 | 新证据 | 新假设 |
|---|---|---|
| 首块慢 = CPU 池出专家不够快 | 池减半反而 +2.5% | **争用/带宽受限**：20 个 worker 抢同一条内存通道，反而互相拖慢；首块的 1.3 s 更像"冷专家的内存读取 + 逐层串行" |
| R88-2 = 异步 staged copy | 借用量 7.62→3.11 GiB 无影响 | R88-2 = **首块按层预取（读下一个用到的专家块）**，把"读"和"算"错开，而不是搬更多 |

**修订后的执行序**：

| 序 | 项 | 判据 |
|---|---|---|
| 1 | P266 出 `-g` 采样构建（或引擎内计时） | 能给出首块 CPU/GPU/IO 三段占比 |
| 2 | 依归因决定：预取深度 / 池规模 / 别的 | prefill@2K/8K 双档不掉出 2×CV |
| 3 | R94 质量门（KL/top-1） | KL ≤0.0139、top-1 ≥99% 量级 |
| 4 | R89 / P239 / P244 / P48 / P33 / R91 | 排队 |

## 九、下一步

1. **先把 `-g` 构建做出来**（只用于采样、不替换生产），拿到首块的三段分解——没有它，R88-2 只能猜；
2. 同时跑 **R94 质量门**（R90 的欠账，纯测量、不改配置）；
3. `--pool-workers 10` 已生效，后续所有臂的基线要用新值重录。
