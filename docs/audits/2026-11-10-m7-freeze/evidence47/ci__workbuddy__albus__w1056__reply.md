# W1056 回执：R116 微基准判否（PV dot4 整线关闭）+ 唯一队列按「代码相关 + 前置项」重排

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）· restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args/env 明细 | 38 项 args 逐字未动（`--pack` `--native` `--pcie-frac 0.20` `--spec 4` `--kv k8v4` `--prefill auto:16384` `--kv-grow` 等）；env 13 项未动（含 `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T05:14:12Z` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | VRAM free **884 MiB**（metrics 实时键）；expert cache **8301 槽 / 24,807 MiB（24.2 GiB）**；borrows：metrics 本轮未暴露该键（W1055 读数 2609 槽 / 7.62 GiB，生产未动，本轮只读） |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`（`a85743d7…`）；备份 `tmp/w1052/cfg_pv_pre.bak` / `tmp/w1047/cfg_preinstall_w1047.bak`；rollback = `cp` 回备份 json 并冷重启（≈45 s） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0、**重启 0 次 / 停机 0 s**、装机 0、回滚 0；微基准在一次性 scratch 容器（`docker run --rm`）跑，disk=build=running 三方未动 |
| 9 | ROCm（容器内） | `.info/version` **10.1.0** · HIP runtime **7.16.26323-0000000**（`hipconfig`）· clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | **b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`** + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc`（镜像未换 `2e7539eeb76b` ⇒ pin 未变，沿 W1055 实测；容器内 `ggml-cuda/` 14 个 mmq 文件复核） |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）本轮未动；生产树 `pr/k10` 头 `19dc7ac1b`（W1055 CI 提交），脏 0 行。新证据件：`albus/w1056/`（微基准 `pv_micro_r116.cu` + `run_micro.sh` + `run.log`、账本落地 `land_w1056.py`、队列重写 `rewrite_queue.py`、方案备份 `W832_OPT_PLAN_V2.md.bak-w1056`）。

**三、本次落生产** — **零**：装机 0 / **重启 0 次 / 停机 0 s** / 回滚 0。判否性结论不需要动生产；微基准全部在 scratch 容器完成。

**四、进度** — **530 条 / 已结 442 / 83.4%**（+2 条 `P581`/`P582`，`R116` 判否转 DONE_NEG）。队列（代码 + 前置优先）：**R74 → R91 → R101 → R85/R46 > R64 > R60 → R89 → R95 → R86 →（治理）R80 → R79 → R81**（详见 `W832 §0.1`）。

## 1. R116 微基准判否：dot4 密度红利在 PV fold 上只值 1.26×（P581）

预注册门（`W832 §6.2 R116`）：合成误差预算 → **微基准（同访问面）>1.3×** → 才谈 OPT 位。预算上一轮已 PASS（0.2603%，`P580`），本轮微基准**不过门**：

| 臂 | 语义 | ms/chunk | vs A | 3 run 稳定性 |
|---|---|---|---|---|
| **A_fp32** | 生产 fold 形状（thread t 拥有 dim t，cell-major P in LDS，4-cell V 组载，12 fma/cell） | **0.0270** | 1.000× | 0.0270 / 0.0270 / 0.0270 |
| **B_dot4_pre** | P 预量化（上界臂，量化成本=0），V nibble→int8 现场符号扩展 | **0.0214** | **1.264×** | 1.263–1.265× |
| **C_dot4_live** | 同 B + P 在途量化（诚实臂，生产代价） | **0.0264** | 1.022× | 1.022× |
| **D_dot4_v8** | 同 B 但 V 物化为 int8（读流量 ×2，验证「nibble→byte」代价） | **0.0216** | 1.248× | 1.245–1.248× |

- **正确性**：dot4 臂 vs CPU 同方案参考 **rel_err 5.8e-8**（逐位同构）；A 臂 vs CPU fp32 参考 1.4e-7。合成数据 dot4 vs fp32 rel_rms 0.54%（真实数据预算 0.2603% 不变，两者口径不同：合成 P 分布更平）。几何：CHUNK=64 × G=12 × HD=256，Q4_0 V 池 18B/32 值，nchunk=256、reps=200、5 trial 交错（臂轮转抵消漂移）。
- **结构结论（比数字更重要）**：**PV fold 是访存/延迟瓶颈，不是 ALU 瓶颈**。dot4 把 MAC 指令密度提到 4×，只转化出 1.264×；P 在途量化再吃掉 23%（C vs B = 1.022×）；「V 读流量 ×2」在该形状下近免费（D vs B 只差 1.3%）——V 池整体 282 KB 级、L2 可容，流量翻倍不翻时间。
- **判决**：三臂全 < 1.3× 门 ⇒ **不接 OPT，R116 判否收口**。R110（int4 P，死于长尾）→ R112（真实 dump）→ R116（int8 P）的 k8v4 V 侧 dot 化**整条线关闭**。残余观察记录在案：若未来重开 KV 布局话题，「V nibble→int8 流量 ×2」不再是反对理由。
- **方法论**（举一反三，同 P578 族）：**「指令密度」≠「时间收益」**——任何「换更强指令」类条目（含 R91 的 dot8、R64 的 Q.K int8、P455 的 fp16 dot2）在动内核前都应先过同访问面微基准，把转化率量出来再立项。R91 的 P0（R84）已做 dot8 数值验证，但吞吐转化率尚无微基准——这成为 R91 进 P2 前的新前置检查点。

## 2. 唯一队列重排：代码相关 + 前置项优先（P582，机主 2026-11-08 指令）

`W832 §0.1` 唯一队列按「优先推进代码相关的以及前置项」重排：

- **第一（代码移植 + 前置门）**：**R74**（W4A4 离线精度门，不动内核——R91 的前置）→ **R91**（dot8 接入 P1–P6）→ **R101**（#31247 cherry-pick，`quantize.cu` DS4 分支同步改）。
- **第二（prefill 代码手段，R85 验收随行）**：R46 > R64 > R60；四条前置链显式入队——**R60←R59**（KL≤0.005+top-1≥99%）、**R64←32K/131K attention 占比实测**、**R86←R95 之后且 ≥5%**（默认不开工）、**R63←R61**。
- **代码存量候选（队外 OPEN 一次入册，按需捞）**：P455（fp16 dot2 救 P454 层）· P481（解开 3 处编译期排除）· P424（MMQ load 管线误配核查）· R63 · G1–G10 / D28 / M2 / K8 / U2 / U4 / X3–X7 / P1c。
- **治理排后**：R80 → R79 → R81。
- 举一反三（补查结论）：`W1055` 的 wave64 盘点（`P579`）与本轮微基准共同指向——**R91 动 P2 前先补一个 dot8 微基准**（同访问面量化转化率），否则可能重演「密度 4× 收益 1.26×」的落差。

## 3. 下一步（按新队列）

1. **R74（W4A4 离线精度门，零停机）**：先离线模拟不动内核——参照 P557 探针工程，在 `quantize_mmq_q8_1` 入口做 env 门控一次性激活 dump，真实数据重放 int4 vs Q8_1 量化误差；判据 KL ≤ 0.005 / top-1 ≥ 99%（分辨率 0.0032，跨进程噪声底）。
2. **R91（dot8 六阶段）**：P1 量化器起，P4 KL 门不过即停；**P2 前补 dot8 同访问面微基准**（本轮教训）。
3. **R101**：#31247 单条 cherry-pick + `quantize.cu` DS4 分支同步，提示侧 KL ≤ 0.0139 + 48-token 贪心指纹逐字节。

## 4. CI/CD 与门

本轮改动面 = 账本 + 方案（无引擎代码），provenance 提交照常走 `ci/w1047-coverage`：语法/自检套件 + Downstream gate + GPU gate（`self-hosted strata166-gfx906`），run id 登记 `deploy/CI_RUNS.tsv`（D7 fail-closed）。收尾 `albus/w1002/round_close.py` 15 道 HARD 门全绿后交件。
