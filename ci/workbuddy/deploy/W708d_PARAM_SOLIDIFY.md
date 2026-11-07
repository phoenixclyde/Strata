# W708d -- Strata 参数面：固化机制 + 组合/冲突矩阵 + 批次 A 结果

> 时刻：2026-10-08 00:55 CST ｜ 机器：166（1 x MI50 32GB gfx906 + 128 GB RAM）
> 承接 `W708c_PARAM_AUDIT.md`（现状 / 未配候选 / 不该动）。本件加两件机主要求的东西：
> **① 固化机制（跑完不扔、有效果的收进来）；② 冲突与协同的组合分析。**

## 0. 结论先行

- **固化机制已建成并自证**：`PARAM_REGISTER.tsv`（唯一真值）-> `gen_config.py`（生成生产 config）-> `verify_config.py`（复验生效）。
  生产 config **不再手改**，只由生成器产出；每条被采纳的改动都可追溯到证据行、也可被复验证明真的生效。
- **批次 A 已落地并复验通过：13/13 PASS**（新增 `--expert-profile-save` + 把 env 落进 config）。
- **校准（P24）被一个硬约束挡住**：`tools/calibrate.py` 要**独占 GPU** ---- 实测它自己的引擎
  `cudaMalloc(1485606400) for the weight arena failed (out of memory): 568 MiB of 32752 MiB VRAM free`。
  => 必须**先停生产容器**，约 10~15 分钟窗口。**这一步需要机主给窗口**（WorkBuddy 正接着这个模型）。

## 1. 固化机制（三件 + 一个闭环）

```
        测量/证据                     判定                      ← 人工只做这一步
   ab_runs/<id>_<ts>.md  ──►  PARAM_REGISTER.tsv  ──►  gen_config.py --write
                                 (status=ADOPTED)          │
                                                           ▼
                                                  /data/strata-ud-iq4_xs.json
                                                           │
                                        verify_config.py ◄─┘  （重启后复验 4 个数据面）
```

| 件 | 作用 | 关键设计 |
|---|---|---|
| `params/PARAM_REGISTER.tsv` | **唯一真值**。35 行 = 12 ADOPTED / 14 CANDIDATE(+1 BLOCKED) / 8 REJECTED | 每行带 `requires` / `conflicts_with` / `synergizes_with` / `evidence` / `verdict`；`id` 稳定（如 `P20`），跨波复用 |
| `params/gen_config.py` | 由 register **生成**生产 config | 只吃 `status=ADOPTED`；`--live` 与 166 现行 config 做 diff；`--write` 落盘并备份；`CALIBRATED` 值会被跳过并列出来 |
| `params/verify_config.py` | **证明** ADOPTED 项真的生效 | 四个独立数据面：config JSON / 容器 `Config.Cmd` / `Config.Env` / 引擎**当前这次**启动块里的 `engine started:` 行（锚到日志里**最后一次**，避开跨启动块历史行） |
| `params/ab_runs/` | 每次 A/B 的原始读数与判定 | 与 register 的 `evidence` 列互指 |

**闭环纪律**：`测 -> 判 -> 改 register -> gen_config --write -> 推 166 -> 重启 -> verify_config`。
**任何一步 fail 都不许进下一步**（本次就靠这条抓到了 cp 权限问题，见 §3）。

## 2. 冲突 / 协同矩阵（源码级，带行号）

### 2.1 资源争夺（同一份 VRAM / RAM / CPU）

| 争夺 | 机制（证据） | 结论 |
|---|---|---|
| **`--prefill auto:N`  vs  专家缓存** | `--prefill auto` 的定义就是"the largest chunk **whose buffers the expert cache can lend**"（`generate.cpp:507-508`）；我们当前借 **1554 槽 / 3.49 GiB**；另有 `--no-prefill-borrow` 反证"借"是默认 | **必须成对评**。chunk 从 8192 -> 32768 会借走约 4 倍槽位，prompt 期间可用专家槽大幅下降 |
| **`--kv-resident N` / `--kv-grow`  vs  专家缓存** | help L128-134 明写 "the **freed VRAM goes to expert slots**" | 同一块 VRAM 的**三方**竞争（KV / 专家槽 / prompt 缓冲） |
| **`pin=N`  vs  prompt-cache / 专家槽** | pin 要把共享前缀的 K/V 钉住 | 需实测；pin 的价值在"同长文反复问"，不是吞吐 |
| **`STRATA_PREFILL_CPU_SHARE`  vs  CPU 专家池** | 它让 CPU 在 chunk<1024 时算"最少被路由的专家" | 与 21 个 pool worker 抢 CPU；`--no-pool` 与它**直接互斥** |

### 2.2 硬前置（requires，不满足则无意义）

| 项 | 前置 | 证据 |
|---|---|---|
| `STRATA_GR_SPLIT=1` | **`STRATA_GR_FAST=1`**（默认即 1） | `fused_gr.cu:1722` "the latency-hidden norm/up (**STRATA_GR_FAST**) with the K-split down"；`:853` 同义 |
| `STRATA_SPEC_GUMBEL=1` | **采样（temperature>0）+ coupled-draft 家族** | `coupled_draft.hpp:1` 头注 "COUPLED DRAFT SAMPLING"；`:14` "replaces the inverse-CDF pick on BOTH sides"；**贪心（top_k=1/temp=0）下是空操作** |
| `--prompt-cache-tail` | **`--prompt-cache` 且 `--prompt-cache-every > 0`** | help L207-208；我们默认 6 / 16384，满足 |
| `--expert-profile-save` | 目标目录须存在可写 | 已建 `/data/profiles/`（宿主 `/home/albus/strata166/data/profiles`） |

### 2.3 必须同口径测（否则互相盖）

| 组 | 成员 | 为什么 |
|---|---|---|
| verify window | `--spec N` / `--spec-min-p` / `--suffix-draft` / `--lookup-chain` / `--mtp-max-t` | 它们共同决定窗口能长到几（日志：`window up to 6`）。**调 `--spec-min-p` 前必须先钉死其余几个**，否则校准值会被别的旋钮盖掉 |
| VRAM 分配 | `--expert-cache` / `--kv` / `--kv-resident` / `--kv-grow` / `--prefill auto:N` | 同一块 VRAM；一次只能动一个 |
| 采样口径 | `temperature` / `top_k` / `top_p` / `STRATA_SPEC_GUMBEL` / `STRATA_SPEC_COUPLED` | GUMBEL 只在采样下有意义；W708 的 bench 用贪心 => **测不出来** |

### 2.4 明确互斥 / 违规

- `--no-pool` 与 `STRATA_PREFILL_CPU_SHARE`（一个砍池、一个用池）
- `--peer-device` 与 `--layer-split` / `--expert-cache-device1..3`（help 明写）
- `--mmap-experts` 与 `--resident-experts`（后者**包含**前者，是模式名不是并列开关）
- `--vram-elastic` 与 AMD（help 明写 NVIDIA）
- 另外：**`--expert-cache-per-layer` 不要在 PROFILE 策略下开**（我们是 `--expert-profile` 驱动、命中 94.6~96.4%，已优于该文档的 2.97%/21.4%）

### 2.5 建议的组合（协同）

| 组合 | 成员 | 为什么值得打包 |
|---|---|---|
| **K：校准包**（优先） | `--pcie-frac` + `--spec-min-p` + `--pool-workers` + `--adapt-every/swaps/decay` | `calibrate.py` 本身就是**联合**测（前两个二维扫描、后两组各自重启扫），比逐个 A/B 省得多；且它 `>MIN_GAIN` 才保留 |
| **L：长文复用包** | `--prompt-cache`(6) + `--prompt-cache-every`(16384) + `--prompt-cache-root`(2048，默认已开) + `--prompt-cache-tail` + `pin=N` + `--conversation-cache-mib` | 全服务"多轮长上下文复用"；但注意 RAM/VRAM 叠加，且 `pin=N` 是请求级 |
| **S：短 prompt 包** | `STRATA_PREFILL_CPU_SHARE=auto` + `--short-read N`(默认 64) | 只对 chunk<1024 生效（note：19~35%） |
| **D：解码包**（彼此独立、可叠加） | `STRATA_GR_SPLIT=1`（不依赖采样）+ `STRATA_SPEC_GUMBEL=1`（依赖采样）+ 校准后的 `--spec-min-p` / `--pcie-frac` | 先单测 GR_SPLIT，再在**采样口径**下测 GUMBEL |
| **V：容量包** | `--expert-cache` + `--kv k8v4`(已配) + `--kv-resident`/`--kv-grow` | 三者合起来才是"VRAM 分配最优" |

## 3. 批次 A 执行记录（走完整闭环，含一次被验证拦下的失败）

| 步 | 结果 |
|---|---|
| 收养 | `P20 --expert-profile-save /data/profiles/ud-iq4_xs-learned.bin`（**行为中性**：只写文件）+ `P11`（env 落进 config，使其自包含） |
| 生成 | `gen_config.py --write`；与现行 config 的差异 = **仅** 这两项（arg 次序已对齐，无噪声 diff） |
| **第 1 次部署：失败** | config 是 `root:root`，SSH 用户 `albus` -> `cp` 被拒；我又没断言 rc => 静默跳过。**但 `verify_config.py` 报 FAIL 拦住了**（新 flag `config=False started=False`） |
| 修正 | 改用 `sudo -n cp -a`，并给每一步加断言（md5 双端一致 / `grep -c` 新 flag = 1） |
| 第 2 次部署 | config md5 双端一致 `547d280c...`；`docker restart` -> 40 s 就绪 |
| **复验** | **PASS=13 FAIL=0**；锚定启动行 `2026-10-07 16:49:58 engine started: ... --expert-profile-save /data/profiles/ud-iq4_xs-learned.bin` |
| 备份 | `strata-ud-iq4_xs.json.bak_20261008_004826` / `.bak_20261008_004949` |

**教训（已写进机制）**：① 远端写盘一律 `sudo -n` 且**每步断言 rc/输出**；② 复验不是形式----它第一次就抓出了部署失败。

## 4. 校准（P24）的状态与硬约束

`tools/calibrate.py` 直接可跑（`python tools/calibrate.py <cfg>.json`），调 4 个硬件相关旋钮，
**只调解码**（"the prompt path streams every expert whatever these settings say"），且只保留 `>MIN_GAIN` 的改动。

**实测被挡**（第一次尝试，日志 `logs/_calib_402.log`）：

```
[strata] starting the engine: reading the model's weights ...
strata generate: cudaMalloc(1485606400) for the weight arena failed (out of memory):
                 568 MiB of 32752 MiB VRAM free on this GPU. The arena is allocated first,
                 before the KV and expert caches: another program (or an engine that is still exiting) holds the rest
CALIB_EXIT=1 / POST_RESTART_DONE
```

=> **calibrate 的自带引擎要独占显存**，生产容器占着 33.95 GB => 校准期间**必须先停生产容器**。
绕法（已写好，待窗口）：停 `strata166-402` -> 用**同镜像的临时容器**跑 calibrate（挂 `/weights:ro` + `/data` + kfd/dri）
-> 结束无条件 `docker start strata166-402`。**窗口约 10~15 分钟**，期间 `/v1/models` 不可用。

（wrapper 的"结束时强制重启"已验证有效：本次失败后 `POST_RESTART_DONE` 已执行。）

## 5. 产物

- 机制：`D:/strata166/params/PARAM_REGISTER.tsv` · `gen_config.py` · `verify_config.py` · `_mk_register.py`
- 记录：`params/_verify_baseline.txt`（基线 12/12）· `params/_batchA2.out.txt`（批次 A 全流程 + 13/13）
- 166：`/data/profiles/` · `logs/_calib_402.log` · config 备份两件
