# W966 · 代码级定位：0.8.0 的 MMQ 内核与 0.7.0 **逐字节等价**，0.8.0 可以跟

- 日期：2026-11-04 20:5x–22:0x
- 目标（机主）：不要停在"慢 6%"，要**具体到代码级**；而且 llama.cpp 要**紧跟上游**。
- 结论：**内核级没有任何退步证据**（指令体大小 + 寄存器 + 共享内存全同），
  **热态生产路径 A/B 三者等价**（0.4.1 503 / 0.8.0 497 / 0.1.55w 506 tok/s）⇒ 升级在性能上是安全的。
  我此前的 −6% 是**冷启动口径 + 噪声**，不是上游退步。

---

## 1 怎么做到"代码级"：把 `.hip_fatbin` 拆开看每个内核

```bash
llvm-objcopy --dump-section=.hip_fatbin=f.bin mmq-instance-q4_k.cu.o   # 得到 __CLANG_OFFLOAD_BUNDLE__
clang-offload-bundler -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f.bin -output=u.o
llvm-readelf -n u.o    # 每个内核的 .sgpr_count / .vgpr_count / .private_segment_fixed_size / .sgpr_spill_count
llvm-readelf -s u.o    # 每个内核的符号大小（= 指令字节数）
```

## 2 结果：我们实际跑的那个内核，两版一模一样

`pick_J` 在生产形状下选 **J=64、fallback=false、prec=Q8**（`W960` 已实测），对应符号
`_ZL9mul_mat_qIL9ggml_type12ELi64ELb0EL9ggml_prec30E…`：

| 项 | 0.7.0（无 fusion） | 0.8.0（fusion） |
|---|---:|---:|
| 内核符号大小 | **23,164 B** | **23,168 B** |
| sgpr | 44 | 44 |
| vgpr | 128 | 128 |
| private segment | 44 | 44 |
| sgpr spill | 0 | 0 |

⇒ **+4 字节**（一个 `if constexpr` 的边界），寄存器与私有内存**完全一致**，没有 spill。
`has_fusion=true` 的那个变体是 **48 B / sgpr 38 / vgpr 41** 的独立小内核，**不会被我们的调用选中**
（我们的 `fusion` 成员保持默认 `{}`，`gate == nullptr`）。

## 3 另外三个"可能是它"的，逐个排除

| 候选 | 结论 | 依据 |
|---|---|---|
| **#30553** stream-k cap（10-19） | **与我们无关** | `mmq-config-gcn.cuh` 里 Q4_K、J=64、fallback=false 的 CASE 第 8 个参数是 `false`（`stream_k=false`）；我们根本不走 stream-k |
| **#30087** GDN `cols_per_warp=4` | **不是 0.7→0.8 的差** | 0.7.0 与 0.8.0 的 `gated_delta_net.cu` **都是 9 处 `cols_per_warp`、默认 4** |
| **融合 loader 增加取数** | **不影响非 fused 实例** | 上面 §2：同一个 J=64/fallback=false 内核，代码大小与寄存器都没变 |

## 4 热态生产路径 A/B：三者等价

口径：production 的 `serve/server.py` + 项目自带 `ci/prefill_probe.py --quick`（`/v1/chat/completions` + streaming，
每个 cell 先打一次丢弃），**同一 1916-token prompt、同 config**，只换 `exe`：

| 引擎 | TTFT（3 次） | 吞吐 |
|---|---|---:|
| `strata-0.1.56`（0.4.1 + 我们的补丁） | 3810 / 3806 / 3797 ms | **503 tok/s** |
| `build-080c/strata`（0.8.0） | 3850 / 3884 / 3886 ms | **497 tok/s** |
| `strata-0.1.55w`（回滚件，0.2.9） | 3770 / 3803 / 3789 ms | **506 tok/s** |

⇒ 三者差 **≤1.8%**，在噪声内。**0.8.0 不慢**；`W960/W962` 的 −6%/−5% 是冷启动（每个容器第一段 prompt）测出来的，
那一段主要由**专家换入**支配，与内核无关——这也解释了为什么内核逐字节相同却"看起来慢"。

## 5 遗留异常（下一轮必须解决，否则绝对数值不可比）

三者都只有 ~500 tok/s @1916，而 `W863`（11-01 20:50，同一探针）是 **946 @1242 / 1231 @2468**。
关键线索：W863 记录"同一 prompt 第 2–5 次 **252 ms（14.6×）**"，而我这三次重复 **TTFT 全是 3.8 s，缓存一次都没命中**。

⇒ 我的 harness 里 **prompt cache 没生效**。最可能的原因：OpenAI 兼容接口要求请求带 `cache_prompt: true`
（`ci/prefill_probe.py` 没带），或者 wrapper 侧把缓存关了。
**在这一点查清之前，"500 vs 946"不能算生产退步，只能算口径不同。**

## 6 对"紧跟上游"的建议

1. **性能上可以跟**：内核等价 + 热态等价，没有理由因为 prefill 拒绝 0.8.0。
2. 跟之前要补的两件事（`W956 §5.1`、`W961 §5`）：
   - overlay 的 trellis 段要适配 `ggml_cuda_mmq_util_funcs(..., prec)`（否则只能 `STRATA_MMQ_TQ_OVERLAY=OFF`，我们不用 trellis，可接受但要显式）；
   - **摘 `#29953` 的越界 padding**（`ids_dst` + `J-1`、`src1_q8_1` 按 `nthreads` 上取整）——这是我们 0.4.1 缺的正确性修复。
3. 真正的下一步不是继续比 0.4.1 vs 0.8.0，而是**把缓存口径查清**，然后六长度档 A/B 一次定稿。

## 7 复现

```bash
bash albus/w966/res2.sh <070.o> <080.o>   # 内核资源
bash albus/w966/size.sh <070.o> <080.o>   # 内核代码大小
bash albus/w966/warm2.sh                  # 热态两臂（wrapper + 项目探针）
bash albus/w967/warm_155w.sh              # 回滚件同口径
```
