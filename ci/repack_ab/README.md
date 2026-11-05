# R86 / R97 — Q5_1 repacked MoE GEMM：可复现 A/B

> 入仓原因（W1002，2026-11-05）：W999–W1001 的结论全部产自
> `/home/albus/strata166/build-tab/repacktest/`（临时构建目录）和 `/tmp/*.cu`，
> **不在 git 里、CI 看不见、换机即丢失**。本目录把源码、复现脚本、结果表、
> 已知局限与完整移植状态一起固化，让每个数字都能被重跑。

## 1 这两份 bench 分别是什么

| 文件 | 出处 | 用途 | 是否有效 |
|---|---|---|---|
| `repack_bench.cu` | W999 → W1001 修正 | 单臂：mx repacked Q5_1 GEMM，按 `use_w32` 分派 w32 / 64-wide；激活为零填充 | 只用于「kernel 能不能编、能不能跑」，**不作判据** |
| `ab_bench.cu` | W1001 | **公平 A/B**：两臂在同一进程、同一 stream、共用同一份由我们引擎 `mmq::quantize` 生成的 grouped `block_q8_1_mmq_h` 激活；A 臂 `mmq::Context::run`（现役），B 臂 mx repacked GEMM | **当前唯一有效判据** |

W999 的结论（「四档全慢、R86 判否」）**已撤回**，原因见 `deploy/W986_PLAN_V3.md` V3.8：
① 没按 `mul-mat-id.cu:216` 的 `use_w32 = n_assign < 2*BN_ID*ne02`（16 专家时阈值 4096）分派，
小行数档被强制走了 64-wide；② 激活填的是标准 `block_q8_1`（32 值/块），
而 mx GEMM 要 `block_q8_1_mmq_h`（`QK8_1_MMQ=128`、`d4[4]`）。修掉这两处后结论反转。

## 2 依赖（都在 166，容器外/内路径）

| 项 | 路径 |
|---|---|
| 镜像（含 hipcc / ROCm / cmake） | `strata-gfx906:0.2.10-101` |
| 我们的 fork | `/home/albus/strata166/pr/strata-fork` |
| ggml 0.29 参考树（**不是 b12099，那是 0.28**） | `/home/albus/strata166/ref/llama_b12110` |
| mx repack 参考源码（8 文件，外部资产，不入仓） | `/home/albus/strata166/ref/mx` |
| 现役 MMQ 静态库 | `/home/albus/strata166/build-tab/libstrata_mmq.a` 等（W994 全量重编产物，md5 复现生产） |
| 输出目录 | `/home/albus/strata166/build-tab/repacktest` |

## 3 复现

```bash
bash ci/repack_ab/run.sh            # 摆头文件 → 编译两个 bench → 跑四档
python3 ci/repack_ab/verify.py      # 纯静态自检，CI 用，不需要 GPU
python3 ci/round_gate.py --ci       # 产物 + 四件套工具 + 移植状态自检
```

`run.sh` 需要 `--device=/dev/kfd --device=/dev/dri`（与生产共享同一张卡，
只跑毫秒级 kernel，**不改生产配置、不重启容器**）。运行 `ab_bench` 需要
`STRATA_MMQ_KQ=1`（`kq_ok()` 在非 DSO 构建下要求此 env）。

## 4 结果（`RESULTS.tsv`，16 专家，Q5_1 down 640×2560，3 reps 中位数）

| rows/expert | canonical | repacked | 比值 | |
|---:|---:|---:|---:|---|
| 32 | 0.237 ms | **0.156 ms** | 0.659 | 小专家快 34% |
| 128 | 0.542 ms | **0.507 ms** | 0.935 | 快 6.5% |
| 320 | **1.245 ms** | 1.430 ms | 1.149 | 慢 15% |
| 1024 | **3.437 ms** | 3.460 ms | 1.007 | 持平 |

**但端到端未必赚**：W991 实测 2K 请求每专家 ncols **p50=331 / p90=742**，
大头正落在变慢区间。⇒ 方案 V3.9 立 **R97：按 `expert_bounds` 每段行数混合分派**
（小段走 repacked w32，大段留 canonical），判据六长度档 + 2×CV、prefill@2K ≥5%。

## 5 已知局限（不许当生产结论引用）

1. **不是完整生产移植**：mx kernel 与 ggml 0.29 头文件混搭；`ggml_cuda_q8_1_cache_acquire`
   被 stub 成 `cached=nullptr, hit=false`。
2. **只计时，没有逐位等价验证**（输出数值未与 CPU 参考对照）。
3. 权重是随机字节、激活是量化后的随机值；只保证两臂输入相同，不代表真实分布。
4. mx 松散 grid 有空转；`repack_q51` 是 host 端内联实现，未走 GPU 上传侧 repack。
5. 融合 FFN 红利仅单 token decode，prefill 多 token 拿不到。

## 6 完整移植的状态

见 `PORT_STATUS.md`。**当前三条通道全部 NOT_STARTED，生产源码零改动。**
`ci/round_gate.py --ci` 会强制检查该文件存在，防止「嘴上说移植完了」。
