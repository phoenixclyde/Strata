**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`，本轮未改） |
| 2 | 运行中引擎 | `strata-0.1.57-001`（**回滚后**），md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`（换引擎后已逐字节回退）；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T18:46:29Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | **本轮动用了**：`ci/rollback.sh --exe strata-0.1.57-001 --apply`（ledger 记 `ROLLBACK`）；另存 `strata-0.1.57-002`（b12129 试版）、`0.2.10-101` 镜像 |
| 8 | 本轮改动 | 引擎换 1 次（002）+ 回滚 1 次（001）；镜像、容器、args/env 未变；**disk = build = running = `5e63174d…` 三方一致**（002 另存作实验件）；`RELEASE_CHECK: PASS` |

**二、主线** gfx906/mi50 @ 372106ed · tag `mi50-0.2.11-r33-8` · 落后上游 0 / 领先 71 · 工作树脏 0 行；移植另存 `exp/lcpp-b12129` = `4db10037`。
**三、本次落生产** 引擎 2 次（换 → 回滚）；**重启 2 次**；停机合计约 3 分钟；回滚件动用 1 次；代码面 0 提交进主线（实验分支 1 提交）。
**四、进度** 286 条 / 已结 206 / **72.0%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、「最新」是两个东西，先把它们分开

| 概念 | 值 |
|---|---|
| master HEAD | `45b6604b20f17b7d7638042306c0cd1b6af5999c`（2026-11-05 16:47Z，`model: add support for xing4_0 #31589`） |
| **最新 tag（我拿它当候选）** | **`b12129` = `3259ab6e5dd86fad1931962d784702cb53c7877b`** |
| 生产现用 | `b11062` = `3cf03257…`（2026-09-20） |

差 46 天。HEAD 与最新 tag 只差一个模型支持提交，与引擎无关，所以用 tag —— 可读、可复现、能被 `ci/release_check.py:103` 校验。

## 六、46 天里上游把 MMQ 改了一遍

查 GitHub commits API 与 PR 正文，与我们相关的有四条：

- `#31047` **linearize MoE data layout**：把「每专家的列区间」换成 `mmid.cu` 预算的 **tile 分配表**，并把原先只给 RDNA3/4 的「小 tile 更优」推广到所有 GPU。PR 自报 **MI50 Q4_0 mb64：1343→1657 t/s（1.23×）**、gemma4 26B MoE 454→649（1.43×）。
- `#31188` / `#31296`：MMQ 里融合 MoE gate/up + GLU（含 NVFP4）。
- `#31247`：Q8_1 correction sum 修正 —— **会改数值**。
- `#31679`：mmvq/mmid 的 max batch 改用「最高编译架构」判断。

## 七、移植面 4 类 34 处，全部机械

| 旧（b11062） | 新（b12129） | 处数 |
|---|---|---:|
| `ggml_cuda_mmq_get_config(type, J, fallback, cc)` | `…, cc, prec_src1)` | 5 |
| `mul_mat_q_case<type>(ctx, a, s)` | `<type, prec_src1>` | 24 |
| `new_pool_for_device(int, int)`（`src/prefill/ggml_cuda_host.cu:143`） | `(context &, int, int)` | 1 |
| W4A4 的 `DECL_MMQ_CASE(NVFP4)` | `DECL_MMQ_CASE_W4A4`（`GGML_PREC_Q4`） | 2 |

b12129 里 **`ggml-cpu/iqp.cpp` 已删除**（v0.2.11 构建的硬依赖），但没有任何地方引用它 ⇒ 只影响 Dockerfile 里那句 `test -f`。
全量 **154/154、LINK_OK**，二进制 44,496,832 B、md5 `54ff1635…`、`--version` = 0.1.57。

## 八、实测：三档全回退，超 2×CV

| 量 | b11062（现役） | b12129 | 差 | CV |
|---|---:|---:|---:|---:|
| prefill@2K tok/s | **530.43**（回滚后复测 531.42） | **509.11** | **−4.02%** | 0.75% |
| prefill@8K | **716.02** | **683.13** | **−4.59%** | 0.26% |
| prefill@16K | **780**（`P261` 六档，跨日） | 766.02 | −1.79% | 0.08% |
| decode tok/s | 33.64（回滚后 34.61） | 35.48 | +2~5%（CV 3.97% 内） | — |
| TTFT@2K | 3.95 s | 4.09 s | +3.5% | 0.79% |

**判据是 2×CV，不是感觉**：2K 的带 = 1.5%、8K = 0.5%，两档都越了 3~9 倍。已回滚，ledger 记 `ROLLBACK`，config md5 回 `53ac61e0…`。

## 九、先证明它没算错，再谈快慢

`serve/server.py` 从不填 `logprobs`（content 恒空），所以只能看**贪心输出**：固定 prompt、`temperature 0`、48 token。

- 968-token 英文：**逐字节完全相同**（224 字符）；
- 短英文：前 118 字符相同，新版多 4 字符（48-token 预算边界）；
- 1565-token 中文：差异只在 reasoning 与 content 的分配。

⇒ MoE 布局变了，我们的 prefill 算术**没被算错**。回滚的理由是性能，不是正确性 —— 这两件事必须分开说。

## 十、为什么抄不到 PR 那个 1.23×

`#31047` 的收益来自 **`mmid.cu` 预计算 tile 分配**这条路径，对象是 **Q4_0 + microbatch 64**。
我们的专家是 **Q4_K / Q5_K**，而 `moe_mmq.cu:505` **自己构造 `mmq_args`**（`expert_bounds` 由 pointer-table 设计自己算，见 `src/prefill/moe_mmq.cu:377` 的 `pick_J` 注释）⇒ 新布局那条路**一次都没跑**。
PR 同时把「小 tile 更优」推广到所有 GPU，对 gfx906 可能是负向 —— **这只是候选解释，没有 profiler 证据，不写成结论**。

## 十一、留档：这次不算白做

- 移植在 `exp/lcpp-b12129` = `4db10037`（5 文件），主线 `gfx906/mi50` 仍是 `372106ed`（dirty 0，随时能编 b11062）；
- 试验构建 `build-lcpp` 与二进制 `strata-0.1.57-002` 保留，下次从「已经能编」起步；
- `build-r28`（发布构建）全程未动，`RELEASE_CHECK` 仍 10/10。

## 十二、教训：上游的倍数自带「路径前提」

`1.23×@MI50` 是真的，但它属于「Q4_0 + mmid 新布局」；我们走「Q4_K + 自建 bounds」，抄不到。
这与 `#22174 +17%`、`#31188` 性能栏、`v_mfma` 三次同型：**引用外部倍数必须写清谁的实现、哪条路径、什么形状**，否则它只是线索，不是判据。

## 十三、门与同步

`RELEASE_CHECK` **PASS**（10/10，pin 仍 b11062）；`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1023`、`P354`（b12129 实测回退）、`P355`（移植留档）、`P356`（抄不到 1.23× 的原因），`§0.1` 依赖 pin 行补「b12129 已试并回滚」。
