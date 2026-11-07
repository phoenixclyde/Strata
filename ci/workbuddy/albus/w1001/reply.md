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
| 8 | 本轮改动 | **生产零改动、零重启**（只在 `build-tab/repacktest/` 编独立 A/B）；三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**206 条 / 已结 128 / 62.1%**；主线 **178 / 128**；死块池 **0/28**。
队列：**R97 → R96 → R86 → R91 → R95 → R94 → R89 → R46 → R49**。

---

## 五、按「重写就重写」走的第一步：把 A/B 做对

你上一问的两个质疑，我用**重做实验**回答了，不是嘴上认错。修了 W999 的两个缺陷：

| 缺陷 | 修法 |
|---|---|
| 用错 kernel | 按 mx `mul-mat-id.cu:216` 的 `use_w32 = n_assign < 2*BN_ID*ne02` 分派：rows<4096 走 `mmq_gemm_repacked_w32<true,1,8,Q5_1>`（BN=32、block 32×8），否则 64-wide |
| 激活布局错 | 外网核实 `sizeof(block_q8_1_mmq) == 4*sizeof(block_q8_1)`（128 值/块、144 B）、Q5_1 用 `MMQ_Q8_1_DS_LAYOUT_DS4`；进而做成**两臂共用同一份**我们引擎 `mmq::quantize` 生成的 grouped 激活 |

新产物 `build-tab/repacktest/ab_bench.cu` + `ab_bench`：同一进程、同一 stream、hipEvent 计时，链接 `libstrata_mmq.a`（两步编链，避开 `-x hip` 吃 `.a`），运行需 `STRATA_MMQ_KQ=1`。

## 六、公平 A/B 结果：**结论反转**

16 专家、Q5_1 down 640×2560、3 reps 取中位：

| rows/expert | canonical | repacked | 比值 | |
|---:|---:|---:|---:|---|
| 32 | 0.237 ms | **0.156 ms** | 0.659 | **快 34%** |
| 128 | 0.542 ms | **0.507 ms** | 0.935 | 快 6.5% |
| 320 | **1.245 ms** | 1.430 ms | 1.149 | 慢 15% |
| 1024 | **3.437 ms** | 3.460 ms | 1.007 | 持平 |

⇒ **W999「四档全慢」作废**（那是 dispatch 用错造成的）；repack 在**小行数明显更快**、大行数变慢。你坚持"重写就重写"是对的。

## 七、但端到端不一定赚——这是下一步的关键

W991 实测 2K 请求的每专家 ncols：**min 4 / p50 331 / p90 742 / max 7680**。分布的大头（331~742）正好落在 repacked **变慢 15%** 的区间，只有尾部小专家吃得到 34%。⇒ **全量替换很可能净亏**。

**⇒ 立 R97：按 `expert_bounds` 每段行数混合分派**——小段（<128 行）走 repacked w32，大段留 canonical，一个 group 内混合 launch。这样吃到小专家的 34%，不付大专家的 15%。判据：六长度档 + 2×CV，prefill@2K 提升 ≥5% 才继续。

这也修正了 R86 的完整移植方向：不是"全量 repack"，而是**只为小段提供 repacked 路径**（V3.8 的三条通道仍要做，但范围收窄）。

## 八、更新

- **R86 保持 OPEN**，补 W1001 公平 A/B 数据；P281 留可复现路径；**R97 新立**。
- 方案 **V3.9**：队列改为 **R97 → R96 → R86 → R91 → R95 → R94 → R89 → R46/R49/R50**。
- 外网核对（P280）仍成立：fused FFN 类公开收益 +1.9~14.7%，MoE 版 +17.2% 无对照——都是个位数到十几个百分点，与新测的局部 34% 不矛盾（那是单内核小形状，端到端会被大段稀释）。

## 九、下一步

1. **R97-1**：在 `ab_bench` 里实现混合分派原型（按每段行数拆成两个 launch），先测单内核加权收益；
2. 若加权收益 ≥5%，再进 V3.8 的完整移植（上传侧 repack kernel + 调度侧分派 + 逐位验证）；
3. **R96** 源码可行性并行做（PR #29948 已合并、有跨硬件对照，且不动权重布局）。

（报告已过 `report_lint`：12 字段 PASS。）
