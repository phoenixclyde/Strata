# W712 升级记录 ---- Strata v0.1.40.2 -> v0.1.40.4（gfx906 / MI50）

> 写于 2026-10-08 20:1x CST。上游 `Niko1221/Strata`。
> 本件 = **本波做了什么、怎么自证**；下一步方案见 `W712_PLAN.md`。
> 环境声明：本件所有现场读数均在 **Z0=off（省电档）** 下取得。
> 编码规范：本件 CR=0，且不含禁用码位（U+21D2 / 2192 / 2014 / 2013 / 2026 / 2265 / 2264 / 2260 / 2212 / 00D7）。

---

## 0 一页速览

| 项 | 值 |
|---|---|
| 触发 | 机主：上游今日又发新版，先升级到最新版 |
| 新版 | `v0.1.40.4`（2026-10-08 08:04 UTC 发布，即 16:04 CST） |
| 源码指纹 | `strata-src-0.1.40.4.zip` = 18,591,099 B / **sha256 `7d19b4d5cc8922d4e558f2cddec9a28b7595775ccfb4e6085b02287d95059300`**（本机与 166 两侧**各自下载、哈希相同**） |
| 补丁面 | 与 0.1.40.2 **完全相同**：H1~H4 上游已修（验证）、**H5 + H6 仍需打**。补丁器 `patch_gfx906_402.py`(v3) **一字未改**直接复用 |
| 新镜像 | `strata-gfx906:0.1.40.4` / ID `8f8f6e87e664` / 6.57 GB / 2026-10-08 20:09 CST |
| 引擎二进制 | `/src/build-906/strata` = 24,841,832 B / md5 `b0020081b8292d48c4a555c5f036081b`（0.1.40.2 为 24,862,088 B / `10cb60648180ca7463f51848bbd88a21`：**已变，符合预期**） |
| 新容器 | `strata166-404`（**已启动，现役**），参数与旧 -402 逐项一致 |
| 当前生产 | **`strata166-404`（0.1.40.4）**，2026-10-08 20:11:52 起服务；旧 `strata166-402`（0.1.40.2）`Exited (0)` 保留用于回滚 |
| 切换 | **已完成**：20:11:47 停 -402 -> 20:11:52 起 -404 -> 20:12:28 ready（**35 s**），脚本 `switch_404.sh` 自带 300 s 轮询与自动回滚 |
| 中性验证 | **已实测**（背靠背 A/B，见 §3）：冷预填 456.1 vs 457.6 tok/s（**-0.33%**）、温 TTFT 5.753 vs 5.853 s、`reused` 均为 16384 => **落在分辨力内，中性成立** |

---

## 1 上游近三版变更（0.1.40.1 -> 0.1.40.4）

| 版本 | 发布（UTC） | 主题 |
|---|---|---|
| v0.1.40.1 | 10-06 09:53 | 热修：0.1.40 的"思考里被引用的 tool_call 被误当真调用"、引擎重启期间挂起。**仅 python 侧**，引擎与 0.1.40 相同 |
| v0.1.40.2 | 10-07 12:13 | 大版：Intel Arc 官方支持、多卡 layer-split 预填最高 +60%、低内存 Linux 文件层 +20~42% 解码、长文档 `pin=N` 首答 48-149 s -> 0.35-0.55 s、`STRATA_PREFILL_CPU_SHARE`（短 prompt 19-35%）、`STRATA_SPEC_GUMBEL`、`STRATA_IO_PREFETCH`、`STRATA_STAGER_SLEEP`、`STRATA_MMVQ_IL`（2-4 token verify 窗口权重块只读一次，默认开）等 |
| **v0.1.40.3** | 10-07 18:01 | 热修：Intel Arc 安装与 A 系、**Windows AMD 16 GB+ 显存下限**（#1376）、**Windows HIP 运行时 DLL 闭包**（#461）、#1244 Docker/K8s config 链接、MTP router 512 专家门（#1357）、tokenizer 加固（#1385） |
| **v0.1.40.4** | 10-08 08:04 | 热修：**Pascal(sm_61) 解码恢复 0.1.40 速度**（#1469/#1470）。官方原文：修复**只作用于 sm_70 以下**；Volta 及更新（RTX 20/30/40/50）编译产物与 0.1.40.3 **逐字节相同** |

### 1.1 这三版里**与我们（gfx906 / Linux / HIP / 单卡）有关**的部分

全树逐文件比对（pristine zip 对 pristine zip，2,260 -> 2,262 文件）：

- **变化 34 个文件，新增 2 个**（`tools/hip/dll_closure.py`、`tools/test_dll_closure.py`，均为 Windows 打包用）。
- 与我们可能相关的三处，逐条判过：

| 文件 | 改动 | 对 gfx906 的判定 |
|---|---|---|
| `include/strata/kernels/pdl.hpp` | `STRATA_PDL_RESTRICT` 拆出 Pascal 分支：`#elif defined(__CUDA_ARCH__) && (__CUDA_ARCH__ < 700)` 才用 `__restrict__`；否则为空。`kPdlPrefetch` 同样加 Pascal 分支 | **HIP 分支一字未动**（`#if defined(__HIPCC__)` 仍为 `__restrict__`，`kPdlPrefetch` 仍为 false）。HIP 编译**不命中** `__CUDA_ARCH__` 分支 |
| `src/kernels/cuda/native_bf16.cu`、`native_mmvq.cu` | 把 `__restrict__` 从 kernel **签名**挪进**函数体**局部声明（为绕开 MSVC/宿主 stub 的签名一致性） | HIP 下 `STRATA_PDL_RESTRICT` 展开仍为 `__restrict__`，**语义等价**（限定仍在函数体内生效） |
| `src/core/mtp.cpp` | per-token router 调用加门：`native_router_enabled() && g.n_expert == 512 && K == 10`（#1357） | 本机模型 = **512 专家 / top-10** => 门恒成立，**行为中性** |

- 与我们**无关**的：`src/program/generate.cpp` 的 Windows WDDM 显存下限（`_WIN32 && STRATA_USE_HIP` 才编）、Windows HIP 运行时诊断、Linux `/dev/kfd` 权限提示、`docker-entrypoint.sh` 的 `CONFIG=`（我们不走 entrypoint，容器是直起 `serve/server.py`）、Intel/SYCL 全部分支、`setup.py`（我们用 Dockerfile 手工构建，不跑 setup）。

**=> 结论（源码级判定，非推测）：0.1.40.2 -> 0.1.40.4 对 gfx906 的预期影响为中性。**
本升级的收益是"对齐上游 + 消除分叉"（补丁面不扩大、不带历史包袱），**不是性能收益**。
这一点必须写进结论，避免日后拿"升级了"当性能解释。
上面是**源码级预测**；**实测复核**见 §3（背靠背 A/B，实测差 -0.33%，中性成立）。

---

## 2 本波升级实施（六步，逐步自证）

### 步骤 1：源码取证（本机）
- 经 `gh-proxy.com` 下载 `v0.1.40.4` 与 `v0.1.40.3` 源码 zip；
- 落盘 `deploy/transfer/strata-src-0.1.40.4.zip`，sha256 `7d19b4d5...9300`；
- 与 166 侧**各自独立下载**的同一文件哈希相同（见步骤 3）=> 两侧编的是同一棵树。

### 步骤 2：补丁面复核（本机，dry-run 对 pristine 树）
对**未打补丁的 0.1.40.4 源树**跑 `patch_gfx906_402.py --root <dry404>`：

```
=== 汇总  patched=2  verified=4  not_applicable=0  failed=0 ===
   patched  : CMakeLists.txt :: H5 CUDA 分支 q6_k 实例门 加 OR STRATA_HIP_GFX906
   patched  : include/strata/platform/hip_compat/strata_hip.h :: H6 补 cudaEventBlockingSync 映射
   verified : strata_hip.h H1 / fused_gr.cu H2 / mtp.cpp H3 / vmm.cpp H4
PATCH_V3_OK
```
第二遍 => `patched=0 / verified=6`（**幂等**）。
关键事实：`strata_hip.h` 在 0.1.40.4 里**仍缺** `cudaEventBlockingSync`（H6 未修）；
`CMakeLists.txt` 的 q6_k 门**回到** `if(STRATA_Q6K_EXPERTS)`（H5 未修，且注释里删掉了 gfx906 那句）
=> **补丁面与 0.1.40.2 完全相同，仍是 2 处**。

### 步骤 3：166 侧构建上下文
- 新建 `/home/albus/strata166/build-ctx-404/`；
- 166 **自行下载**源码 zip（gh-proxy 直连），`sha256sum` = `7d19b4d5...9300`（与本机一致）；
- 复用 `llama.cpp-3cf0325.tar.gz`：`setup.py` 的 `LLAMA_CPP_COMMIT` = `3cf03257f219afbe7334045ff7c6a06ac68c627d`，**与 0.1.40.1 / 0.1.40.2 相同** => 不必重下；
- 推送 `Dockerfile-0.1.40.4` 与补丁器（补丁器文件**未改一字**）。

### 步骤 4：镜像构建
- Dockerfile 与 0.1.40.2 版的差异只有三处：源码 zip 换名、**镜像内 `sha256sum -c` 校验源码**（fail-closed）、注释与版本号；
- 复核 grep 六条（H1/H6/H2/H3/H4/H5）**全中，不中即构建失败**；
- 构建日志实测：`[132/139] mmq-instance-q6_k.cu.o` **被编进去**（这正是 H5 的作用：q6_k 的 MMQ 实例），`[133/139] Linking libstrata_mmq.a`，最终 `naming to docker.io/library/strata-gfx906:0.1.40.4`;
- 镜像内自证：`project(strata VERSION 0.1.40.4)`；`grep -c "cudaEventBlockingSync hipEventBlockingSync"` = **1**（H6 已生效）；`grep -n "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906"` 命中行 1270（H5 已生效）。

### 步骤 5：建容器（不改生产）
`strata166-404` 用 `docker create`（**不 start**，端口 8090 仍由 -402 占用），参数从 -402 逐项抄：

| 项 | 值（与 -402 一致） |
|---|---|
| binds | `/home/albus/strata166/data:/data`、`/home/albus/strata166/weights:/weights:ro` |
| devices | `/dev/kfd`、`/dev/dri`，`--group-add video` |
| 其它 | `--ipc=host`、`--ulimit memlock=-1`、`-e HSA_OVERRIDE_GFX_VERSION=9.0.6` |
| 端口 | `8090:8090` |
| 重启 | `unless-stopped`（Docker 原生 policy，**不用 systemd**） |
| Cmd | `bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-ud-iq4_xs.json --port 8090'` |

### 步骤 6：复验（**已执行，全部通过**）
切换后跑的四项，与 0.1.40.2 时同口径，**全部通过**：
1. `/v1/models` = 200，`status.value = loaded`，`meta.n_ctx = 262144`；
2. `docker exec` 读 `/proc` 引擎子进程 cmdline，三项现役参数均在：`--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192`；
3. `python deploy/params/verify_config.py` => rc=0 / **PASS=15 FAIL=0 SKIP=1**（锚定启动行已换成新的 `2026-10-08 12:11:53 engine started`）；
4. 生产 config 未变：md5 仍为 `d2b10f0c4e8293ba010614c7acc70bea`（本波**没有**改任何参数）。
另：`/v1/chat/completions` 冒烟 200（prompt 54 tok / 16 tok 出，1.6 s）。

---

## 3 中性验证：背靠背 A/B（**实测，不是推算**）

**做法**：同一探针 `bench_prefix.py 400`（约 18,084 token，3 个 chunk）、同参数、同一天、Z0=off，
两版**背靠背**各跑 2 组（COLD + WARM），中间只做一次容器切换。

| 指标 | **0.1.40.4**（-404） | **0.1.40.2**（-402） | 差 |
|---|---|---|---|
| COLD prefill（引擎日志） | **456.1 tok/s**（18,084 tok / 39,648 ms） | **457.6 tok/s**（18,084 tok / 39,520 ms） | **-0.33%** |
| COLD TTFT（探针，两次） | 40.16 / 39.81 s | 40.33 / 39.69 s | 中位 40.16 vs 40.33 s |
| WARM TTFT（探针，两次） | **5.753 / 5.735 s** | 5.853 / 5.772 s | 中位 **-1.7%** |
| WARM 前缀复用 `reused` | **16384 / 16384** | **16384 / 16384** | 一致 |
| WARM 读入量 | 1711 tok in 5,576 ms（306.9 tok/s） | 1711 tok in 5,683 ms（301.1 tok/s） | -0.3% |
| MTP draft 接受（COLD 15/17 与 WARM 19/24 各一） | 14/17、19/24 | 14/25、19/22 | 同量级 |
| 常驻专家 RAM | 33.45 GiB | 33.45 GiB | 一致 |
| 解码专家缓存命中 | 93.8-96.7% | 93.0-96.8% | 一致 |

**判据**：本机分辨力 **预填 1.2-1.7%**。**样本量声明（2026-10-08 审计 F8）**：本次每臂仅 **2 组**，低于本项目自己「亚分辨力效应须 >=5 轮/臂」的口径，故本条只判「**差值小于分辨力**」（这是 n=2 足以支持的部分），**不判**「两版完全等价」。实测差 **-0.33%**（冷预填）、-1.7%（温 TTFT，
其绝对差仅 0.1 s 且两版区间重叠）=> **两版在分辨力内不可分辨，源码级"中性"预测成立**。

**注意（别混用读数）**：§3 那次 A/B 的生成只有 32 token，**不足以**当解码基准。
0.1.40.4 的**解码**基准已按历史同口径补测（A2，2026-10-08 21:1x）：

| 项 | 0.1.40.4（本次实测） | 历史（0.1.40.1 时代） |
|---|---|---|
| 解码（512 token x 3，temp 0 / top_k 1，预热 2 条） | 引擎行 **45.7 / 43.3 tok/s**（探针口径 37.27 / 46.02 / 43.53，中位 **43.53**） | 42.9 tok/s |
| MTP draft 接受 | **208/292（71.2%）、204/285（71.6%）** | 61-66% |
| 解码专家缓存命中 | 95.1-96.9% | - |

**判据**：解码分辨力 **9.5-15%**。本次相对历史差 **+1% ~ +6.5%**（且 prompt 长度不同，历史是 18k prompt、本次是 73-token prompt）
=> **落在分辨力内，记"未见差异"**，不宣称提速。MTP 接受率更高（71% vs 61-66%）属**短 prompt 的 draft 动态**，
与 18k prompt 不可直接比，故同样只作记录、不当结论。

### 3.1 切换与回滚凭据
- 切换脚本：`deploy/scripts/_w712_switch_404.sh`（166 上 `/home/albus/strata166/w712/switch_404.sh`，
  本机 md5 = 远端 md5 = `0d68c90ef526558f1945f01f4fd9cc1c`，CR=0，`bash -n` 通过）。
- 切换日志：`/home/albus/strata166/w712/switch_404.log`。
- 回滚：`docker stop -t 30 strata166-404 && docker start strata166-402`（一条命令，随时可用）。
- 旧容器 `strata166-402`（0.1.40.2）停得**干净**（`Exited (0)`，非 137）；`-401` / `strata166` 仍保留。

### 3.2 B1：`--prompt-cache-every` 的三档边界（实测矩阵，2026-10-08 21:06-21:24）

单变量三臂（每臂独立 restart，臂内三档长度，探针 `bench_prefix.py`，Z0=off，档内 2 轮）：

| 档（实测 token） | **A: 8192（现役）** | **B: 16384（旧默认）** | **C: 32768（候选）** |
|---|---|---|---|
| **<8k**（4,589 / 4,600） | COLD 10.83 -> WARM **10.472 s**，`reused=0` | 10.87 -> **10.496 s**，`0` | 10.88 -> **10.464 s**，`0` |
| **8-16k**（9,989 / 10,000） | 23.10 -> **5.866 s（-74.6%）**，`reused=**8192**` | 23.10 -> **23.066 s（-0.1%）**，`0` | 23.11 -> **23.147 s（-0.1%）**，`0` |
| **>16k**（23,939 / 23,950） | 50.10 -> **16.990 s（-66.1%）**，`reused=**16384**` | 49.98 -> **16.989 s**，`16384` | 49.99 -> **50.181 s（-0.4%）**，`0` |

**9 个格子全部与机制预测吻合**（每臂还断言了容器 `/proc` 里的实际值 = 该臂的值）。三条结论：

1. **`<8k`：三臂都 `reused=0`**，温 TTFT 与冷几乎相同（10.46~10.50 vs 10.83~10.88 s）。
   **换任何值都救不了**  -  整条 prompt 不足一个 chunk，没有可对齐的边界。
   （日志显示该档确实建了 `1 checkpoints`，但**对齐要求**才是决定性的：边界须是 chunk 的整数倍。）
   => 现实含义：**短会话（工具调用往返）每轮都整条重预填**，4.6k prompt 约 10.4 s。
2. **`8-16k`：这是 8192 唯一的、也是决定性的价值域  -  温 TTFT 5.87 s 对 23.07 s（3.9 倍）**。
   臂 B/C 的 `reused=0` 把 W709 的单侧推断变成了**双向实测**。
3. **`>16k`：8192 与 16384 等效（both `reused=16384`），32768 反而归零（温 TTFT 50.18 s，≈ 冷 49.99 s）**
   => **"值越大越好"不成立**：checkpoint 落在 prompt 之外就一个都拿不到。
   结论：**8192 是在三档上都不劣的唯一档位**，P34 的 ADOPTED 值不动。

**收尾自证**：`params/generated` 的生产 config 已无条件拷回 LIVE（md5 仍 `d2b10f0c...bea`），
`verify_config.py` = **PASS=15 / FAIL=0 / SKIP=1**（P34 PASS，锚定恢复后的启动行 `2026-10-08 13:23:50`）；
register 的 **值/状态一字未动**，只把 B1 结论写进 P34 的 evidence/verdict
（md5 `a91b677e...` -> `3bf819e3ccd3f54ed454154b14c3eb3f`，仍 **35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7**，已同步 166）。
重新 `gen_config.py --write` 后生产 config **逐字节未变**（`identical = True`），即"改 register 未影响生产参数"。

### 3.3 B1 派生的新假设（B1b，**尚未测**）：把 prefill chunk 调小，可能让短会话也吃上复用

工具链事实（现役镜像内 `strata --help` 实读）：
`--prefill CHUNK` **接受显式尺寸**（"batched prompt processing in chunks of CHUNK tokens"；`auto` = 不超过 8192）；
`--prompt-cache N` = "keep N conversation checkpoints between requests (default 6, ~118 MB of RAM each)"。

**假设**：`<8k` 档为零是因为 chunk=8192 而 prompt 不足一个 chunk。
若把 chunk 降到 4096（并令 `--prompt-cache-every 4096` 与之对齐），4.6k prompt 就存在 4096 边界
=> 可复用 4096/4600（约 89%），温 TTFT 有望从 10.4 s 降到约 1.3 s。

**为什么值得做**：它打的是本项目最日常的场景（WorkBuddy 短会话），量级是"每轮 10.4 s -> 1.3 s"。
**代价与风险**（必须一起测，不能只看收益）：
① 小 chunk 可能降低**长 prompt 的预填吞吐**（W709 只测过**调大**到 16384 无收益，**调小从未测**）；
② checkpoint 尺寸/数量随 chunk 变化，RAM 账要重算；③ 需与 `--prompt-cache-every` 成对改，属**两变量**，须拆成两次单变量 A/B。
**判据**：机制量 `reused`（4.6k 档应出现 4096）+ 温 TTFT；另在 23.9k 档复核预填 tok/s 未退化超过分辨力（1.2-1.7%）。

---

## 4 本波没有做的事（边界声明）

- **没有改任何参数**：register 的**值/状态一字未动**；§3.2 收口时把 B1 的边界结论写进了 P34 的 evidence/verdict（md5 `a91b677e...` -> `3bf819e3ccd3f54ed454154b14c3eb3f`，仍 35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7；重新 `gen_config --write` 后生产 config **逐字节未变**）。
- **没有删任何东西**：四个镜像、四个容器全在（含回滚用的 -401 / `strata166` / -402）。
- **没有跑解码基准**：本波是构建 + 升级波，不是参数波；中性验证只覆盖**冷预填 / 温 TTFT / 前缀复用 / 缓存命中**四类口径（见 §3）。

---

## 4 产物索引

| 类别 | 路径 |
|---|---|
| 本件 | `deploy/W712_UPGRADE.md` |
| 方案 | `deploy/W712_PLAN.md` |
| 新 Dockerfile | `deploy/docker/Dockerfile-0.1.40.4` |
| 补丁器（复用，未改） | `deploy/docker/patch_gfx906_402.py` |
| 源码包 | `deploy/transfer/strata-src-0.1.40.4.zip`（+ 0.1.40.3） |
| 全树比对 | `deploy/tmp/_w712_tree_diff.txt`（34 改 + 2 增） |
| 补丁面 diff | `deploy/tmp/_w712_diff_402_404.txt` |
| 内核级 diff | `deploy/tmp/_w712_kernel_diff.txt` |
| 补丁器 dry-run | `deploy/tmp/_w712_dryrun404.txt` |
| 166 侧日志 | `deploy/tmp/_w712_probe166.out.txt`、`_w712_prep166.out.txt`、`_w712_build166.out.txt`、`_w712_image404.out.txt` |
| 切换脚本（本机原件） | `deploy/scripts/_w712_switch_404.sh`（md5 `0d68c90ef526558f1945f01f4fd9cc1c`） |
| 切换日志（166） | `/home/albus/strata166/w712/switch_404.log` |
| 切换实录 | `deploy/tmp/_w712_switch.out.txt` |
| 复验输出 | `deploy/tmp/_verify_20261008_2012.out.txt`（PASS=15 / FAIL=0） |
| **中性 A/B 原始输出** | `deploy/tmp/_w712_neutral_ab.out.txt`（两臂各 2 组 COLD+WARM + 引擎日志行） |
| 166 构建日志 | `/home/albus/strata166/build-ctx-404/build-404.log` |
| 波形脚本 | `waves/_w712_*.py` |

---

## 5 本波落盘与自伤记录（含一次真实的操作事故，按 W709 §7 的口径自报）

| # | 事项 | 处置 |
|---|---|---|
| 1 | **自伤：把含反引号的文本经 Bash + `python -c` 传递** -> shell 先做命令替换，`workbuddy-strata166.md` 追加上去的 §九 **丢掉了所有被抓的内容**（只剩标点）。这正是本机长期缺陷清单里第 3 条，**我自己又踩了一次** | 已用 Write 落盘脚本重写该节，并在同一脚本里做全文码位清洗（见 #2）。**教训：任何含反引号/$() 的落盘文本一律走 Write 工具，绝不走 shell** |
| 2 | `deploy/configs/workbuddy-strata166.md` 全文**存量**禁用码位 **14 处**（U+2014 x4、U+2192 x7、U+2264 x2、U+2212 x1） | 已清 14 处，md5 `bfb850d583a6...` -> `2817e4d4cfda...`，改后 **CR=0 / BAN=0**；替换台账：U+2014x2->` - `、U+2192->`->`、U+2264->`<=`、U+2212->`-`（**只动标点，不动数字与结论**） |
| 3 | 本次新建的 `Dockerfile-0.1.40.4` 自带 5 处禁用码位（沿用了旧 Dockerfile 的写法） | 已清（**仅注释**，`RUN/COPY/ARG/FROM/ENV/WORKDIR/CMD` 共 17 行**一字未动**），md5 `5767 B` -> `5759 B` / `7931c4764530613f3da17cda474e7e6d`，并**重新推到 166** 保持两侧逐字节一致；166 侧 `diff` 实证差异只在那 3 行注释 |
| 4 | **存量未清（报出，不动）**：`deploy/docker/Dockerfile-0.1.40.2`（6 处）、`deploy/docker/patch_gfx906_402.py`（14 处） | 二者是**本次构建的输入件**（patcher 一字未改地跑过构建），按 W709 §7「前波存量单独报出、不篡改」的口径**保持原样**；若要清，是一次独立的小改（只动注释/docstring/提示串），需重跑 dry-run 自证 |

**自证判据**（与 W709 §7 同口径）：
1. 改后文件 **CR=0** 且**无禁用码位**（脚本实测打印，见产物索引）；
2. 只改**标点**：数字、路径、命令、结论字符串逐条人工比对（#2 的替换表逐项列出；#3 由 `diff` 给出 3 行注释差异）；
3. 需要跨机一致的件（Dockerfile）**两侧 md5 相等**（`7931c4764530613f3da17cda474e7e6d`）。
