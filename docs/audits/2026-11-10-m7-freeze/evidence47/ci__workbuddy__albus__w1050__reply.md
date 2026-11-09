# W1050 四件套 — R106 结案 / R113 护栏验证 / R114 三件套就位

**一、生产容器（10 字段，2026-11-08 02:5x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835` · `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | `--pack` `/data/packs/ud-q4_k_xl` `--native` `…UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`（**更正**：旧报告 3a 的 `--serve` 首位系误抄，live args 无此 flag） |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1` 共 13 项未动 |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T17:01:45Z` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1049/cfg_preinstall_w1049.bak`；rollback = cp 回备份 json 并重启容器（≈45 s） |
| 8 | 本轮改动 | **零**：disk = build = running 三方一致；**重启 0 次 / 0 分钟停机 / 装机 0 / 回滚 0** |
| 9 | ROCm 版本 | 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp 版本 | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行，上游本轮未重算。本轮新候选分支 `gfx906/r114@7d4db2363`（GDN dot2）与 `gfx906/r113`（#30837 断言验证构建）；`ci/w1047-coverage@18d44dc24` 在册，本轮收尾将追加 provenance 提交。

**三、本次落生产** — **零**（重启 0 次 / 0 分钟停机）。微基准、离线门、工具链修复全程零停机；R114 的 G2 窗口下轮单独报。

**四、进度** — **496 条 / 已结 403 / 81.2%**。新增 P548–P550；R106 结案。

队列：**R114（G2 窗口 + 相位 A/B，候选已建）** → **R113（余 4 提交择机）** → **R110/R112（PV-dot8 真实 P/V）** → **R111（GPU runner）** → **R105** → **R107（audit 欠账，机主自理）**。

## 1. R106 结案：改参唯一道工具链与生产零漂差（P548）

`gen_config.py --live` → **(无差异)**。清掉的漂差（原九处 + 运行中抓出的派生项）：

| 类 | 行 | 处置 |
|---|---|---|
| 同义重复 emission | P55 / P56 | P55→SUPERSEDED（P110 承载语义）；P56→REJECTED（对齐 P541：生产未设 REDUCE12） |
| 坏 name（= +中文/整句） | P156 / P230 | 降级 MEASUREMENT / PLATFORM 记录行，不再 emission |
| 缺声明行 | TUNED/DECODE_TIMING/SPEC_DEPTH/PREFILL_TIMING | 补 P543–P546（ENV/ADOPTED） |
| META 过期 | tokenizer / model_name | 对齐 `/data/packs/ud-q4_k_xl` + `ud-q4_k_xl-abliterated` |
| **tuned7 家族 emission 归属** | P78/P103/P109/P110/P115/P116/P127/P149/P245 | 实证 `arch_defaults.cpp` 缺省生效（`{"STRATA_HC_Q8","1"}` 等）⇒ scope=DEFAULT 不 emission |
| 参数数据 bug | P138 `direct(缺省)` / P259 描述性 name / P254 name 混值 / V02 旧 IQ4_XS 路径 | 逐一规范化 |
| **P547 `--serve` 反向否决** | 新增行按 live 实证 REJECTED | live args 无此 flag；W1047/W1049 报告 3a 误抄旧文（已在 3a 更正） |

工具链加固：`validate()` fail-closed（ENV/CLI name+value 严格正则，坏行**报错不静默生成**）+ `--self-test` **8/8**（含 W1040 两种真实损坏形态的负例）；`--live` 规范化比较（键序 cosmetic、exe 归 D5、args 按多重集）。

## 2. R113 #30837：wave64 不变量验证（P549）

GitHub API 取真实 diff：`1a24df16` = **仅 1 行** `static_assert(I % warp_size == 0, …)`（编译护栏，零 codegen）。本树 `mmq.cuh` 该锚点 **2 处**（双模板），双插后 **编译通过** ⇒ gfx906/wave64 配置满足不变量。断言随下次重编带上；无行为改动故不换件（同树重编 bit 可复现已由 hc4b md5 复现证实）。余 4 提交（#29948 FFN 融合 / #31373 RDNA4 无关 / #31296 NVFP4 / #31047 MoE 布局）保持 OPEN 择机。

## 3. R114：离线门 + 微基准 + 候选（P550）

- **离线权重门**（GGUF 4 分片真实值，`gguf-py` 解析）：`blk.N.ssm_alpha/beta.weight` 4.42M×2 值，F32→引擎 bf16 **100% 精确**；bf16→fp16 无损率 99.909%/99.957%，**0.47–0.5% 落 fp16 次正规区**（min 2.8e-11，max≈1.1 无溢出）⇒ 无损 FAIL / 范围 CONDITIONAL。外证印证：「权重在 [6.1e-5, 65504] 内转换精确，风险在两端」。
- **微基准**（`gdn_ab_bench.cu`，真实形状 n=2560/rows=96）：dot2 **5.75 vs 7.65 us/call = 1.330×**，rel_rms 2.1e-4。关键机制发现：该点**延迟/占用受限**（每调用仅 12 blocks、实测 65 GB/s ≪ HBM 墙）——先验 roofline 否决被实测推翻，与「gather 型换指令无效」并不矛盾（那类是真带宽墙）。
- **候选**：`strata-0.1.57-r114`（`gfx906/r114@7d4db2363`，md5 `d909d597…`），`STRATA_GFX906_GDN_DOT2=1` 开，fmaf 原内核保留为 off 臂。**G2 KL + gdn 相位 A/B 窗口下轮开**；若 G2 失败预案 = per-row 2^k 二次幂缩放（外证：缩放保 bf16 有效位、只改指数）。

落点可复核：tuned7 缺省在 `src/core/arch_defaults.cpp:222`（`STRATA_HC_Q8`）与 `:231`（`STRATA_HIP_PROMPT_F16`）；GDN ab 热点 `src/kernels/cuda/fused_gdn.cu:101`（`gdn_ab_kernel`）与 fmaf 点 `:115-118`；gen_config 校验 `deploy/params/gen_config.py:34`（`validate()`）；离线门 `albus/w1050/gdn_fp16_gate.py:1`；#30837 断言落点 `llama-master/ggml/src/ggml-cuda/mmq.cuh` 的 `ggml_cuda_mmq_get_I` 两处模板。

## 4. 边界与纠错留痕

- **R107 不代做**：机主 01:19「审计欠账继续记着，后面我处理」——记账保留（18 轮欠账、audit_scope FAIL）。
- 本轮工程教训：①长字面量跨工具链会被改字节（`stream)>>>` 多括号、`\n`→`/n`），编译错要用 `od` 对字节不靠目检；②GGUF array 子类型只读一次；③「roofline 否决」前必须量 launch 形态/占用。
- 全部产物在 `albus/w1050/`；候选二进制在 `/data/bin/strata-0.1.57-r114`（未装）。

门状态（收工行）：报告三门 / 方案 / 账本 / 指针 / claim_homes / round_ledger / live 三硬门 / gen_config 自测 8/8 / deploy_gate 自测 14/14——全 PASS；唯一 FAIL 为既存 `audit_scope`（机主自理）。
