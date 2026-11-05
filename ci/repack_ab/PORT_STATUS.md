# R86 完整生产移植 · 状态（唯一权威）

> 立档 W1002。机主三问「你完整移植了吗 / 四项报告呢 / CI/CD 呢」——
> 本文件是**第一问的机器可读答案**，由 `ci/round_gate.py --ci` 强制检查存在。
> 每次推进只改状态行并附证据；**没有实测数据不得写 DONE**。

| 通道 | 内容 | 状态 | 证据 / 缺口 |
|---|---|---|---|
| C1 权重上传 | 专家从 host arena 借槽上传时做 GPU 侧 repack，借槽/换入换出全程保持 repacked 布局 | **NOT_STARTED** | 无 ggml extra buft；现为 host `repack_q51`（仅 bench 内联） |
| C2 调度分派 | 重写 `mmq::Context::run`：`use_w32` / 64-wide / 窄 mat-vec 三路 + `repack_tile_off` + `expert_stride` 改 `repack_gcn_nbytes` | **NOT_STARTED** | 生产 `src/prefill/moe_mmq.cu` 未改；bench 内分派不等于调度 |
| C3 激活对齐 | `mmq::quantize` 输出与 `block_q8_1_mmq_h` 逐字节核对 | **PARTIAL** | W1001 已共用同一份激活，两臂可比；但未做布局逐字节断言 |
| C4 融合 | `ggml_cuda_try_fuse` 的 `{MM_ID,MM_ID,GLU}` | **N/A（prefill 无红利）** | mx README：仅 `ne[2]==1` 单 token |
| C5 验收 | 逐位等价 + 六长度档 A/B + 2×CV + KL/top-1 质量门 + env 开关 + 镜像回滚 | **NOT_STARTED** | 无 |
| C6 R97 混合分派原型 | 按 `expert_bounds` 段行数分派，先出加权单内核收益 | **NOT_STARTED** | V3.9 队列第一项 |

**当前结论**：`PRODUCTION_PORT = NOT_DONE`，`src/` `include/` `CMakeLists.txt` 零改动。
生产二进制 md5 仍为 `eea5ea3749ad54b124330386605a18bc`。

**移植前置判据**（沿用机主「测完有实际数据才能做判断」）：
R97 加权单内核收益 ≥5% 才进 C1/C2；否则不动生产路径。
