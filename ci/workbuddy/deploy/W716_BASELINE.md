# W716 ---- 换权重后的基线重建 + B6 关项（交付报告）

- 日期：2026-10-09 02:0x-02:2x（本机时间）
- 结论：**huihui abliterated 与官方 base 性能同量级、无退化**；B6（P30 `STRATA_MMVQ_IL`）以源码判定关闭；
  另**更正 W715 报告的两处口径问题**（cache 槽归因、温 TTFT 口径）。

---

## 1 B6：`STRATA_MMVQ_IL`（register P30）---- 编译期即定，本机不适用

register §6.2 #4 写明"读源码即判，无需发车"，据此判定如下（证据全部为源码原文）：

    src/kernels/cuda/native_mmvq.cu:2474   #if !defined(__HIPCC__)
    ...
    src/kernels/cuda/native_mmvq.cu:2641   #else  // HIP: no interleaved path
    :2643   void native_q8_1_interleave(...) {
    :2644       throw std::invalid_argument("native_q8_1_interleave is CUDA only");
    :2646   bool native_mmvq_il_supported(int, int, int) { return false; }        <== 恒 false
    :2653   #endif  // !__HIPCC__

调用点是 `src/core/verify.cpp:952` 与 `:1604`：

    if (g_mmvq_il() && strata::kernels::native_mmvq_il_supported(w->native_type, n, n_out)) { ...IL 路径... }
    else { native_mmvq(...); }

- `g_mmvq_il()`（`verify.cpp:107`）默认 **on**（未设或非 '0' 即 true）---- 但这对本机无意义。
- 166 的构建是 **HIP**（走 `__HIPCC__`），于是 `native_mmvq_il_supported()` 恒返回 false =>
  **条件永远为假，永远走普通 `native_mmvq()`**。

**判定：本机结构上不可能命中（编译期即定，不是"未验"）。** register P30 已由 CANDIDATE 改为 **REJECTED**，值记 `(不适用)`。
另注：CUDA 分支下真正的门是 `ncols in [2,4] && g_multi_exact && il_arch_ok()`（后者要求 `major >= 8`，即 sm_80+），
这两条对本机同样不成立 ---- 属于旁证。

---

## 2 两臂基线对照（同探针 / 同参数 / 同批次）

探针：固定 3 档 prompt（5,485 / 11,785 / 27,985 token），每档先冷后温（温 = 原样重发同一 prompt），
贪心（temp 0 / top_k 1），max_tokens 64。两臂用**同一探针、同一参数、同一台机器**，**串行各跑一次**
（`-407` huihui 于 02:05、`-406` 官方 base 于 02:11，相隔约 6 分钟；显存放不下两个引擎，无法并行）。

| 档 | 臂 | 冷预填 tok/s | 冷 TTFT | 温 TTFT | 温 reused | 冷解码 tok/s | 温解码 tok/s | MTP 接受 |
|---|---|---|---|---|---|---|---|---|
| 5,485 | huihui | 428.7 | 12.84 s | 0.15 s | 5,480 | 40.5 | 42.7 | 44/47 |
| 5,485 | orig | 412.8 | 13.33 s | 0.11 s | 5,480 | 36.2 | 45.6 | 39/51 |
| 11,785 | huihui | 456.6 | 25.86 s | 0.11 s | 11,780 | 43.9 | 48.2 | 42/51 |
| 11,785 | orig | 457.3 | 25.82 s | 0.11 s | 11,780 | 46.9 | 52.8 | 39/43 |
| 27,985 | huihui | 465.6 | 60.10 s | 0.14 s | 27,980 | 46.2 | 55.3 | 42/49 |
| 27,985 | orig | 472.6 | 59.28 s | 0.13 s | 27,980 | 46.7 | 55.8 | 45/49 |

（口径声明：本表**吞吐与 `reused` 全部取引擎日志行原文**；TTFT 取客户端流式首字时刻。两臂同一口径。）

对照分辨力（本工作区既有口径）：**预填 1.2-1.7%、解码 9.5-15.0%**。

- 预填：+3.9% / -0.2% / -1.5% ---- 仅 5,485 档超出分辨力，其余无差。
- 温 TTFT 与 `reused`：**两臂逐格相同**（机制相同，符合预期）。
- 解码：+11.9% / -6.2% / -0.6% ---- 两个档在分辨力内，5,485 档超出但该档生成仅 64 token、噪声最大。
- MTP 接受率合计：huihui **249/290 = 85.9%**，orig **249/280 = 88.9%**；差 3 个百分点，在单批次噪声内。

**判定：无退化迹象。** 换权重后既有读数作废这一点成立，且**新分母与旧分母同量级**。
但要点明边界：本轮只重测了 3 档预填/解码 + 2 档前缀，**P25 `--pcie-frac 0.20` / P06 `--spec-min-p 0.70` /
P34 `--prompt-cache-every 8192` 这三条的"最优值"并未在 huihui 上重测** ---- 本节只能支撑"基线量级未变"，
不等于"参数结论已复核"。三条参数的正确表述是：**沿用 base 结论、待重测**。

---

## 3 追加式口径（与 W713 对齐，真正的"多轮对话"）

上一节的"温"是**原样重发**，测的是复用上限，**不能与 W713 的 5.866 s 直接比**。为此另跑追加式探针
（`/data/bench_prefix.py`，第 2 次在 prompt 末尾追加一句），档位与 W713 相同：

| 档 | 冷 TTFT | 温 TTFT | 温 cached | 引擎行 |
|---|---|---|---|---|
| 400 段（客户端计 18,085 / 引擎计 18,096 tok） | 45.04 / 39.37 s | **5.748 / 5.734 s** | 16,384 | `18096 tokens = 16384 reused + 1712 read in 5689 ms` |
| 150 段（客户端计 6,838 / 引擎计 6,849 tok） | 14.67 / 14.78 s | **14.679 / 14.721 s（等于冷）** | **0** | `6849 tokens = 0 reused + 6849 read in 14636 ms` |

- 400 段 vs W713 同档 **5.866 s**：本次 5.748 s = **-2.0%**，在分辨力（1.2-1.7%）边缘，**判定一致**。
- 150 段（<1 chunk）**reused 恒 0、温等于冷** ---- 与 W713 B1 的"<8k 任何值都无复用"结论**完全一致**。

=> **W713 的机制结论在 huihui 版上依然成立**（换权重不改机制，符合预期）。

---

## 4 对 W715 报告的两处更正

### 4.1 cache 槽归因错了：不是 `--vision`

W715 报告写"expert cache 从 10,289 掉到 9,757（-1.21 GiB），疑与 `--vision` 预留有关"。**本次同批次实测**：

| 项 | huihui (-407) | orig (-406) |
|---|---|---|
| free VRAM（取启动行 `expert cache auto` 的 free 值） | 22.88 GiB | 22.88 GiB |
| expert cache | **9757 槽 / 21.98 GiB** | **9758 槽 / 21.98 GiB** |
| prompt path 借槽 | 1554 槽 / 3.49 GiB | 1554 槽 / 3.49 GiB |
| 加载后 VRAM free | 572 MiB | 574 MiB |

（注：上表的 `free VRAM` 取自启动行 `expert cache auto: 22.88 GiB free, 700 MiB reserved ... -> 6779/6780 slots`；
日志里另有 `FileExpertSource: ... really free for a ... page-locked complement` 行（两臂为 25.10/13.49 与 12.37/23.77），
那是**分配 page-locked 时的瞬时可用量**，与 expert cache 的分配无关，两者不是同一指标，勿混。）

**两臂只差 1 槽** => `--vision` 不占 VRAM（我们走 CPU 编码器，符合预期）。
W715 里那个 10,289 是**更早时点**的启动读数，当时 GPU 的可用显存背景不同 => **不属于可比对照**。
**教训同 W714 的抽样事件：对照必须同批次。**

### 4.2 温 TTFT 有两个口径，不能混比

- **同 prompt 重发** => 复用全长，温 TTFT 0.11-0.15 s（这是**上限值**）。
- **末尾追加一句**（真实多轮）=> 复用受 checkpoint 边界限制，18k prompt 的温 TTFT 是 **5.75 s**。
- W715 报告没有用错这个数（它没写温 TTFT），但本轮中间汇报里说过"5.87 s 掉到 0.11 s"，**该说法错误、特此更正**。

---

## 5 遗留

1. **W715 遗留 #3**：`vision` 三个键（V00-V02）在 `verify_config.py` 里因 scope=CFG 被 SKIP，无独立核验。要闭合得给核验器加一条"读 config 的 vision 段并与 register 对撞"的判定。
2. **W715 遗留 #4**：答案级受控 A/B 未做。考虑到本工作区已实锤"**贪心也不保证可复现**"，该对照需要多次重复取多数才有判据，性价比低 ---- 建议维持"结构性证据"（native 路径 + PLE 分片 + compat-bf16 差异）。
3. 换权重后，此前 0.1.40.x 时代的其它档位读数仍需在 0.1.41 + 本模型上重取（本节只覆盖 3 档 + 2 档前缀）。
4. 其余待办不变：P31/P33 多轮缓存 · P23 CPU_SHARE · P29 GUMBEL · P28 GR_SPLIT · `--kv-grow` · C4 `_sshutil` 自包含 · C5 避坑回写 · C3 清理 · 向上游提 feature request。

---

## 6 过程与文件

- 探针源码：`waves/_w716_bench.py`（3 档 x 冷/温）与 166 上的 `/data/bench_prefix.py`（追加式）。
- §2 两臂原始输出：`deploy/tmp/_w716_arm_huihui.txt` / `_w716_arm_orig.txt`。
- §3 前缀探针原始行：166 `/data/strata-huihui-ud-iq4_xs.log` 行 218 / 229 / 244 / 254。
- §4.1 槽位读数原始行：-407 日志 `expert cache 9757 slots` / `pre-filled 9757 of 9757 ... in 38.6 s`；-406 日志的 9758 对应行。
- B6 源码证据：`deploy/tmp/_w716_b6.txt` / `_w716_b6b.txt`。
- register 变更：P30 CANDIDATE -> REJECTED（本机 md5 `af072c2e0db9688a7f13c3aff4edeb60`；40 行 / ADOPTED 20 / REJECTED 14 / CANDIDATE 6），已推 166 并两侧对齐。
- 两臂切换用的是既有容器（`-407` huihui / `-406` 官方 base），跑完已切回 `-407`；`-406` 仍为回滚位。
