# W794 注意力：没有可翻的开关，只有一条 int8-only 的 gfx906 专用路径

> 机主令「继续，该上网查一定要上网查」。本轮把 P5 的第一项（`qsa attn`，M 19.7% / L 15.3%）查到底：
> **先证明"没有可以打开的等价路径"，再查清"上游在 gfx906 上到底做过什么"，最后只做那一条有上游实测数字的小改动。**

---

## 1 结论先行

1. **`qsa_prompt_attn.cu` 里所有 prompt 注意力内核在 AMD 上都是 `__trap()`**：
   `mma16816()` 逐字 `#if !STRATA_PA_SM80 && (defined(__HIPCC__) || ...) __trap();`，
   而 v1（`prompt_attn_kernel`）、i8、i8v3、v70、wmma 五个内核**全部**调用它（行 343/456/673/765/910/993）。
   => `qsa_prompt_attn_batch()` 里那句 `#if defined(STRATA_HIP_GFX906) return false;` **不是 bug，是必须的**。
   **"已实现但被一行挡住"这个假设，在这一处不成立。**（规则 J 的第一次失败）
2. **gfx906 真正有的专用优化只有两条，且都是 int8-only**：#1661 的 query swizzle（+14.65% kernel / **+1.19% 全模型提示**，**逐位一致**）
   与 `reduce12`（同样的归约换法）。两者在代码里都被 `kv_mode == 1` 卡住。
3. **我们的 `--kv k8v4` 是 KV_MODE 3（int8 K + q4_0 V）**，所以这两条**一直关着**。
   而"置换"本身是 q 在 LDS 里的双射 XOR（`sd = d ^ ((d >> 3) & 4)`）+ 读侧 `qflip = lane & 4` 还原，**与 KV 格式无关**
   ⇒ 放开到 mode 3 在算术上是恒等的。本轮打了这个补丁（p4 镜像）并实测（§5）。
4. **roofline 先算清楚**：M 档 `qsa attn` 6.85 s / 3 chunk；每 chunk ≈ 2.5 TFLOP（12 个 QSA 层 × 因果 8192²/2 × 2 × 256 × 24）
   ⇒ **约 1.1 TFLOPS = f32 峰值(13.2) 的 8%**；而 KV 读字节 ≈ 80 GB/chunk ÷ 805 GB/s ≈ 0.1 s ⇒ **带宽只占 4%**。
   => **纯算力受限**，且只跑到 8%。上游 #2220 在 Turing 上把同族内核重写后拿到 **1.5-4.1x（逐位一致）**，
   证明这条核确实有 3 倍以上余量 —— 但那要**写内核**，不是翻开关。
5. **`attn_batch` 32→128 彻底否掉**：`launch_chunks_batch` 的 grid 是 `(n_chunks, n_head_kv, n_q)`，
   查询维度**已经在 grid.z 里真并行**，`attn_batch` 只是把 z 切片分几次 launch。加它只省 launch 数（每 chunk 6144 次 × 5 µs ≈ 30 ms）。

---

## 2 源码证据（逐字）

```cpp
// qsa_prompt_attn.cu:53
#if !STRATA_PA_SM80 && (defined(__HIPCC__) || !defined(__CUDA_ARCH__) || __CUDA_ARCH__ < 750)
    __trap();   // AMD and pre-Turing builds: no mma.sync (the host keeps the old kernel there)

// qsa_prompt_attn.cu:2346
#if defined(STRATA_HIP_GFX906)
        return false;   // gfx906: the tensor-core and WMMA kernels are not for it; the FP32 kernel runs
#endif

// qsa_decode_attn.cu:966-970  ← 唯一可用的 gfx906 专用注意力路径，int8-only
    static const bool query_swizzle = [] { const char* v = std::getenv("STRATA_GFX906_ATTN_QUERY_SWIZZLE"); return v && v[0] == '1'; }();
    const bool use_query_swizzle = kernel < 0 && query_swizzle && !lane_cell && kv_mode == 1 &&
                                   query_swizzle_gfx906_device();
```

注意最后那行 `kv_mode == 1`：我们生产是 mode 3。`qsa_decode_attn.cu` 的分派逐字：
`if (kv_mode == 3) STRATA_ATTN_CHUNK_SEL(3, pre)` —— 走通用模板，**没有 swizzle、没有 reduce12**。

---

## 3 上游取证（GitHub API 实读正文）

| 条目 | 内容 | 对我们的判定 |
|---|---|---|
| **#1661**（closed）「Perf/gfx906 qsa query swizzle」 | 为 gfx906 wave64 的 INT8 批量 QSA attention 加默认关的 **query-LDS 布局置换**（`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1`）：**内核组件 +14.65%，全模型提示 +1.19%，输出逐位一致** | **这是我们唯一能拿的那一条**；上游只在 int8 池上量过 => 本轮放开到 k8v4 实测 |
| **#2220**（closed）「sm_75: QSA decode attention for INT8 KV off the shared-memory pipe (bitwise)」 | 重写 INT8 KV 的 decode attention，少 shared/shuffle 开销，**内核 1.5-4.1x，逐位一致**；其 `reduce12_gfx906` 思路**来自 gfx906** | Turing 专用实现（`#if !defined(__HIPCC__)`），gfx906 拿不到；**但它证明这条核有 3 倍以上余量** => 下一步是"移植/重写"，量级可估 |
| **#3857**（open）gfx928 wave64 构建 | 候选 1 就是"让 `STRATA_PREFILL_MMQ` 接受 wave64 后端" | 与我们的专家 MMQ（20.6%）同题；说明上游的 MMQ 矩阵路径对 wave64 也是缺口 |
| **#3073**（open） | `STRATA_SELECT_SIMT=2` 在 HIP 上静默退路 | `W793` 已判：我们树同样有此缺陷；P4 实测 -0.36% 判为噪声 => 不做 |

**没有**任何上游条目给出"gfx906 的 FP32/非 MMA prompt 注意力"——这一点本轮是**否定结论**，不是没查到。

---

## 4 本轮改动（p4 镜像）

`deploy/docker/patch_gfx906_attn_swizzle.py`，三处、共 12 行：

1. 判定放宽：`kv_mode == 1` → `(kv_mode == 1 || kv_mode == 3)`；
2. `attn_chunk_kernel<3, false, true, true>`（reduce12）；
3. `attn_chunk_kernel<3, false, true>`（仅 swizzle）。

镜像 `strata-gfx906:0.2.4p4` = p3 + 本补丁；断言：`W794` 出现 1 次、两个 `<3, ...>` 实例化各 1 次。
**算术不变**：置换只改 q 在 LDS 里的位置，读侧按同一双射还原；因此 A/B 用**定长贪婪输出的 sha16 全等**来判"逐位一致"。

---

## 5 实测（p4 三臂 A B C A B C，A 得两次、B/C 各一次后因重复启动事故中止）

| 臂 | env 增量 | `qsa attn` ms | `prompt_ms` | GPU timeline |
|---|---|---|---|---|
| **A** 基（p4，全关） | — | **6,742 / 6,743** | 34,910 / 34,459 | 34,205 / 33,758 |
| **B** +swizzle | `STRATA_GFX906_ATTN_QUERY_SWIZZLE=1` | **6,202（-8.0%）** | **33,954（-2.7%，见下方 AUDIT8 块：端到端应按相位算 -1.6%）** | 33,220 |
| **C** +swizzle+reduce12 | 再加 `STRATA_GFX906_ATTN_REDUCE12=1` | **11,764（+74%）** | 39,121（+12%） | 38,390 |

**A 的两次 `qsa attn` 差 1 ms（6742 / 6743）**，所以 B 的 -8.0% 不是噪声。

> **【AUDIT8 更正 2026-10-25 18:4x，P1-2】** 原文写"其余相位一个没动"是**错的**：同一批数据里 **`gemm gate/up` = 7,643（A①）/ 7,503（A②）/ 7,133（B）/ 7,136（C）**
> —— A 臂比 B/C **高 5.8%**，而注意力 swizzle 只改 q 在 LDS 里的双射 XOR，**不可能**动专家 MMQ。
> 于是总量差 1,012 ms 里有 **≈440 ms 与开关无关**；按 `qsa attn` 相位差（6,742.5 → 6,202 = **-540 ms**）折算，**端到端是 -1.6%，不是 -2.7%**。
> 除 `gemm gate/up` 外，`hc read` 2624/2624、`qsa select` 702/702、`gdn` 3722/3758 确实没动 ⇒ "只命中注意力"这条仍然成立。

**结论**：swizzle 采纳（**`qsa attn` 相位 -8.0%，可复现到 1 ms；端到端 -1.6%（相位折算）**；总量 -2.7% 含 440 ms 与开关无关的漂移，不作幅度依据），**reduce12 否决（+74%）** —— 后者显然假定了 int8 V 的 lane→head 映射。

## 5.1 一个意外的副产物：本引擎跨请求不确定，"位等价"无法用哈希验证

本想把"输出 sha16 全等"当位等价判据（上游 #1661 声称逐位一致），结果在同**一个容器、同一 env** 下连发三次
同一条 `temperature=0` 的 8-token 请求，得到 **2 次 `a108be5b`（长度 15）+ 1 次 `9f1f1d0c`（长度 17）**。
=> **引擎本身跨请求不确定**（最可能是专家驻留/换入路径的差异，`W767 §4.1` 记过同类观察）。
所以本轮的位等价只能用①上游声明②置换是自逆 XOR③"只动 qsa attn"的相位证据三者合起来，**门用 needle**（32k@50% FOUND，53 s）。
这条也要记下来：以后任何人拿"同一 prompt 两次输出不同"当 bug，先排掉这个已知不确定性。

## 5.2 采纳（2026-10-25 17:10）

| 项 | 值 |
|---|---|
| 镜像 | `strata-gfx906:0.2.4p4`（= p3 + `patch_gfx906_attn_swizzle.py`，构建 ~4 min） |
| env（7 项） | 原 6 项 + **`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1`** |
| 质量门 | needle 32k@50% **FOUND**（53 s） |
| 合规 | `verify_config` **PASS=31 FAIL=0**；`gen_config --live` 无差异 |
| 生产 | slots 9901 / vram 606 / ver 0.1.49.2 / 无仪器 M：`prompt_ms 33,200`、657.4 tok/s、墙钟 38.8 s |
| 回滚 | 镜像 `0.2.4p3` / `0.2.4`；config `.bak_w794final_*`、`.bak_w793_*` |

---

## 6 举一反三

1. **"已实现但默认关"有第四种形态：默认关、且技术上不可能开**（MMA 在 AMD 上是 `__trap()`）。
   前三轮我把它归成三类（可用 / 被前置条件挡死 / 没编进去），本轮补第四类：**编译成陷阱**。
   判据：`grep -n "__trap()" <文件>`，再看谁调用了那个被 trap 的函数。
2. **同一份代码里，平台专用优化往往只覆盖了作者自己那一种配置**。#1661 是 int8 池，我们是 k8v4；
   `kv_mode == 1` 这个判定把 gfx906 唯一的注意力优化在我们配置下彻底关掉，**而且没有任何日志会说"它被关了"**。
   => **规则 O：凡 "平台专用 + 环境变量开" 的优化，必须核 `use_*` 的前置条件里有没有配置项（kv_mode/batch/T 下限），不能只看 env 名。**
3. **先算 roofline 再谈写内核**。8% 的峰值效率 + 上游同族 1.5-4.1x 的实证，这两条一起才构成"值得写"的理由；
   只凭"它占 19.7%"就去写内核，等于凭占比下注。
