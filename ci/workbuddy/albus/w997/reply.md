## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `..._MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；`VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | **生产零改动、零重启**（只跑独立 bench/PMC + 改账本/方案）；三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**199 条 / 已结 123 / 61.8%**；主线 **171 / 123**；死块池 **0/28**。
队列：**R86 → R91 → R96 → R95 → R94 → R89 → R46 → R49**。

---

## 五、先纠正上一轮的错误

W995 我说「`ref/mx` 的 ggml-cuda 下没有 repack 实现、sparse clone 没带全」——**错了**。`ref/mx` **本身就是 repack 源码目录**，8 个文件都在顶层（我上次只搜了 `ggml-cuda/` 子目录）：

| 文件 | 内容 |
|---|---|
| `repack.cuh` | 对外 API（7 个函数） |
| `repack-common.cuh` | 布局数学 `repack_qs_stride` / `repack_gcn_nbytes`、X swizzle、设备结构 |
| `repack-kernels.cuh` | 全部 device kernel：`repack_tile_off`、`mmq_gemm_repacked_impl` + 64/32-wide 包装 |
| `repack-common.cu` | `repack_q51_host()`（:285）等主机端转换 |
| `buffer.cu` / `mul-mat.cu` / `mul-mat-id.cu` | buffer type、dense/MoE dispatch |

⇒ **R86 不需要"找实现"，实现齐备**，只差接进我们的 `kq_bench`。

## 六、本机新数据：形状扫描 + PMC

**① 形状扫描**（`kq_bench`，16 专家，3 reps；Q5_1 down 640×2560 / Q4_K gate-up 1280×2560）：

| rows/expert | Q5_1 TMAC/s | Q4_K TMAC/s |
|---:|---:|---:|
| 32 | **3.55** | 5.67 |
| 64 | 4.62 | 5.13 |
| 128 | 6.22 | 5.83 |
| 320 | 6.77 | 6.56 |
| 1024 | **7.69** | 7.94 |

⇒ 每专家行数从 1024 降到 32，Q5_1 供给率掉 **54%**；这正对应 R95 里 2K 短档 gemm down 1.87× 的每 token 成本。**R86 的靶子确实存在**。

**② PMC**（`rocprofv3` 采 `mul_mat_q<(ggml_type)7,64,false>`，Q5_1）：

| 计数器 | 值 |
|---|---:|
| SALUInsts | 674 |
| VALUInsts | **21,233** |
| SALUBusy | 1.7–1.9% |
| VALUBusy | 53–59% |

⇒ 标量地址指令只占 **3.1%**；kernel 是 VALU/访存混合受限，不是纯地址计算。W944 记的「`v_add_u32/v_mul_lo_u32` 占 19.7%」指的是 VALU 里两条特定 opcode，本机尚未复核（`roc-obj-extract` 没产出，已列待办）。

## 七、上网核对：`+84%` 口径不成立

| 来源 | 实际写了什么 |
|---|---|
| `ref/mx/README.md` | **没有任何 Q5_1 +84% 的表**；全文唯一数字是 MoE **mat-vec（decode）** 的 `+3.5% at <64,16,16>` / `−15.9% at <8,4,32>` |
| `iacopPBK / mxxm-t` gfx906 fork 公开实测 | PP16384 **+14.1%**、120k fill +9.3%（同配置、temp0 sha 一致） |
| kamali-lab gfx906 fork | 列了 mmq 软件流水/MMVQ 改动，未给 Q5_1 单格式数字 |

⇒ W944 记的「mx 官方表 Q5_1 +84% prefill」在本机 README **查不到**，不能当本机预期写进方案。**R86 的单内核收益上限按 ~20% 估**——恰好压在 W944 自定的「<20% 判否」线上。

## 八、方案 V3.5：先做最小 A/B，不直接动生产

1. 用 `repack_q51_host()` 在 `kq_bench` 生成 repacked buffer，`mmq_gemm_repacked` 跑同形状（16×320，Q5_1 640×2560）；
2. 两臂各 n≥10、2×CV；**<20% 判否、≥40% 才谈生产**；
3. 并行复核 19.7% 那条指令占比——若真实占比远低于此，R86 可直接判否，省掉移植。

**为什么这一步必须先做**：PMC 已表明 kernel 不是被标量地址指令卡住；若 19.7% 也不成立，花半天移植 repack 很可能换来 <20% 的结果，正好被自己的判据否掉。

## 九、下一步

1. 修好反汇编路径（`roc-obj-extract` → `llvm-objdump`），数出 `v_add_u32/v_mul_lo_u32` 的真实占比；
2. 依结果决定：直接判否 R86，还是接 `repack_q51_host` 做单内核两臂；
3. R91 / R96 / R94 并行不占 GPU。

（报告已过 `report_lint`：12 字段 PASS。）
