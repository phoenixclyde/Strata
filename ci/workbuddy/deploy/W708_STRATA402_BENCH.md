# W708 -- Strata v0.1.40.2 三臂 bench + 官方 release note 逐条核对 + 构建修复 PR

> 时刻：2026-10-08 00:10~00:35 CST ｜ 机器：166（1 x MI50 32GB gfx906 + 128 GB RAM）
> 本文已并入 W708b 对抗性审计的 13 条裁定（见 §8）。

## 1. 方法与协议

三臂 **ABBA**（主臂在首尾各测一次，用来判"臂间差异"是否只是漂移）：

| 臂 | 容器 | 镜像 | 引擎 |
|---|---|---|---|
| A | `strata166-402` | `strata-gfx906:0.1.40.2` | **0.1.40.2** |
| B | `strata166-401` | `strata-gfx906:0.1.40.1` | 0.1.40.1（热修版） |
| C | `strata166-402` | `strata-gfx906:0.1.40.2` | 0.1.40.2（复测） |

配置 `=/data/strata-ud-iq4_xs.json`（三臂**同一份**）：UD-IQ4_XS / `--max-context 262144` / `--kv k8v4` /
`--spec 4 --spec-min-p 0.5` / `--mtp /data/mtp/rt` / `--resident-budget-gib 76` / `--prefill auto` / `--expert-cache auto`。

测量协议（与既有版本对拍同协议，保证可比）：**预热 1 条丢弃** + **冷预填 18,089 token x3**（每轮带不同 salt，强制冷）
+ **解码 512 token x3**（`temperature 0 / top_k 1 / top_p 1`）。取中位与极差。

**[!] 一处口径必须写明**：三臂**引擎版本不同**，但**启动路径也不同** ---- A/C 由容器自带 `Cmd` 起（`serve` 是 PID 1），
B 由 `docker exec -d ... setsid nohup` 起（`serve` 非 PID 1）。就绪时间差（B 45 s vs A/C 30 s）即由此而来。
对吞吐**大概率无实质影响**，但"唯一变量"这句严格讲**不成立**，应读作"唯一**有意的**变量 = 引擎版本"。

## 2. 读数

### 2.1 主表（HTTP 侧计时）

| 臂 | 预填中位 (min~max) | 预填极差 | 解码中位 (min~max) | 解码极差 |
|---|---|---|---|---|
| **A 0.1.40.2** | **455.8** (451.3~457.9) | 1.4% | **44.10** (39.55~45.27) | 13.0% |
| B 0.1.40.1 | 456.4 (450.8~456.9) | 1.4% | 43.80 (39.89~44.95) | 11.6% |
| C 0.1.40.2-again | 456.0 (450.7~456.7) | 1.3% | 43.04 (39.94~45.28) | 12.4% |

**A vs B**：预填 **-0.13%**、解码 **+0.68%**（(44.10-43.80)/43.80）。
**C vs B**：预填 **-0.09%**、解码 **-1.74%**（(43.04-43.80)/43.80）。
**A vs C**（同为 0.1.40.2）：预填 **-0.04%**、解码 **+2.5%**。

=> **臂间差的绝对值 <=1.74%**，而**同臂内自身极差 11.6~13.0%** => 臂内极差约为**最小**臂间差（0.68%）的 **约 6.7 倍**以上。
=> **本机在本配置下，0.1.40.2 与 0.1.40.1 无分辨率内的性能差异。**

### 2.2 引擎日志逐条（`strata-ud-iq4_xs.log`，可复算）

**[!] 该日志是 append 的，跨多次启动/多份配置**，且**没有 per-arm 标记**；下面的"按臂切分"依据是**请求发生顺序**
（每臂 7 条：warm + prefill x3 + decode x3），并与 HTTP 侧逐条对齐（数值吻合）后才成立。

| 臂 | 请求 | 预填 tok/s | 解码 tok/s | MTP 接受 |
|---|---|---|---|---|
| A | warm 59 | 50.4 | 29.5 | 10/12 = 83% |
| A | pre1/2/3 | 453.4 / 459.8 / 457.8 | 32.4 / 38.3 / 44.5 | 29/40, 29/41, 29/41 |
| A | dec1/2/3 | -- | 39.5 / 45.2 / 44.1 | **278/434=64.1%, 283/440=64.3%, 277/451=61.4%** |
| B | warm 59 | 49.4 | 29.7 | 10/12 |
| B | pre1/2/3 | 452.7 / 458.9 / 458.3 | 29.5 / 36.7 / 45.2 | 29/51, 31/47, 30/39 |
| B | dec1/2/3 | -- | 39.9 / 44.9 / 43.8 | **289/443=65.2%, 284/433=65.6%, 272/445=61.1%** |
| C | warm 59 | 51.5 | 29.5 | 10/12 |
| C | pre1/2/3 | 452.7 / 458.2 / 458.6 | 29.0 / 42.3 / 44.4 | 28/47, 30/39, 30/41 |
| C | dec1/2/3 | -- | 39.9 / 43.0 / 45.2 | **285/439=64.9%, 277/447=62.0%, 281/406=69.2%** |

**[!] "两路对照"的适用范围**：**预填**两路是真独立（HTTP 451.3/457.9/455.8 vs 日志 453.4/459.8/457.8，差约 0.4%，含排队/网络）；
**解码**两路**同源**（HTTP 的 decode 就是从同一 wall time 算的，日志 `512 generated in 12946 ms` = 512/12.946 = 39.55），
因此解码的"两路一致"**不构成独立验证**。

### 2.3 资源与启动

| 项 | 值 |
|---|---|
| 启动就绪 | A 30 s / B 45 s / C 30 s |
| 解码专家缓存命中 | **94.6~96.4%**（这 3 条取自日志末尾 = **C 臂**的三次解码，非 A 臂） |
| 跨 PCIe 取专家 | 0.7~1.1% |
| RAM 侧驻留专家 | **32.24 ~ 33.45 GiB**（两值出自不同启动块，见 §3 注） |
| VRAM 占用 | 33,950,179,328 B |
| GPU 专家缓存槽位 | 10,289 槽 / 23.19 GiB（该行出自较早一次 `int8`/131072 启动块） |
| 异常 | 0 / 0 / 0 |

## 3. 结论：为什么"官方说快了，这里测不出来"

**主论证（与内核是否命中无关，最硬）**：官方在**本机同形态**（单卡、非低 RAM 场景、默认配置）给出的默认增益量级是
**解码 +1.7~4.3%**（RTX 3060 +1.7/+4.3、RTX 5070 +3.9、P100 +3.7/+2.5）。而本机**解码臂内自身极差就有 11.6~13.0%**
=> **官方那些增益低于本机的分辨力**，测不出来是预期结果，不是测量失败。

**次要论证（逐条排除，均为"不适用"而非"没测到"）**：

| 官方项 | 本机是否适用 | 依据 |
|---|---|---|
| 多卡 layer-split 预填 +60% | 否（单卡） | 需 >=2 GPU |
| 低 RAM / 文件层 解码 +20~42% | 否 | 该项前提是"RAM < 模型"；本机 RAM 侧驻留 32.24~33.45 GiB 专家、解码专家缓存命中 94.6~96.4%、跨 PCIe 0.7~1.1% |
| `pin=N` 长文档 | 否（opt-in，未启） | 未设 |
| `STRATA_SPEC_GUMBEL=1` | 否（opt-in，未启） | 未设 |
| RX 7900 XTX hipBLASLt 表 | 否 | gfx906 无 hipBLASLt |
| `STRATA_MMVQ_IL` | **未验证** | 官方只写 "on by default, RTX 30 series and newer"；源码 `src/core/verify.cpp:73` 的 `g_mmvq_il()` **默认 true 且无 arch 门**，是否真的走该内核取决于运行时 `native_mmvq_il_supported()`（`:917`）。**本机是否命中未验，故不作为解释依据** |

**[!] "专家全常驻"----W708c 已补到直证（审计判"证据不足"是因为我引用不全）**：
取**当前这次**启动块（`strata-ud-iq4_xs.log` 的"最后一次 `engine started`"之后），原文是

```
strata generate: profile /src/data/expert-profile.bin: 24576 ranked pairs, built for 24576 slots
strata generate: expert cache 9758 slots, 21.98 GiB of VRAM; policy is ... PROFILE, ranked by routing frequency, no eviction.
FileExpertSource: RAM budget 76.00 GiB: 14818 of the 33.45 GiB of experts the GPU cache does not hold, by profile rank
FileExpertSource: mapped pinned cache complement ready: resident 33.45 GiB, pinned 33.45 GiB in 20 s
strata generate: resident RAM mode: 33.45 GiB of experts in RAM (page-locked), 9758 in the GPU cache;
                 adaptive swaps exchange them with the GPU cache (no file reads)
```

=> **9758（GPU 缓存）+ 14818（RAM 补集）= 24576 = 全量槽位**，且引擎自述 "no file reads"。
即 **"全部专家常驻（GPU 缓存 + page-locked RAM 互补）"成立，且有算式级直证**。
我原先只引了 `resident RAM: 33.45 GiB` 一行（它在日志里跨多个启动块反复出现），
**教训：引用启动期读数必须锚到"最后一次 `engine started` 之后的块"**。

## 4. 官方 release note 逐条核对

落盘：`D:/strata166/upstream/relnotes/v0.1.40.2.md`（8399 B）· `v0.1.40.1.md`（3818 B）· `v0.1.40.md`（13101 B）

| # | 说法 | 官方原文 | 核对 | 本机适用 |
|---|---|---|---|---|
| 1 | 常规解码 +1.7~4.3%（RTX 30/50、P100） | 表：RTX3060 +1.7%(story)/+4.3%(code)、RTX5070 +3.9%、P100 +3.7%/+2.5%（10/10 pairs） | **一致** | 否（非 RTX；且量级低于本机分辨力） |
| 2 | 多卡 layer-split 预填最高 +60% | "Multi-GPU layer split: up to +60% prompt speed"；4x R9700 32K 2,797 tok/s，3 卡 1,970 -> 2,458 | **一致** | 否（单卡） |
| 3 | Linux 内存不够模型大：解码 +20~42%（文件层走 page cache） | "+20 to +42% decode (#1194)"；P100 32GB 限额 12.6 -> 15.2 / 9.3 -> 13.3 | **一致** | **否（非低 RAM 形态）** |
| 4 | `pin=N` 长文档连问：首答 48~149 s -> 0.35~0.55 s | "first answer in 0.35-0.55 s instead of 48-149 s (opt-in `pin=N`)" | **一致** | 否（opt-in，未启） |
| 5a | AMD opt-in `STRATA_SPEC_GUMBEL=1` 解码 +5.7~9% | "Gumbel-max coupled drafts (`STRATA_SPEC_GUMBEL=1`, +5.7 to +9% decode on AMD in the reporters' runs; on an RTX 3060 ... within noise)" | **一致** | 否（opt-in，未启；原话限定 "in the reporters' runs"） |
| 5b | RX 7900 XTX 小 chunk hipBLASLt 表 +32% 预填 | "RX 7900 XTX hipBLASLt table rows for small prompt chunks (+32% prompt, measured by the author, #1289)" | **一致** | 否（gfx906 无 hipBLASLt） |
| 6 | **新收编**一个 gfx906 专属 opt-in `STRATA_GR_SPLIT=1` | **release note 全文无此字样**（8 版 note 全查：0 命中） | ⚠ **内容对、"新收编"不成立** | 见 §4.1 |

### 4.1 第 6 条更正（**本节已按 W708b 审计重写**）

`STRATA_GR_SPLIT` **不是 0.1.40.2 新增**，但两版之间该处**确有一处实质代码改动**（不是"只改注释"）。

**权威原文取自 release 源码 zip（不是本地解压树）**：

| 版本 | zip 内 `src/kernels/cuda/fused_gr.cu` | L1743 原文 |
|---|---|---|
| 0.1.39 | 67,305 B / md5 `729ff04592cdb05e77f464126449e9fa` | （无该构造） |
| **0.1.40.1** | 96,423 B / md5 `ab856a507f40708855d7b5c8d8ba894a` | **`        return;`**（裸 return，GR_SPLIT x3） |
| **0.1.40.2** | 96,522 B / md5 `640fe793e8a8bf9e3bd97184928fbd4c` | **`        return false;   // the gfx906 STRATA_GR_SPLIT read: no q8_1 (the caller quantizes), like the v3 path above`**（GR_SPLIT x4） |

- 两版 `fused_gr.cu` 的**全文差异只有这一行**（`grep "no q8_1 either"`：0.1.40.1 = **0**、0.1.40.2 = **0**）。
- => 这就是 **#1083 第 1 项（gfx906 分支裸 `return;` -> `return false;`）被上游采纳的**代码**修复**，
  注释措辞与我们 v2 写的不同。**这也是我们补丁器 v2 在该处锚点失配、必须改成"验证"模式的直接原因。**
- `docs/AMD_HIP.md` 的该表格行（0.1.40.1 L411 / 0.1.40.2 L461）**逐字相同**：
  "`gr_down_multi`, opt-in | split along K (8 rows x 5 slices of 2048), **~3% per window**; sums in another order
  than the single-token read, **so off by default** | `STRATA_GR_SPLIT=1`"。
  => "K-split down / 每 verify window ~3% / 默认关（求和次序不同）"三点全对；**"新"字不成立**。

**[!] 本节的取证教训（已记）**：我第一版用的是 `D:/strata166/tmp/src401` 与 `tmp/src401_pristine` ---- 这两棵树
**都已跑过我们的补丁器**（都含我们写的 `// no q8_1 either; ...`），于是"看起来只差注释"。
**凡判"两版本某文件差异"，必须取未被任何人改过的原始产物（此处 = release zip），并用 md5 自证。**

### 4.2 其它值得记的两条官方声明

- **"Default answers are byte-identical to 0.1.40 (checked on Q2_0, IQ3_XXS, Coder and IQ3_S)"**。
- **0.1.40.1 = 0.1.40 的引擎 + 纯 Python 热修**（其 note 原文："The engine is the same as in 0.1.40, so there is
  nothing new to download"）=> 本 A/B（0.1.40.2 vs 0.1.40.1）等价于与 0.1.40 的引擎差，与官方"against 0.1.40"口径同源。
  **[!] 这一条只有 note 自述，无二进制比对**（未取 401 内 `strata` 的 hash）---- 属旁证，不是直证。

## 5. 现场

- 容器：`strata166-402` running / `restart unless-stopped`；`strata166-401` 与 `strata166` 保持 `Exited`（可回滚）。
- 端口 8090 `/v1/models` 200；VRAM 33.95 GB；RAM used 42 / available 82 GB；磁盘 73%。
- **bench 这一段本身**只读 + 切容器，未改任何 git 对象；随后的 PR 是**独立的一步**（见 §6），不属 bench。

## 6. 构建修复 PR（与 bench 分开的一步）

**PR #1396** = `https://github.com/Niko1221/Strata/pull/1396`
base = `Niko1221:main` @ `e8ca9afd03d8`（= tag v0.1.40.2，两者同点）｜head = `phoenixclyde:gfx906-build-fixes-402` @ `87c6d0218d`
**2 files +3/-2 / 1 commit / state=open**：

| 文件 | 改动 |
|---|---|
| `CMakeLists.txt` | `if(STRATA_Q6K_EXPERTS)` -> `if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)`（+2/-2） |
| `include/strata/platform/hip_compat/strata_hip.h` | 加 `#define cudaEventBlockingSync hipEventBlockingSync`（+1/-0） |

**H5（q6_k 实例门）必要性的直证**（不是推测；原始输出 `D:/workbuddy/_z_rk81/_pr118.out.txt`）：

1. `libstrata_mmq.a` 内 `mul_mat_q_case<(ggml_type)14>` 恰有 **1 个 `U`（未定义引用）+ 1 个 `W`（弱定义）**。
2. 其它归档（engine/prefill/spec/kernels/core/kernels_cpu，共 **6 个**）该符号**定义数全 0**。
3. 把 `mmq-instance-q6_k.cu.o` 从归档移除后，用**原链接命令行**重链 => `link_rc=1`、**产物未生成**，
   报 `ld.lld: error: undefined symbol: void mul_mat_q_case<(ggml_type)14>(...)`；
   对照（原归档）=> `link_rc=0`、产物 **24,862,088 B**。

**[!] 两处口径要写清**：
- "定义在哪个 `.o`、`U` 引用来自哪个 `.o`" **本轮没有取到**（探针 `ar p ... | nm -` 那两段输出为空）。
  可说的只有：**归档级** U=1/W=1，以及**源码级** `src/prefill/moe_mmq.cu:219` 在 `__HIPCC__` 下调它。
  "`moe_mmq.cu.o` 引用了它"是**源码推理**，不是本轮观测。
- H6 那条：**`main` 上"0 次"这个说法必须限定文件** ---- `platform/hip_compat/strata_hip.h` 里 0 次；
  **wave32 头 `include/strata/hip_compat/cuda_runtime.h:39` 本来就有该映射**。另外 **open PR #1101 也往 wave32 头加了同一行**
  （`/pulls/1101/files`：`cuda_runtime.h +1/-0`）----**不同文件，与本 PR 不重叠**，但足以说明"上游完全没有该映射"是错的说法。

**[!] 幂等性缺口（已记）**：`_pr120_open.py` 在 `POST /pulls` 前**只断言了文件数与 ahead_by，没有查同 head 是否已有 PR**；
重复跑会开出重复 PR。下次要加 `/pulls?head=phoenixclyde:<branch>&state=all` 查重（W703 的做法）。

## 7. 产物

- 本报告：`D:/strata166/W708_STRATA402_BENCH.md`
- PR 正文：`D:/strata166/pr/PR_BODY.md`（4558 B / `2d88b07b050adcaa374fd1c2798b94d4`）
- 探针与原始输出：`D:/workbuddy/_z_rk81/` 下 `_pr108*`（现场）、`_pr109*`（三臂 bench）、`_pr113/117/118*`（H5 直证 v1/v2/v3，
  **只有 v3 有效**）、`_pr116*`（引擎日志逐条）、`_pr115*`（release note 落盘）、`_pr120*`（建 PR）、`remote/_h5v.sh`、`remote/_mkpr.sh`
- 官方 release note 全文：`D:/strata166/upstream/relnotes/v0.1.40*.md`

## 8. W708b 对抗性审计：13 条裁定与处置

派独立上下文只读子 agent（Explore）复核，结论：**主结论成立，但查出 1 条 P1 事实错误 + 1 条 P1 无证据 + 11 条 P2**。

| # | 级别 | 内容 | 处置 |
|---|---|---|---|
| 1 | **P1** | §4.1 原写"0.1.40.1 与 0.1.40.2 该段只差一行**注释**"，并引用了**不存在的**旧文本 `// no q8_1 either;` | ✅ **已改**：实际是 `return;` -> `return false;` 的**代码修复**；原文改用 release zip 取；教训入 §4.1 |
| 2 | **P1** | "`moe_mmq.cu.o` 对它有 `U` 引用"无原始支撑（归属探针输出为空） | ✅ **已改**：只保留归档级与源码级两条，并显式标注未取到归属 |
| 3 | P2 | "main 上 `#define cudaEventBlockingSync` 0 次"口径过宽（实为**单个文件**）；且 open PR #1101 也加了同一行（另一文件） | ✅ **已改**：§6 写明文件口径与 #1101 |
| 4 | P2 | 94.6~96.4% 命中率的臂归属错（实为 C 臂） | ✅ **已改**：§2.3 |
| 5 | P2 | "其它 7 个归档"实为 6 个 | ✅ **已改**：§6 |
| 6 | P2 | "专家全常驻"证据不足（无总量读数；且有 4820 次 blob read） | ✅ **W708c 补到直证**：§3 现给出算式 `9758 + 14818 = 24576` 与原文 "no file reads"；审计当时判"无证据"是因为**我引用不全** |
| 7 | P2 | "`MMVQ_IL` 在 AMD 不开"超出原文（note 只说 RTX 30+ 默认） | ✅ **已改**：§3 标为**未验证**，不作为解释依据 |
| 8 | P2 | 倍数"6~10 倍"上限无来源；"<1.8%" 系 1.74% 向上凑整 | ✅ **已改**：§2.1 给"约 6.7 倍以上"与精确 1.74% |
| 9 | P2 | A vs C 预填符号写反（+0.04% 应为 -0.04%） | ✅ **已改**：§2.1 |
| 10 | P2 | "唯一变量 = 引擎版本"不严（B 臂 serve 非 PID 1） | ✅ **已改**：§1 加口径说明 |
| 11 | P2 | 建 PR 无查重，不幂等 | ✅ **已记**：§6；本次未重复执行，无重复 PR |
| 12 | P2 | §5"未做任何额外变更（无 commit、无 push）"与 §6（已开 PR）表面冲突 | ✅ **已改**：§5 限定为"bench 这一段" |
| 13 | P2 | "引擎日志与 HTTP 两路互为对照"对**解码**不成立（同源） | ✅ **已改**：§2.2 标注适用范围 |

**审计确认成立、无需改的部分**：三臂中位读数与原始输出逐字一致；三臂各 7 条与日志逐条一致且 MTP 区间计算正确；
7 组官方引文在 `v0.1.40.2.md` 中逐字命中；`STRATA_GR_SPLIT` 的 x3/x4 与文档行逐字相同、8 篇 note 均 0 命中；
PR #1396 的 base/head/文件数/行数与 API 完全一致；H5 重链反证成立（`link_rc` 取的是**无管道**的普通 `$?`，口径可信 ----
给出错误 `link_rc=0` 的 v1 用的是 `${PIPESTATUS[0]}`，本报告**未引用 v1/v2**）。

**审计列出的"无法验证清单"**（本报告已按此收缩措辞）：401 镜像内二进制的 hash、"专家总量"、`MMVQ_IL` 的 AMD 命中、
`U` 引用的具体成员、append 日志"最后 21 条 = 三臂"的标记、0.1.40.1 引擎 == 0.1.40 引擎、PR 里"整树编译成功"的完整日志。
