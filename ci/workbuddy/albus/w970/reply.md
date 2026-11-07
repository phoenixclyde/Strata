**刚才那两次 down 是我在切基线，不是崩了。** 现在已起来并在跑 **llama.cpp 0.8.0**：health OK、真实请求 5.20 s / 2,353 prompt / 503–535 tok/s。

## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | **`209d8f50a77d9d45803c9cbbe3e70dde`，44,908,992 B**（0.8.0 构建，overlay ON） |
| 3 | **config** | md5 **`07b4cedd70534ffb23b07f09df8882ae`**；exe=**`/data/bin/strata-0.1.56-080`**；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T13:58:06Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB`（与旧版一致） |
| 7 | 回滚件 | 旧引擎 `/data/bin/strata-0.1.56`（md5 `ae085365…`）；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w970 /data/strata-huihui-ud-iq4_xs.json`；`ci/strata-ci rollback --exe strata-0.1.56 --apply` |
| 8 | 本轮改动 | **引擎换版**：disk = build = running 全为 `209d8f50…`；主线 `304bd3be` / tag **r31** |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag **`mi50-0.2.10-r31`**（末条 tag == HEAD）· 上游 `ffa80d73` · 落后 0 / 领先 41 · 工作树脏 0 行。

## 三、本次落生产

| 项 | 内容 |
|---|---|
| 改动 | 引擎 `strata-0.1.56` → **`strata-0.1.56-080`**（0.8.0 基线 + 我们 35 行适配 + overlay 移植） |
| 重启次数 | **2 次**（冒烟 1 + 切换 1），停机 **≈13 分钟**（每次装载约 4 分钟，机主看到的"起了又 down"就是这两次） |
| 回滚命令 | `python3 -c "import json;p='/data/strata-huihui-ud-iq4_xs.json';c=json.load(open(p));c['exe']='/data/bin/strata-0.1.56';json.dump(c,open(p,'w'),indent=1)" && docker restart strata166-407` |

## 四、进度 + 队列

**176 条 / 已结 102 / 58.0%**；主线 148 / 102 / 68.9%；死块池 0/28。**R90 结案（DONE）**。
队列：**六长度档 A/B 验收** → 摘 `#29953` 越界 padding + 核 `moe_mmq` 尾部余量 → R88-量 → R86-A/B → R87 → R46 → R91 → R93。

---

## 一、机主那句"overlay 不是 on 吗"救了这次上线

上一版我为了绕开编译错误把 overlay 关了，那是缩水。真正原因是 0.8.0 两处签名变化：

```cpp
// mmq.cuh (0.8.0)
typedef void (*ggml_cuda_mmq_load_tiles_t)(const char * __restrict__ x,
                                           const char * __restrict__ x_gate,   // 新增：fusion 的 gate
                                           int * __restrict__ x_tile, const int kbx0, const int i_max, const int stride);
ggml_cuda_mmq_write_back_mma<type, J, fallback, prec_src1, false>                 // 新增 has_fusion
```

overlay 生成器现在按目标树自动补这两处（`x_gate` 接收但不用，trellis 没有 fused 路径；`has_fusion=false`）⇒ **dp4a 与 MMA 两条 trellis 分支、连 NVFP4 那个 TU 都编得过**，`STRATA_MMQ_TQ_OVERLAY=ON` 与生产一致。

## 二、这次跟上游，跟到了什么

| 项 | 值 |
|---|---|
| 上游基线 | `b12099` = 0.8.0（2026-10-28 bump，11-04 发布） |
| 我们的适配 | 35 行（`GGML_PREC_Q8` 透传 34 处 + `new_pool_for_device` 签名）+ overlay 的 2 处模板参数 |
| 构建 | `build-r29`，生产同款 flags，overlay ON，**44,908,992 B，0 error** |
| 试跑（生产配置） | health OK；2,354 tok / 4,732 ms = **497.4 tok/s** |
| 上线后实测 | 5.20 s / 2,353 prompt / 16 out；引擎侧 **503–535 tok/s**；cache 7463 槽位不变 |

## 三、为什么敢切（前几轮的代码级证据）

- 我们实际跑的 **J=64 / fallback=false** MMQ 内核：0.7.0 = 23,164 B、0.8.0 = 23,168 B，**sgpr 44 / vgpr 128 / spill 0 全同**；
- `mmq-config-gcn.cuh` 逐字节相同，我们的 CASE 是 `stream_k=false`（所以 `#30553` 无关）；
- 热态生产路径 A/B：0.4.1 **503** / 0.8.0 **497** / 回滚件 **506** tok/s，差 ≤1.8%。

## 四、还没做（下一步，按顺序）

1. **六长度档 A/B 验收**（2K/8K/16K/32K/64K/130K，真实文本，`|Δ| ≥ 2×CV`），基线模型 `t ≈ 1.7 s + n/822`；
2. **摘 `#29953` 的越界 padding**（`ids_dst` 补 `J-1`、`src1_q8_1` 按 `nthreads` 上取整），并核我们自己 `moe_mmq` 的尾部余量——这是正确性项；
3. 观察一两天：spec/MTP 接受率、vision、长上下文（130K）有没有新告警。

产物：`deploy/W970_R90_DEPLOY.md`（上线记录 + 回滚）；新引擎 `/data/bin/strata-0.1.56-080`；旧引擎原地保留；结案台账 43/43。
