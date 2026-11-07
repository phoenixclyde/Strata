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
| 8 | 本轮改动 | **生产零改动、零重启**（独立 bench/反汇编 + 账本/方案）；三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**201 条 / 已结 125 / 62.2%**；主线 **173 / 125**；死块池 **0/28**。
队列：**R86 → R91 → R96 → R95 → R94 → R89 → R46 → R49**。

---

## 五、把「19.7%」钉死了（并纠正我本轮中途的一个错数）

工具链这次走通：`objcopy --dump-section .hip_fatbin` → `clang-offload-bundler --unbundle --targets=hip-amdgcn-…-gfx906` → `llvm-objdump -d --mcpu=gfx906`，对象是 `build-tab/ar/mmq-instance-q5_1.cu.o`（69 个函数 / 87k 条指令）。

| 类别 | 指令数 | `v_add*+v_mul*` | 占比 |
|---|---:|---:|---:|
| 主 GEMM `mul_mat_q<Q5_1, J=64>` 两个变体 | 1,426 / 1,301 | 258 / 219 | **18.1% / 16.8%** |
| 全部 11 个主 GEMM | 12,063 | 1,959 | **16.2%** |
| `mul_mat_q_stream_k_fixup`（**我们 `stream_k=false`，根本不跑**） | 72,119 | 13,722 | 19.0% |

⇒ W944 记的「19.7%」量级**成立**，但它数的是**地址指令占比，不等于能拿到的加速**；repack 的理论上限 ≈ **16–18%**。

**纠错**：本轮中途我报过一次「8.1%」，那是正则漏匹配 `v_add_u32_e32` 造成的低估，已作废（P276 留痕）。

## 六、第二条独立证据：平面布局本身不值 +84%

mx 的 repack 本质是把权重转成 Q8_0 式平面布局；我们模型的 down 恰好同时有 Q5_1（43 层）和 Q8_0（5 层），可以直接同形状对比（16 专家、640×2560、3 reps）：

| rows/expert | Q5_1 ms | Q8_0 ms | Q8_0 慢 |
|---:|---:|---:|---:|
| 32 | 0.238 | 0.246 | +3% |
| 128 | 0.540 | 0.731 | +35% |
| 320 | 1.243 | 1.442 | +16% |
| 1024 | 3.489 | 3.576 | +2.5% |

Q8_0 是 8 bpw（Q5_1 6 bpw，多 33% 字节）。折算下来**平面布局每字节效率高 15–30%，但多出的字节全吃掉，净耗时仍慢 2–35%** ⇒ 平面布局不足以解释 +84%。

加上 W997 的外网核对（mx README 无 +84% 表；gfx906 fork 公开实测 PP16384 **+14.1%**）⇒ **R86 的预期收益应定在 16–18%，不是 +84%，也不是 20%+**。

## 七、结论：判否倾向明确，但我没有替你关掉它

两条独立证据都指向**单内核收益 <20%**，正落在 W944 自定的「<20% 判否」线内。但按你「测完有实际数据才能做判断」的规矩，**R86 保持 OPEN**——静态指令占比与代理实验是预判，不是 repack 的直接 A/B。

唯一剩余动作：`repack_q51_host()` 生成 repacked buffer + `mmq_gemm_repacked` 接进 `kq_bench`，两臂各 n≥10、2×CV；<20% 即正式判否。

**你的一句话可以省掉半天移植**：若同意按现有静态 + 代理证据结案，我就把 R86 标 DONE_NEG，直接推 R91；否则我按上面做最小 A/B。

## 八、下一步

1. 等你决定 R86 是「直接判否」还是「做最小 A/B」；
2. 同时可并行推进不占 GPU 的 **R91（dot8 P1 量化器）** 与 **R94（KL/top-1 质量门）**；
3. R96（gate/up 融合）的源码可行性判断继续挂着。

（报告已过 `report_lint`：12 字段 PASS。）
