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
| 8 | 本轮改动 | **生产零改动、零重启**；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**204 条 / 已结 127 / 62.3%**（R86 撤回判否，回退 2 条）；队列 **R96 → R86 → R91 → R95 → R94 → R89 → R46 → R49**。

---

## 五、先撤回：W999 的判否不成立

你的质疑对。查 `mul-mat-id.cu:216` 和 README 后，我那个混搭 bench 有**两个实质缺陷**：

| # | 缺陷 | 实测依据 |
|---|---|---|
| 1 | **用错 kernel** | mx 的 `use_w32 = n_assign < 2*BN_ID*ne02`（BN_ID=128、ne02=16 ⇒ 阈值 **4096**）。rows=32/128 时 n_assign=512/2048，真实实现走 `mmq_gemm_repacked_w32`（32-wide、TN=1、block 32×8）或窄 mat-vec；我**全程强制 64-wide** ⇒ 那两档（尤其"慢 2.28×"）无效 |
| 2 | **激活布局错** | mx GEMM 吃 `block_q8_1_mmq_h`：`QK8_1_MMQ = 4*QK8_1 = 128`、f32 `d4[4]`，由 `quantize_mmq_q8_1_cuda` 生成；我填的是标准 `block_q8_1`（32 值/块）全零 ⇒ stride 与 LDS 读取模式都不对 |

⇒ **W999 四档数字不能作判据**。已改账：**R86 回 OPEN**、**P278 标 CORRECTION 作废**，新增 P279（完整移植清单）、P280（外网收益核对）。之前"三条独立证据同向"里，反汇编与代理实验仍成立，但它们只能说明"上限不高"，不能替代直接 A/B。

## 六、"怎么做完整生产移植"——是重写，不是接入

mx README 说得很清楚：它是**给 ggml CUDA backend 写的**，对外只有 `repack.cuh`，三条接入通道。而我们用的是自有 prefill MMQ（`mmq::Context::run` / `moe_mmq.cu`），**没有那套 loader / graph / dispatch**：

| mx 通道 | mx 做法 | 我们要做的 |
|---|---|---|
| ① 权重上传 | `buffer.cu` 把 repack buffer type 注册给 loader，`set_tensor` 在上传时转换；`get_tensor=nullptr`，write-once | 我们没有 extra buft：专家权重在 host arena 71.7 GiB，prefill 每 chunk 借 2606 槽上传。⇒ 要在 `expert_cache.cpp`/prefill 上传路径加一次 **GPU 侧 repack kernel**（上传后就地转），且借槽/换入换出时都要保持 repacked 布局 |
| ② Compute dispatch | `ggml_cuda_mul_mat{,_id}` 按 `should_fire(src0)` 路由，MoE 用 `repack_tile_off` 生成 `tile_off`/`tile_meta` | 重写自有调度：按 `use_w32` 在 **w32 / 64-wide / 窄 mat-vec** 三路径分派、移植 `repack_tile_off`、`expert_stride` 改 `repack_gcn_nbytes`（1,239,040 vs 现 1,228,800 B） |
| ③ Fused FFN | `ggml_cuda_try_fuse` 的 `{MM_ID,MM_ID,GLU}` 分支 | README 明说融合**仅单 token**（`ne[2]==1`），"every step of a speculative verify batch and every multi-slot decode" 都落回 GEMM ⇒ **prefill 多 token 拿不到这个红利** |
| ④ 激活格式 | `quantize_mmq_q8_1_cuda` → `block_q8_1_mmq_h` | 我们 `mmq::quantize` 是 `mmq_q8_1_ds_layout` 变体，需逐字节核对兼容性（W999 就是栽在这） |
| ⑤ 验证 | — | `prefill_mmq_tab_test` 逐位、六长度档 A/B、2×CV、KL 质量门、env 开关 + 镜像 `.new`+`mv` 回滚 |

**结论**：不是"把 mx 接进来"，而是**在我们自有 prefill 路径里重写一套 repack 支持**——上传侧 kernel、调度侧三路分派、tile 元数据、激活格式核对、全套验证。W944 说的"约 60 行"只算了 kernel 改动，没算这三处基建。

## 七、"完整的就会好？"——不一定，而且我们的靶子拿不到主要红利

**上网核到的公开数据（P280）**：

| 来源 | 数字 | 可信度 |
|---|---|---|
| PR #29948（fused FFN gate/up+GLU，**已合并**） | DGX Spark Q4_K_M pp **840.1→899.9 t/s（+7.1%）**、全格式 +4.6~7.4%；RTX 5090 **+1.9~4.1%** | 有跨硬件对照、同配置 |
| PR #28702（同类，贡献者数据） | pp16K +10.5~14.7%（DGX Spark）/ +4.1%（5090） | 草稿 PR、未经独立复现 |
| PR #31188（MoE 版） | 宣称 +17.2% | **原文明确「无对照数据、不能归因」** |

三条都指向**个位数到十几个百分点**，且强依赖硬件/形状；**没有 84%**。另有独立分析强调：融合收益来自"省 launch 与中间搬运"，当未融合 kernel 已高效时会缩水。

**为什么完整移植也不必然好**：

1. mx 的 repack 主场景写的是 **Q8_0 / MXFP4**，Q5_1 虽在类型表里但不是主场景；
2. **融合红利只对 decode 单 token MMV 有效**，而 R86 的靶子是 **prefill 2K 短档**（多 token GEMM）——拿不到；
3. 2K 短档的真瓶颈是 **tile 填充率**（R95：每专家行数少），repack 改的是权重布局/地址计算（静态占比 16–18%），不是同一根因；
4. 完整移植还会新增成本：每次上传的 repack kernel、`repack_tile_off`、stride +0.9% VRAM；
5. W997 反汇编与 W998 代理实验仍指向"上限不高"。

⇒ **完整移植后最可能是「持平或小幅正」，没有依据期待大幅收益**。要确定只能做完再测——但按投入产出，我不建议先做它。

## 八、举一反三：队列重排为 R96 优先

**R96（gate/up + GLU 融合，PR #29948）比 R86 更该先做**：已合并、有跨硬件对照数据、直接打在 R95 的主战场（`gemm gate/up` 占 prefill 20.6%）、且**不需要动权重布局/上传路径**。我们引擎已有 `moe_mmq_tab.cuh` 的 mirrored scheduler，融合是改 epilogue 而不是重写基建。

R86 则先补齐 A/B 的两个前置（按 `use_w32` 分派 + 用我们自己的 `mmq::quantize` 输出做 grouped 激活），重测后再定去留。

## 九、下一步

1. **R96-1**：读 PR #29948 的 CUDA 改动，判断能否映射到 HIP `mul_mat_q_tab`（源码可行性，不动生产）；
2. **R86 补齐 A/B**：改 `repack_bench.cu` 加 `w32` 分支、链接 `libstrata_mmq.a` 复用 `mmq::quantize`，四档重测；
3. **R91 / R94** 并行（不占 GPU）。

（报告已过 `report_lint`：12 字段 PASS。）
