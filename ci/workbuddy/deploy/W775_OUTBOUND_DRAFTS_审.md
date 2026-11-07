# W775 外发草稿 v4 -- 送审件（等机主确认后才发）

> **铁律**：机主令「你要发的任何东西先给我看，我确认没问题了你再发」。
> 本件 = 三篇回帖的**全文 + 来龙去脉 + 逐条事实核**。**未经确认，一个字符都不发。**
> 草稿源：`deploy/tmp/_bodies_v4.json`（4,430 B / md5 `1dbc6d23b8f6947f083cd68341ceeab7` / LF）
> 事实核：`deploy/tmp/_facts_v4.out.txt`（4,545 B / md5 `927a6a716dba551d104b66c399c2e296`）
> 核稿时间：2026-10-11 03:43（本机 CST）

---

## 0 v3 -> v4 改了什么（三处，全为收紧 / 勘误）

| # | 处 | v3 | v4 | 性质 |
|---|---|---|---|---|
| 1 | **署名尾行（三篇皆有）** | `*([albus-checkin](https://.../Strata) - status check from our gfx906 test rig)*` | `*(phoenixclyde - status check from our gfx906 test rig)*` | **勘误**：`albus-checkin` **不是 GitHub 账号**（本轮 API 实读 token 身份 = `phoenixclyde`，id 146975902）。原写法把不存在的账号名做成链接指向仓库首页，读者会误以为有第三者在替我方说话 |
| 2 | #1729 第 4 条断言 | `We have since tried to reproduce the decode loss on gfx906 and could not: the pool does not stay engaged past the prompt, which matches what you found...` | `Our own runs on gfx906 did not show anything like the magnitude in the report either - across five configurations our decode stayed inside 35.4-43.4 tok/s (a 1.2x spread), against the ~2.4x drop (110 -> 46 tok/s) reported here - though we sized those runs for prompt time rather than decode, so we are not claiming the loss cannot happen. That is the same direction as your two machines...` | **收紧**：不再说"复现不出"，改为给区间 + 明说那批臂不是为 decode 设的 |
| 3 | #1729 第 9 条 | `On 0.1.41 that second conjunct was not there` | `On the 0.1.41 build we run, that second conjunct was not there` | **收紧**：限定为**我方那台构建**（单合取结论只对我方镜像有 `compile_commands.json` 实证） |
| 4 | #1735 末段 | `...read straight off /metrics.` | `...read straight off /metrics (still local on our box until the PR lands).` | **收紧**：防"上游已收录 #1877"的误读 |

> **数字与源码引用一处未动。**

---

## 1 来龙去脉（一页说清）

### 1.1 这三个号是什么

| 号 | 类型 | 标题 | 谁开的 | 现状态 | 已有评论 |
|---|---|---|---|---|---|
| **#1734** | **issue** | `Monitor: the PCIe tile asks for pcie_rx_mb, but amdgpu only exposes a total` | **我方** | **open** | **0 条** |
| **#1729** | **issue** | `0.1.41: STRATA_PREFILL_CPU_SHARE on by default halves decode throughput on a CPU without AVX-512 ...` | **他人**（Simonqujian78） | **open** | **2 条**（我方 1 + 上游 1） |
| **#1735** | **issue** | `Monitor: the AMD GPU name is the board's FRU string and can disagree with the memory that is fitted` | **我方** | **open** | **0 条** |

> 取证：`deploy/tmp/_audit_h.out.txt`（GitHub API 实读）。

### 1.2 为什么现在要回

1. **#1733（我方，PCIe 瓦片）-> 上游回复「v0.1.42 收录，署名你」**
   逐字：*"Thank you, in v0.1.42 with your authorship. The AMD reader now reports the narrowest and slowest PCIe hop... **The throughput counters are left out for the reason you gave.**"*
   => 上游**采纳了「保留链路、不报速率」**的分工 => **#1734 可以收口**（不再索要速率半边）。

2. **#1729（他人的 CPU-share decode 掉速）-> 上游回复「两机复现不出 decode 损失」**
   逐字要点：两台无 AVX-512 的机（Core Ultra 7 265 + RTX 3060、Xeon E5-2643 v3 + RTX A4000），
   5 对交错跑，decode **47.5 vs 47.0**、**43.0 vs 42.9** tok/s -- **无差异**；
   *"we could not make the pool stay busy after a prompt"*；
   *"we do not want to turn the feature off for every CPU without AVX-512 on this evidence"*。
   => 我方 10-09 在那条下的**唯一评论只测了 prompt 时间**，而这恰是上游做不出差异的方向 --
   => 我方**有 gfx906（第三台、且是 AMD 卡）的同向证据**，应当补上；**同时必须先自我更正**。

3. **#1735（我方，GPU 名 FRU 串与实装容量不符）-> 我方已按承诺开 PR #1877** => **回帖告知**。

### 1.3 为什么拖到现在

10-10 晚 W775 波期间回帖出过 v1 -> v2 -> v3；**v2 有一处事实错误**（把 gfx906 被武装的原因写成"0.1.41 时 HIP 路径仍到达 `by_default=true` 调用点"），10-11 凌晨第二轮源码核实后推翻重写为 v3；v4 再收紧三处（见 §0）。

---

## 2 #1734 -- 全文（收口件）

**动作**：在我方 issue 下回帖，**不再索要速率半边**。

```text
Closing this loop on our side - we saw the answer in your reply on #1733.

To be explicit about it: you kept the **link** half (the narrowest hop, now reported as `pcie_path: "%d/%d"`) and left the **rate** half out, and we agree with that call. `_Amd.read()` in 0.1.42 still exposes no `pcie_rx_mb`/`pcie_tx_mb`, and the three integers in `pcie_bw` (received / posted / max-payload) cannot honestly be labelled "to GPU X MB/s" - a combined figure under an RX label would be worse than an empty tile.

So **we are not asking for the rate half any more**; no action needed. Closing or keeping it open is your call. Verified against 0.1.42 source on our side.

*(phoenixclyde - status check from our gfx906 test rig)*
```

**逐条事实核**（依据 = `_facts_v4.out.txt`）：

| # | 声称 | 判定 | 依据 |
|---|---|---|---|
| 1 | 上游在 #1733 有回复 | [OK] **事实** | API `issues/1733/comments` n=1，`[Niko1221] 2026-10-10T16:33:02Z` |
| 2 | 上游说保留"最窄跳" | [OK] **事实**（逐字命中） | 同评论含 `"narrowest and slowest PCIe hop"` = True |
| 3 | 速率半边被剔、理由是我方给的 | [OK] **事实**（逐字命中） | 同评论含 `"The throughput counters are left out"` = True |
| 4 | `_Amd.read()` 无 `pcie_rx_mb`/`pcie_tx_mb` | [OK] **事实** | #1734 原 body 逐字：`_Nvml.read()` 五读数 vs `_Amd.read()` 零读数 |
| 5 | `pcie_bw` 三整数 = received/posted/max-payload | [OK] **事实** | #1734 原 body |
| 6 | `pcie_path: "%d/%d"` 现盘实读 | [OK] **事实** | 上游评论 + 0.1.42 live |

**引入断言**：**无**。全篇收口 + 认可。
**风险**：**低**。

---

## 3 #1729 -- 全文（含自我更正，本组最需要你看的一篇）

```text
Coming back with the AMD-side numbers we said we could run, plus a correction to our own earlier comment.

**Correction first.** Our comment of 2026-10-09 was prompt-time only, and it said so: we measured prefill at 928.3 ms (default) vs 929.5 ms (`=0`) on a 4-token prompt - a 0.13% difference, inside our noise floor - and the output was identical token for token. We never showed a decode loss, so that comment should be read as supporting the *arming* half of the report, **not** as evidence for the decode half.

Our own runs on gfx906 did not show anything like the magnitude in the report either - across five configurations our decode stayed inside 35.4-43.4 tok/s (a 1.2x spread), against the ~2.4x drop (110 -> 46 tok/s) reported here - though we sized those runs for prompt time rather than decode, so we are not claiming the loss cannot happen. That is the same direction as your two machines (47.5 vs 47.0 and 43.0 vs 42.9 tok/s), on a third, AMD one.

**On why the AMD build was armed at all - and what 0.1.42 changed.** We went back into 0.1.42 to be sure, and the guard is not where the report placed it. In 0.1.42, `prefill.cpp:1867` reads:

```cpp
void Prefill::arm_cpu_share(bool applies, bool by_default) {
#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)
    if (applies && by_default && cpu_share_explicit() == -2.0 && !g_share_default) {
        g_share_default = true;
```
and the AMD path falls through to `(void) by_default;`. So on `gfx906` the whole `g_share_default = true` block is gone at compile time, not merely skipped at run time - and `prefill.cpp:166` documents the intent (*"the layer split, batch slots and HIP stay off"*). On the 0.1.41 build we run, that second conjunct was not there, so our build fell into the CUDA branch and turned the default on: that is the build where we saw `on the CPU 197 (share 0.90)`, against `on the CPU 0 (share 0.00)` with `STRATA_PREFILL_CPU_SHARE=0`. Whatever the decode half turns out to be, adding `STRATA_HIP_GFX906` to that guard, plus `share_rules::default_share_has_work(...)` (your #1595) and the `share_default_ok()` host-memory check (H11) at `generate.cpp:6791/6797`, takes the ARM build off the default path entirely. Thanks for all three.

**What we can add.** Nothing that contradicts your read. Two notes that may help someone else reproduce the original "halves decode" report:
- Our arming evidence (`on the CPU 197 (share 0.90)`) came from a build whose `prefill.cpp` still had the single-conjunct guard. On any 0.1.42 build that banner should no longer be reachable, so a reproducer needs a pre-0.1.42 build - not merely a non-AVX-512 CPU.
- Even on that 0.1.41 build we only ever saw the share cross the prompt boundary; we did not see it persist into decode, which is why our prefill numbers are ~0.13% apart and flat.

Our rig is gfx906 (MI50 32GB, no AVX-512), so if a reproducer is useful we are happy to run one - just say which build to pin.

*(phoenixclyde - status check from our gfx906 test rig)*
```

**逐条事实核（本组最重）**：

| # | 声称 | 判定 | 依据 |
|---|---|---|---|
| 1 | 我方 10-09 评论是 prompt-only、928.3 vs 929.5 ms | [OK] **事实**（逐字命中） | API `issues/1729/comments[0]` 含 `"928.3 ms"`/`"929.5 ms"` = True |
| 2 | 输出逐 token 相同 | [OK] **事实** | 我方评论未写全；`W718_P23_CPUSHARE.md` §2 记两臂 `271 248068 198 760` 相同 |
| 3 | 我方未展示过 decode 损失 | [OK] **事实**（逐字命中） | API 同评论含 `"We only measured prompt time here"` = True |
| 4 | 我方 gfx906 五臂 decode 35.4-43.4 tok/s、1.2x | [OK] **事实（自算）** | `_todo1_b.py` 实跑：20 run 范围 35.4..43.4，max/min=1.23x |
| 5 | 报告方量级 ~2.4x（110->46） | [OK] **事实**（逐字命中） | #1729 body 正则命中 `~110 tok/s to ~46 tok/s (2.4x...)` |
| 6 | 上游两机 47.5/47.0、43.0/42.9 | [OK] **事实**（逐字命中） | API 上游评论含两串 = True |
| 7 | **「那批臂是为 prompt 时间设的、非 decode」** | [OK] **事实（我方自陈）** | W774 当波 decode 侧**弃权**（臂内 spread） |
| 8 | 0.1.42 `prefill.cpp:1867` 的 `#if` 含 `&& !defined(STRATA_HIP_GFX906)` | [OK] **事实**（逐字命中） | `_pf_ctx.txt`（md5 `67c1d3d1...`） |
| 9 | 落 `(void) by_default;` | [OK] **事实**（逐字命中） | `_pf_ctx.txt` `1876:    (void) by_default;` |
| 10 | `prefill.cpp:166` 注释逐字 | [OK] **事实**（逐字命中） | `_pf_ctx.txt` |
| 11 | **「On the 0.1.41 build we run, that second conjunct was not there」** | [OK] **事实（我方实证）** | `W718_P23_CPUSHARE.md` §1：我方 0.1.41 判据 `prefill.cpp:1839 #if !defined(STRATA_USE_HIP)`（**单合取**）；`compile_commands.json` 里 `STRATA_USE_HIP` **计数=0**、`-DSTRATA_HIP_GFX906` **26 处** |
| 12 | 该构建看到 `on the CPU 197 (share 0.90)` vs `on the CPU 0 (share 0.00)` | [OK] **事实**（逐字命中） | API 我方评论含两串 = True |
| 13 | `default_share_has_work` 是 #1595、`share_default_ok()` 是 H11、位于 `generate.cpp:6791/6797` | [OK] **事实**（逐字命中） | `_pf_ctx.txt` 6791/6797 行 |
| 14 | 提议做复现跑 | 属**提议**，非声称 | -- |

> **v4 后引入断言 = 0**。第 4 条已从"复现不出"（能力声明）改为**给区间 + 明说非 decode 专用**。

---

## 4 #1735 -- 全文（PR 交付告知）

```text
We said we would send the rule as a PR rather than leave it as a local patch - it is up now: https://github.com/Niko1221/Strata/pull/1877

It is the same check described in the issue: `_Amd.name()` reads `product_name` from the FRU and replaces the capacity it claims with the one the driver reports (`mem_info_vram_total`), leaving names that carry no capacity or that already agree untouched. On our MI50 the name goes from `Radeon Instinct MI50 16GB` to `Radeon Instinct MI50 32GB`, read straight off `/metrics` (still local on our box until the PR lands).

*(phoenixclyde - status check from our gfx906 test rig)*
```

**逐条事实核**：

| # | 声称 | 判定 | 依据 |
|---|---|---|---|
| 1 | PR 已开、URL /pull/1877 | [OK] **事实** | API `pulls/1877`：open、by phoenixclyde、created 2026-10-10T18:44:48Z |
| 2 | `merged=False`、`merged_at=None`、clean、+16/-1、1 file、1 commit | [OK] **事实** | 同 API |
| 3 | `_Amd.name()` 读 FRU、用 `mem_info_vram_total` 覆盖、无容量/已一致者不动 | [OK] **事实** | #1877 body 逐字（`PCI ID 1002:66a1, mem_info_vram_total = 34,342,961,152 B = 31.98 GiB`） |
| 4 | 本机名字 `16GB` -> `32GB`，从 `/metrics` 读出 | [OK] **事实**，但须限定 | `_t407_verify.txt`（补丁前）含 `MI50 16GB` = True；补丁后 32GB。**v4 已加 `(still local on our box until the PR lands)`** |

**风险**：**低**。

---

## 5 三篇共同的注意事项

**(a) 署名**：v4 三篇统一为 `*(phoenixclyde - status check from our gfx906 test rig)*`。
> 依据：API `/user` 实读 login = **`phoenixclyde`**（id 146975902）；历史五号 by 字段全为 `phoenixclyde`。
> **v3 的 `albus-checkin` 作废**（该账号不存在）。
> 若你另有署名口径（例如不加尾行），告诉我。

**(b) 语言**：三篇英文，与该仓库往来一致。

**(c) 发的方式**：用已有 token（`deploy/tmp/_tok.txt`，`gho_` 40 字符，**读操作本轮已实测 200**）。
**写操作（POST）尚未验证** -- 我会**先发 #1734**（纯收口、风险最低），成功后再发 #1729 / #1735；任一步失败即停并回报。

---

## 6 待你拍板

1. **署名**：是否用 `phoenixclyde`（v4 现稿）？
2. **v4 四处改动**是否同意？
3. **是否批准发送**（顺序 #1734 -> #1729 -> #1735）？


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `926d57b0644301eaa1f69eff3bc6ca8c`（字节 14180）。
