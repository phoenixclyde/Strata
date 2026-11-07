# W775delta ---- 用 0.1.42 **源码树**闭合审计的「无法验证」项

日期 2026-10-11 ｜ 源 = 166 镜像 `strata-gfx906:0.1.42` 的 `/src`（**机主指出**源码就在镜像里）｜ 本地归档 `deploy/tmp/src142/` ｜ 零发车

## 0 本轮做了什么

审计（`W775delta_AUDIT3.md`）的「无法验证清单」里有 **4 条**是因为**本机只有 0.1.41 源码树**（`deploy/tmp/src411/`）而卡住的。
机主指出 **0.1.42 源码就在 166 的镜像里** => 本轮把它**归档到本机**并逐条闭掉。

**归档方式（可复现，无 GPU、不占 VRAM、不停生产）**：

```bash
docker run --rm --entrypoint bash strata-gfx906:0.1.42 -lc \
  'cd /src && tar czf - src include tools serve cmake docs CMakeLists.txt README.md'
```

| 项 | 值 |
|---|---|
| tar 包 | `deploy/tmp/src142.tgz`（**12,943,360 B** / `f8a241aeb06115c81e73bcd13ad6213a`） |
| 解出 | **618 个成员** -> `deploy/tmp/src142/` |
| 覆盖 | `src/` 5.7M · `include/` 1.2M · `tools/` 1.5M · `docs/` 11M · `serve/` 1.6M · `cmake/` 8K（不含 `bench/` 22M 与 `build-906/`） |
| 版本自证 | `CMakeLists.txt:project(strata VERSION **0.1.42** LANGUAGES CXX)` |

> **意义（不只是补一条）**：此后**车在跑、生产容器停着时也能读 0.1.42 源码** ---- 此前每次读源码都要 `docker exec`，
> 而车期间容器是停的（本轮 `W19` 就因此受过限）。

## 1 逐条闭合

### 1.1 审计「无法验证 #3」：`Q8/Q6_PACKED` 的「无损 / same bytes」实现层

| 位置 | 原文（逐字） |
|---|---|
| `include/strata/kernels/native_mmvq.hpp:96-99` | `STRATA_Q8_PACKED=1 (opt-in): a lossless load-time repack of a Q8_0 matrix into a qs plane (n_out x n_in int8) followed by a d plane (n_out x n_in / 32 fp16), the same bytes (34 per 32 values). A registered matrix's native_q8_0_mmvq calls ... read the packed copy instead; **every output is bitwise equal to the GGUF-layout kernels.**` |
| `:106-109` | `STRATA_Q6_PACKED=1 (opt-in): a packed copy of a Q6_K matrix (the output heads) - the same bytes as ql / qh / scales / d planes - that native_q6_k_mmvq calls on weights read instead (**bitwise equal outputs**). The copy is owned here ... **STRATA_Q6P_SELFTEST=1 checks it bitwise** and times it at load.` |
| `src/kernels/cuda/native_mmvq.cu:1640 / 1766` | 两段实现（`STRATA_Q8_PACKED=1: the packed Q8_0 decode layout (opt-in)` / `STRATA_Q6_PACKED=1: the packed Q6_K head layout (opt-in)`） |
| `src/core/native_dense.cpp:374` | 我们车日志里那条 banner 的出处：`native dense: STRATA_Q8_PACKED=1 packed %zu Q8_0 matrices for decode (+%.1f MiB)` |

**结论**：**这是上游写进头文件的契约**（bitwise equal outputs），且带 `STRATA_Q6P_SELFTEST=1` 自检开关。
与我们 W4X 车实测的 **parity 5/5 逐位相同**一致 => 「只买速度、不改数值」**成立**；「精度更高」**不成立**（两者无损，不涉及精度）。
（**限定**：本件核的是**声明层 + 文件级实现存在**；未逐行读 `native_q8_0_pack_host` 的位操作。）

### 1.2 审计「无法验证 #6」：`arch_defaults.cpp` 在 0.1.42 上是否 gfx906 取空表

`src/core/arch_defaults.cpp`（0.1.42 原文件）：

```
:12  std::vector<std::pair<std::string, std::string>> arch_default_env(const char* gcn_arch) {
:14  if (strata::kernels::gfx_arch_is_gfx12(gcn_arch)) {        // gfx1200/1201：只取 gfx1151 表的 prompt 半边
:22      if (off12 != nullptr && off12[0] == '0') return t;      //   STRATA_GFX12_DEFAULTS=0 可关
:30      return t;
:32  if (!strata::kernels::gfx_arch_is_gfx1151(gcn_arch)) return t;   // <== gfx906 在这里返回（t 仍为空）
:39      {"STRATA_GDN_PP", "2"},          //   two columns per lane: 64K prompt +2.9% (stream A, round 2)
:43      {"STRATA_HCD_EXACT", "1"},       //   64K +1.8% (stream S)
:46      {"STRATA_Q8_PACKED", "1"},       //   +2.3% (S26)
:52      {"STRATA_LFUSE", "1"},           //   (S26)
:58      return t;
```

**结论**：`:32` 之后的表**只对 gfx1151 返回**；gfx906 在 `:32` 就 `return t`（空表）=> **R4 的「§4 族在本卡一个都不自动开」在 0.1.42 源码上直接核实**（此前是从 0.1.41 树推断）。

**顺带一处引用精度更正（R4 件）**：R4 把 `HCD_EXACT` 判「先排」时引的那句
*"it needs the gfx1151 hipBLASLt tuning table, finds none on gfx12, says so on every start and does nothing (measured: 0.0 to +0.1%)"*
位于 **`arch_defaults.cpp:17` 的 gfx12 分支注释里**（不是 gfx906 的实测）。gfx906 侧的准确表述是：
**它不在任何 gfx906 表里（表为空）**，且其机制依赖 hipBLASLt 调优表（本卡没有）=> **预期同样空操作，但"实测 0.0~+0.1%"是 gfx12 的数**。已在 R4 件加注。

### 1.3 审计「无法验证 #5」：`docs/DETAILS.md` 0.1.42 版对 `k8v4` 的逐字定义

`docs/DETAILS.md:91-95`（0.1.42 原文）：

> **Hybrid K8V4 KV cache (engine 0.1.25, optional, PR #120):** `--kv k8v4` keeps **the keys at 8 bits and stores the values as rotated 4-bit: 23% less KV memory than 8-bit, so more experts fit in VRAM**. RTX 3090, the Coder at 198K context: **99 instead of 85 tokens/s output, the same needle results**, prompts 2-5% slower. It streams its KV cache like the other formats (**`--kv-resident N`**): on an RTX 2060 SUPER 8 GB at 128K with 20,480 resident cells, **+780 expert slots** over resident K8V4, and it scores better than 4-bit KV on long documents.

**结论**：与我们的读数**同向**（W770：`k8v4` needle 两臂 **6/6**、decode **+7.7~16.6%**、省 3.8 GiB）。
**并直接支持新登记的 `P63 --kv-resident`**：上游把它写成 k8v4 的**配套流式机制**（"+780 expert slots"），我们此前从未登记。

### 1.4 审计「无法验证 #4」：`+1912.5 MiB` 引擎 banner

该行**本机已归档**：`deploy/W775delta_W4X_Q8PACKED_RESULT.md` §1 引的是车日志原文；
且 1.1 已给出**产生它的代码行**（`src/core/native_dense.cpp:374`）=> **出处闭合**。

### 1.5 审计「无法验证 #1 / #2」----先前已闭

- **#1**（`verify_config` 12:52 那次无留档）：已由 `W22` 落地（此后每次运行存 `deploy/params/_verify_<ts>.txt`）。
- **#2**（W16 车产物）：已补（产物名为 `_w4x_rts_*`，非 `_w16*`）。

## 2 `W25 #7` 一并闭合：`#1479` 两个 opt-in 在 0.1.42 的语义

`src/core/verify.cpp:187-222`（0.1.42 原文）：

```cpp
// A one-token window always keeps its token, so its graph advances the sequence state itself ... CUDA only:
// HIP keeps the commit graph after every window (STRATA_ONE_TOKEN_COMMIT=0 does too).
// The head's hyper-connection read ... (CUDA; HIP keeps gr_read per token; STRATA_HEAD_MIX_MULTI=0 does too):
// bitwise the same sums.
bool head_mix_multi_enabled() {
#if defined(STRATA_USE_HIP)
    ... const char* v = std::getenv("STRATA_HEAD_MIX_MULTI");   // HIP: opt-in (=1)
        return v != nullptr && std::atoi(v) != 0;
#else
        return v == nullptr || std::atoi(v) != 0;                // CUDA: 默认开
#endif
}
bool one_token_self_commit() { ... 同构（HIP 默认关 / `=1` 才开） }
```

**结论（W25 #7 (a)）**：0.1.42 的语义是 **HIP 默认关、须显式 `=1`**（CUDA 反而默认开）---- 与 `W12_PRECHECK` 的记载一致，
也与我们 W12D `D` 臂（同时置两键）的设置一致；且上游注释**自称 bitwise the same sums**，与我们 W12D 的 **parity 5/5 逐位相同**一致。
(b)（prefill 中性 / decode 需 5+ runs）已由 `W12D` 结论覆盖 => **`W713 §6.4 #7` 整个闭环**。

## 3 局限

1. 本件是**源码级核实**（声明 + 逻辑），**不是**新的实测；1.1 的"bitwise equal"仍以我们 W4X 的 parity 5/5 为实测支撑。
2. `src142` 归档**不含 `bench/` 与 `build-906/`**（体积原因）；需要时按 §0 的同一命令重取。
3. 归档是**镜像快照**，不随上游 main 漂移；若上游出新版须重取（并重算 md5）。

## 4 产物

- `deploy/tmp/src142.tgz`（12,943,360 B / `f8a241aeb06115c81e73bcd13ad6213a`）
- `deploy/tmp/src142/`（618 成员）
- 拉取脚本 `deploy/tmp/_src_pull.py`；核验脚本 `deploy/tmp/_src_verify.py`
