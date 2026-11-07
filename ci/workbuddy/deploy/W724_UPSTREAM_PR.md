# W724 ---- 上游 PR 可行性 + 首选候选：gfx906 的宏判据漏判

- 日期：2026-10-09 20:1x（本机时间）
- 缘起：机主问「我们自己能改吗？做 PR？」
- **结论**：**能**（有先例：PR #1396 已并入 0.1.41）。但**首选候选不是 feature**，而是 W718 顺带挖出的
  **一个 1 行 bug** ---- `prefill.cpp:1839` 的 gfx906 宏判据漏判。**证据链极硬：上游自己在相隔 9 行处就写对了。**

---

## 1 上游收不收外部 PR：收，而且流程齐备

容器内 `/src` 实测：

| 件 | 内容 |
|---|---|
| `.github/pull_request_template.md` | Title / Issue / Summary / What changed / Extra Notes |
| `.github/ISSUE_TEMPLATE/` | `bug_report.yml` / `feature_request.yml` / `question.yml` / `config.yml` |
| `AGENTS.md` | **给贡献者（含 agent）的规矩**，见 §4 |
| `LICENSE` | 有 |

`AGENTS.md` 原文（关键三条）：

> - One change per pull request. Say what it changes and what it leaves alone.
> - A new feature is opt-in, and the default path stays byte-identical to the last release. Say how you checked.
> - Build every backend a file touches (CUDA, HIP, SYCL) before asking for review.
> - **A report from hardware the maintainers do not have is welcome.**

=> 最后一条正是我们的位置：**我们有 gfx906，维护者没有**。

---

## 2 首选候选：`prefill.cpp:1839` 的宏判据漏判（1 行）

### 2.1 现状源码（容器内 `src/prefill/prefill.cpp:1837-1850`）

```cpp
void Prefill::arm_cpu_share(bool applies, bool by_default) {
#if !defined(STRATA_USE_HIP)
    if (applies && by_default && cpu_share_explicit() == -2.0 && !g_share_default) {
        g_share_default = true;
        std::fprintf(stderr, "prefill: the CPU share is ON by default ... STRATA_PREFILL_CPU_SHARE=0 turns it off.\n");
    }
#else
    (void) by_default;
#endif
    if (applies && cpu_share_on()) g_stream_min_share = cpu_share_max();
}
```

### 2.2 bug：gfx906 构建**没有** `STRATA_USE_HIP`

`CMakeLists.txt:64-67` 原文：

> `option(STRATA_HIP_GFX906 "Build the CUDA targets for AMD gfx906 through HIP (wave64 compat layer)" OFF)`
> `if(STRATA_HIP_GFX906)` ... `message(FATAL_ERROR "STRATA_HIP_GFX906 and STRATA_ENABLE_HIP are separate backends; enable only one")`

上游**自己的注释**就承认了这件事（`src/core/expert_cache.cpp:5-6`）：

> `// the gfx906 compat build (PR #638), which compiles this file as HIP without STRATA_USE_HIP`
> `#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)`

=> gfx906 下 `STRATA_USE_HIP` **未定义** => `#if !defined(STRATA_USE_HIP)` **为真** => 走 CUDA 分支
=> `g_share_default = true` + 打印 banner => **CPU share 在 AMD gfx906 上默认开启**。

### 2.3 与官方声明不符

- 0.1.41 release note：**"AMD are as before"**；
- 源码注释（同段）：*"HIP stay off"*；
- 但实测**打印了** banner（`-407` 日志中出现 3 次，每次引擎启动一次）。

=> **行为与声明矛盾**，根因就是判据用了"是不是 HIP"来近似"是不是 AMD"，而 gfx906 是"HIP 编译但不带该宏"的第三种形态。

### 2.4 上游自己的正确写法就在手边（三重先例）

| 位置 | 原文 |
|---|---|
| `src/core/mtp.cpp:420` | `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)` （**同一函数内、相隔 9 行处**） |
| `src/core/device.cu:235` | `#if defined(STRATA_USE_HIP) \|\| defined(STRATA_HIP_GFX906)` |
| `src/core/expert_cache.cpp:6` | `#if defined(STRATA_USE_HIP) \|\| defined(STRATA_HIP_GFX906)` |

`mtp.cpp:419-428` 实测原文（**上游内部自相矛盾的最直接证据**）：

```cpp
#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)   // (HIP: the default priority)
    ... 设置流优先级 ...
#endif
    if (!prio && cudaStreamCreateWithFlags(&cs_, cudaStreamNonBlocking) != cudaSuccess) { ... }
#if !defined(STRATA_USE_HIP)                                   // <== 同一函数，紧邻，漏了 gfx906
    // HIP keeps the shared expert on cs_; only CUDA needs this branch stream.
```

---

## 3 改动与验证

### 3.1 改动（1 行）

```diff
--- a/src/prefill/prefill.cpp
+++ b/src/prefill/prefill.cpp
@@ -1837,7 +1837,7 @@ void Prefill::set_cpu_pool(kernels::cpu::ExpertPool* pool) { cpu_pool_ = pool; }
 void Prefill::arm_cpu_share(bool applies, bool by_default) {
-#if !defined(STRATA_USE_HIP)
+#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)
     if (applies && by_default && cpu_share_explicit() == -2.0 && !g_share_default) {
```

`prefill.cpp:272` 与 `:2590` 的两处 `#if defined(STRATA_USE_HIP)` **不动**（那是正向 HIP 判据，守的是
`STRATA_HIP_WMMA`（RDNA4 矩阵核）与 `STRATA_KV_HOST_DMA`，gfx906 是否该走需另证 ---- 按 AGENTS.md
"one change per pull request"，留给后续）。

### 3.2 我们已做的验证（gfx906，MI50 32GB，engine 0.1.41）

CLI 直跑引擎，4-token prompt（触发 `T < 1024`），两臂只差 `STRATA_PREFILL_CPU_SHARE`：

| | 臂 A（默认，误开） | 臂 B（`=0`） |
|---|---|---|
| 引擎原行 | `streamed 309 (295 by DMA, host 174.0 ms), resident 607, **on the CPU 197 (share 0.90)**` | `streamed 506 (492 by DMA, host 177.3 ms), resident 606, **on the CPU 0 (share 0.00)**` |
| 预填 | **928.3 ms** | **929.5 ms**（差 0.13%） |
| 输出 token | `271 248068 198 760` | `271 248068 198 760`（**逐 token 相同**） |

=> ① **机制确实在动**（197 个专家由 CPU 承担）=> 官方 "AMD are as before" 被证伪；
② 该例上**收益为零**（0.13%，远低于本机预填分辨力 1.2~1.7%）；③ banner 自称 "answers can differ
slightly from 0.1.40.3, mean KL ~0.004" => 有非零的答案扰动风险。

### 3.3 我们**没做**的（PR 里要照实说）

- **没有 CUDA 卡** => 无法按 AGENTS.md "build every backend" 编译验证 CUDA 后端。
  可给的替代证明：该改动对 CUDA **宏展开恒等**（`STRATA_HIP_GFX906` 在 CUDA 构建里未定义 => `!defined(...)`
  恒真 => 展开与修改前完全一致），可用 `gcc -E` 做预处理级对照。
- 未在 SYCL 后端验证（同型：SYCL 构建亦不定义 `STRATA_HIP_GFX906`，展开恒等）。

---

## 4 为什么这个 PR 值得提（价值判断）

1. **影响面**：gfx906 是一大类老卡（MI50 / MI60 / Radeon VII），它们会**默认开启一个零收益、且自称会
   微改答案的路径**；用户不会知道。
2. **行为与声明不符**：官方说 AMD 不变，实际变了 ---- 属**文档级 bug**，维护者应关心。
3. **改动极小、零风险**：1 行；对 CUDA/SYCL 展开恒等。
4. **有上游自己的先例**：不是"我认为应该这样"，而是"你在 `mtp.cpp:420` 就是这么写的"。
5. **我们有维护者没有的硬件**：AGENTS.md 明说欢迎。
6. **对我们自己也有价值**：修掉后，我方 config 的 `STRATA_PREFILL_CPU_SHARE=0`（P23 的显式覆盖）
   可以删掉，配置回到"官方默认"，少一处本地偏离。

---

## 5 PR 文案（按上游模板，可直接粘贴）

```markdown
## Title
gfx906 build: Prefill::arm_cpu_share() takes the CUDA branch (STRATA_HIP_GFX906 is not STRATA_USE_HIP)

Issue: (none opened yet - say if you'd rather have one first)

## Summary
On the AMD gfx906 compat build (`-DSTRATA_HIP_GFX906=1`, MI50 / MI60 / Radeon VII),
`Prefill::arm_cpu_share()` guards the "CPU share is ON by default" branch with
`#if !defined(STRATA_USE_HIP)`. That macro is *not* defined in the gfx906 build - as
`src/core/expert_cache.cpp:5` already says, it is "the gfx906 compat build (PR #638), which compiles
this file as HIP without STRATA_USE_HIP". So the branch is compiled in, the banner prints, and
`g_share_default` is set, while 0.1.41's notes say AMD is unchanged.

Add `&& !defined(STRATA_HIP_GFX906)` to match the guard already used at `mtp.cpp:420`,
`device.cu:235` and `expert_cache.cpp:6`. No other guard in this file is touched.

## What changed
- `src/prefill/prefill.cpp:1839`: `#if !defined(STRATA_USE_HIP)` ->
  `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`. One line.

Leaves alone: `prefill.cpp:272` and `:2590`, which guard HIP-only features
(`STRATA_HIP_WMMA`, `STRATA_KV_HOST_DMA`) that gfx906 does not enable; whether gfx906 should also
take those is a separate question.

## Extra Notes
Measured on an MI50 32GB (gfx906, ROCm via the compat build), engine 0.1.41, CLI generate, a 4-token
prompt (below the 1024-token `cpu_share` threshold). Two arms, differing only in
`STRATA_PREFILL_CPU_SHARE`:

- default (branch compiled in): `experts streamed 309 (295 by DMA, host 174.0 ms), resident 607,
  on the CPU 197 (share 0.90)`; prefill 928.3 ms
- `STRATA_PREFILL_CPU_SHARE=0`:   `experts streamed 506 (492 by DMA, host 177.3 ms), resident 606,
  on the CPU 0 (share 0.00)`; prefill 929.5 ms

Both arms produced the same 4 tokens. So the mechanism does run on AMD (contra "AMD are as before"),
and on this machine it bought ~0.13% prefill - below our 1.2-1.7% prefill resolution - while the
banner itself warns of a KL ~0.004 answer shift.

Not tested: no CUDA or SYCL GPU here. For those backends the change is a preprocessor no-op -
`STRATA_HIP_GFX906` is undefined there, so `!defined(STRATA_HIP_GFX906)` is true and the guard
expands exactly as before. (Happy to attach a `gcc -E` diff if useful.)
```

---

## 6 能力盘点与缺口

| 项 | 状态 |
|---|---|
| 完整源码树 | **有**（本机 `deploy/tmp/src411/Strata-0.1.41/`；容器内 `/src`）-- 但**均无 `.git`**（发布包解出） |
| 构建环境 | **有**（166 `build-906`，gfx906 + HIP 全链路） |
| 验证手段 | **有**（`verify_config.py` / bench 探针 / `conversation_cache_parity.py` / CLI 两臂对拍） |
| 目标硬件 | **有**（MI50 32GB）-- 维护者**没有** |
| 先例 | **有**（PR #1396 已并入 0.1.41） |
| **缺** | **git 通道**：源树非 clone，需 `git clone` 上游 + fork + push；并需要**你的 GitHub 账号** |

=> 结论：**技术侧全通，只差"发布通道"这一步**（属于要你拍板的事 ---- 公开提 PR 会带上账号身份）。

---

## 7 建议的下一步

1. **就提这一个 PR**（1 行 + 上面文案）。**不要**把 `mtp.cpp:428` 那处同型并进来：
   它动的是 gfx906 的**流选择**，若 gfx906 实际需要 `side_` 流，改了会**破坏运行** => 必须先
   在 gfx906 上实测再单独提（同 AGENTS.md "one change per pull request"）。
2. feature（"子 chunk 边界 checkpoint"）**先不提** ---- 它工作量大、需要上游设计讨论，适合先用
   `feature_request.yml` 的 issue 探路。
3. 我方自用侧：PR 合并后删掉 config 里的 `STRATA_PREFILL_CPU_SHARE=0`（P23 的显式覆盖）。

---

## 8 证据索引

| 件 | 位置 |
|---|---|
| 目标行 | 容器内 `src/prefill/prefill.cpp:1839`（函数 `arm_cpu_share`，起于 :1837） |
| 宏定义 | `CMakeLists.txt:64-67`（两后端互斥）、`:128`、`:134` |
| 上游自认 | `src/core/expert_cache.cpp:5-6` |
| 正确先例 | `src/core/mtp.cpp:420`、`src/core/device.cu:235`、`src/core/expert_cache.cpp:6` |
| 自相矛盾证据 | `src/core/mtp.cpp:420` vs `:428`（同一函数内相隔 9 行） |
| 实测两臂 | W718 报告 `deploy/W718_P23_CPUSHARE.md`；原始日志 `deploy/tmp/_w717_p23_arm{A,B}.log` |
| 贡献规范 | 容器内 `/src/AGENTS.md`、`.github/pull_request_template.md`、`.github/ISSUE_TEMPLATE/` |

> 过程脚本：`C:\Users\clyde\AppData\Local\Temp\_w724rec{,2}.py`；原始输出 `_w724recon.txt`、`_w724rec2.txt`。
> 本轮**只读**：未 clone、未改任何源码、未动 166。

---

## 9 追加（2026-10-09 20:4x，W725 波）

**① 「缺 git 通道」不成立 ---- 通道早已打通。** 166 上 `/home/albus/strata166/pr/` 是上次提 PR 的完整工作区：
- `strata-fork/` = **真 git 仓**，remote `git@github.com:phoenixclyde/Strata.git`（分支 `gfx906-build-fixes-402` / `main`，HEAD 干净）
- `_mkpr.sh` = **7 步流程**（clone/shallow -> 建分支 -> 打补丁 -> 核对改动清单 -> commit -> push -> 远端核对）
- `commitmsg.txt` = 上次的 commit message（可作模板）

=> 提 PR **不需要新配任何东西**：fetch 最新 main -> 建新分支 -> 打 patch -> push -> 开 PR。

**② PR #1396 的真相（表述更正）**：实查 GitHub API ---- `state=closed`、`merged=False`；维护者评论原文（2026-10-08T12:18Z）："**is in 0.1.41 with your authorship kept** ... **Closing as ported**"。落地 commit = `a732a19b6f`（在 main 上，改 `CMakeLists.txt` 与 `strata_hip.h`）。=> 应表述为「**已 ported 进 0.1.41（保留署名），PR 状态 closed-not-merged**」，而非「已并入」。

**③ `mtp.cpp:428` 复核结论**：**不是同型漏判**（创建 `side_` 与使用它用同一个宏、配套自洽）----详见 `W725_SWEEP.md` §6。**若照本报告 §2.4/§7 的思路去"补宏"，会引入 `side_ == nullptr` 的真 bug。**

---

## 10 追加（2026-10-09 21:3x，W728 波）---- 候选 2 从「建议」升级为「已实测的 patch」

W726 时**候选 2（`serve/telemetry.py` 的 `_Amd.read()` 不读 PCIe）**只是一句空口建议。W728 已把它做成
**21 行 diff + 单测 6/6 + 容器内实测 + 端到端 + 反事实自证**，而且**已在生产跑通**。

**补丁正文**（下方片段是 **v1（只读设备自身那一跳）**，仅存史；**当前定稿是 v4** ---- 见
`deploy/tmp/_w733_telemetry_final.py`（md5 `7433869abef54c8fba0012ca9fad59db`），
口径与对外提法见 `W733_TELEMETRY_AUDIT.md`。原版 md5 `e0a011fe...`，原版件在
`deploy/tmp/_w728_telemetry_pristine.py`）：

```python
    @staticmethod
    def _link_gen(path):
        """The PCIe link generation from an amdgpu link-speed file ("16.0 GT/s PCIe" -> 4), or None.
        The file holds the negotiated speed while the card is up; amdgpu has no PCIe throughput counter."""
        try:
            with open(path, encoding="utf-8") as f:
                return {2.5: 1, 5.0: 2, 8.0: 3, 16.0: 4, 32.0: 5, 64.0: 6}[float(f.read().split()[0])]
        except (OSError, ValueError, TypeError, IndexError, KeyError):
            return None
```

```python
        out["pcie_gen"] = self._link_gen(os.path.join(self.dev, "current_link_speed"))
        out["pcie_gen_max"] = self._link_gen(os.path.join(self.dev, "max_link_speed"))
        out["pcie_width"] = self._int(os.path.join(self.dev, "current_link_width"))
```

**为什么这样写**：`Telemetry.sample()` 用 `s.update({f"gpu_{k}": v for k, v in g.items()})` **透传 reader 的全部键**
（不是白名单）=> 只要 `_Amd.read()` 多返回这三个键，`/metrics` 与 `app.js` 一行都不用改。
**为什么不含吞吐（v1 当时的判断，W732 已推翻）**：当时以为 amdgpu `pcie_bw` 的三个整数
（空载 `50 0 256` / 负载 `4571 4709165 256`）**语义无内核文档**。W732 查证：**内核是有文档的**
（`Documentation/gpu/amdgpu/driver-misc.rst` + `soc15.c` 的 EVENT0_SEL=40 / EVENT1_SEL=108）
=> 文档口径带宽 = `(received + sent) * mps`，**已采用**（写法见 v4 的 `bw()`）。
**但方向口径是新的问题**：`pcie_rx_mb` 在 NVML 是纯 RX，AMD 侧拿到的是双向合计，没有方向可拆
=> 见 `W733_TELEMETRY_AUDIT.md` §4，**这是本改动不该原样提上游的主因**。

**我们已做的验证**（gfx906 / **MI50 32GB** / engine 0.1.41）：
v1 时 `_link_gen` 单测 6/6、容器内 `_Amd(0).read()` -> `pcie_gen 4 / pcie_gen_max 4 / pcie_width 16`；
**v3/v4 起改为"路径瓶颈"**（`link()`）：`sudo lspci -vv` 独立通道确认根口 LnkSta=8 GT/s、本卡跳 16 GT/s
=> 有效 **Gen3 x16**，`/metrics` 实测 `gpu_pcie_gen 3 / gen_max 3 / own_gen 4 / width 16 / path 4/4`；
v4 单测 **23/23 PASS**（假 sysfs 树 + 反事实 + 多卡聚合）；生产无 traceback。

**更正**：本节早先写的 "MI50 **16GB**" 是我把板子的 FRU 字符串
（`product_name` = `Radeon Instinct MI50 16GB`）当成了真值 ---- 本机实际是 **32GB**
（PCI ID `1002:66a1` + lspci 名 + VRAM 31.98 GiB）。FRU 与实物不符见 `W728_PCIE_TELEMETRY.md` §9.5。

详见 `W728_PCIE_TELEMETRY.md`。=> **对外仍是 3 件**（2 PR + 1 feature request），本条只是证据更强。
