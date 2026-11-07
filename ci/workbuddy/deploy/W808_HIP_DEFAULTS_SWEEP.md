# W808 · 「HIP 默认关 / CUDA 默认开」这一类开关的清算：全平或全负，解码侧被 GPU 计算锁死

日期：2026-10-26 21:44-22:3x ｜ 生产：`strata166-407` / `strata-gfx906:0.2.4p4` / 引擎 0.1.49.2 / env 12 项
结论先行：**这一类开关一个都不值钱**（−0.3% / −0.6% / −6.3%），而相位分解说明了原因 ——
**一手解码 44.19 ms 里有 31.85 ms（72%）是纯 GPU 计算等待**，能省的 host 侧总共只有 9.4%，`commit/emit` 只有 0.04 ms。

> **【AUDIT10 更正 2026-10-26 23:4x】补一条从未记录的事实（结论不变）：**
> **`STRATA_DECODE_TIMING=1` 自身让 decode 从 50.74 掉到 42.69 tok/s（−15.9%）**——同配置 P 臂，
> `w808_hipdef`（无仪器）对 `w808c_dectiming`（有仪器）。
> ⇒ (1)本文 §3 的相位百分比只能与同批 DT 行的 `ms/window` 相互比较，**不能拿去和非仪器的 tok/s 换算**；
> (2)它同时是 `W802 §3.3` 那个 T0 decode **+37.5%** 异常最可能的解释（当时只写「仪器 x share 相互作用」，没有量）。
> 另：四臂 tok/s 与 DT 相位（44.19 = 38.71(31.85+4.16+0.05)+0.04+3.82）经独立重算逐字一致。

---

## 0 四条结论

1. **扫出一类、清掉三个**：`P132`（`FUSE_HITS`）、`P133`（`HEAD_MIX_MULTI`）、`P134`（`ONE_TOKEN_COMMIT`）全部 REJECTED，
   decode tok/s 中位 50.74 / **50.58 / 50.43 / 47.55**。
2. **为什么全平**：`FUSE_HITS` 折的是 `moe_hit_add` 进 combine（旧 stages 行里 `copy+combine` 只有 **0.70 ms**），
   `HEAD_MIX_MULTI` 只省 launch，`ONE_TOKEN_COMMIT` 能省的 `commit/emit` 实测只有 **0.04 ms/window（0.1%）**。
3. **解码是 GPU 计算受限**：`GPU-reach wait 31.85 / 44.19 ms`，avg T 2.30、**1.89 token/window**（有草稿），
   即 M≈2 的专家 GEMV 打满。**参数面在解码侧到此为止。**
4. **顺手纠正我自己的两处错**：解码相位的开关是 **`STRATA_DECODE_TIMING`**（不是 `STRATA_TRACE`）；
   日志里旧的 `VRAM hits 10.99`（ms/window，stage profile）与 DT 行的 `VRAM hits 21.22`（**µs/layer-window**）**不是同一个量**，不能并列引用。

---

## 1 这一类开关是怎么找出来的

`W806` 的教训是「宏缺失 ⇒ 走进 CUDA 分支 ⇒ 把 CUDA 默认带进来」（被动泄漏，P127）。
但源码里还有**方向相反**的一类：函数自己写了

```cpp
bool xxx_on() {
#if defined(STRATA_USE_HIP)
    ... return v != nullptr && ...;      // HIP: opt-in
#else
    ... return v == nullptr || ...;      // CUDA: default ON
#endif
}
```

于是**我们这类构建主动关掉了 CUDA 上默认开的东西**。写了个扫描器（`albus/w808/scan_hip_defaults.py`，
按括号配平切函数体、比对两个分支的 getenv 三态）在 `src/` 里扫，得到 **8 个**：

| env | 函数 | HIP 默认 | 非 HIP 默认 | 位置 |
|---|---|---|---|---|
| `STRATA_ONE_TOKEN_COMMIT` | `one_token_self_commit` | 关（opt-in） | **开** | `verify.cpp:398` |
| `STRATA_HEAD_MIX_MULTI` | `head_mix_multi_enabled` | 关（opt-in） | **开** | `verify.cpp:297` |
| `STRATA_SH_STREAM` | `sh_stream_on` | 关 | **开** | `verify.cpp:260`（W798 已测，-10.8% 否决） |
| `STRATA_MTP_PREFILL_SYNC` | `prefill_per_group_sync` | **开** | 关 | `mtp.cpp:1377`（我们已是开） |
| `STRATA_FUSE_HITS` | `fuse_hits_on` | 关（arch=gfx12 才开） | 关 | `verify.cpp:381` |
| `STRATA_FUSE_CONVAB` | `fuse_convab_on` | 关 | 关 | 上游自报 gfx1201 −0.3%，跳过 |
| `STRATA_FUSE_WAIT` | `fuse_rows_on` | 关 | 关 | 上游只在 sm75 量过，跳过 |
| `STRATA_GFX12_DEFAULTS`/`hc_q8_env` | — | 关 | 关 | 我们已用 `HC_Q8=1` 显式开 |

取前三个（+ `FUSE_HITS`，因为它的名字直指 `VRAM hits`）做 A/B。

---

## 2 A/B：三条臂全平或全负

口径：3 条不同 prompt（`dec_corpus` 前三条，各 200 token，`temperature 0`），
`decode_ms` 与 `output_tokens` 取自服务端 `/metrics` 的逐请求记录（不含客户端开销）；每臂一次装载，`ENVCHECK` 全过。

| 臂 | p0 | p1 | p2 | **中位 tok/s** | 相对生产 |
|---|---|---|---|---|---|
| **P**（现役 12 项） | 45.1 | 51.6 | 50.7 | **50.74** | — |
| **H** `HEAD_MIX_MULTI=1` | 46.2 | 50.6 | 52.8 | **50.58** | **−0.3%** |
| **F** `FUSE_HITS=1` | 47.0 | 52.4 | 50.4 | **50.43** | **−0.6%** |
| **O** `ONE_TOKEN_COMMIT=1` | 46.0 | 52.0 | 47.5 | **47.55** | **−6.3%** |

同臂内 p0..p2 的极差是 5.4-6.5 tok/s（**prompt 之间的差异，不是重复噪声**）；四条臂跑同样的三条 prompt、同序，所以中位可比。
⇒ **H、F 落在噪声内（都是略负），O 明显变慢。**

---

## 3 相位分解：解码的钱花在哪（`STRATA_DECODE_TIMING=1`，现役配置）

臂 P（生产配置）逐字：

```
106 windows, avg T 2.30, 1.89 tokens/window, 44.19 ms/window
  = verify 38.71 (GPU-reach wait 31.85 + per-layer host 4.16 [plan 0.15 actq 0.14 jobs 0.04 CPU 3.76] + stage 0.05)
  + commit/emit 0.04 + draft 3.82
per layer-window: CPU experts 0.80 (0.98 entries), VRAM hits 21.22, PCIe 0.01
adapt wait 1.60 join 0.00, 15.4 swaps/window
prompt 76 tokens read in 1263 ms (60.2 tok/s), 200 generated in 4685 ms (42.7 tok/s), drafts accepted 94 of 138
```

| 项 | ms/window | 占 44.19 |
|---|---|---|
| **GPU-reach wait（纯计算等待）** | **31.85** | **72.1%** |
| per-layer host（plan / actq / jobs / **CPU experts**） | 4.16（3.76 是 CPU experts） | 9.4% |
| **draft（草稿头）** | **3.82** | **8.6%** |
| commit / emit | **0.04** | **0.1%** |
| stage | 0.05 | 0.1% |
| 其余（adapt wait 等） | ≈1.6-2.6 | 4-6% |

**三条结论**：

1. **`commit/emit` 只有 0.04 ms** —— 所以 `ONE_TOKEN_COMMIT` 想省的那张图**本来就不值钱**。
   实测 −6.3% 的差异不在这 0.04 上：O 臂的 **drafts accepted 只有 80/126（63.5%）、120 windows**，
   而 P 臂是 **94/138（68.1%）、106 windows** —— 自提交路径改变了草稿头看到的状态，接受率掉了，
   于是每个 token 要更多窗口。机制未查透，但**判死的依据足够**：连"省 0.1%"都没挣到，还改了草稿接受率。
2. **`FUSE_HITS` 折的不是大头**：它把 `moe_hit_add` 折进 combine，而旧的 stages 行里 `copy+combine` 只有 **0.70 ms**；
   DT 行里 `VRAM hits` 折算下来也只是**每层每窗 ~21 µs（×47 层 ≈ 1.0 ms/window）**。所以 −0.6% 是它应得的结果。
3. **host 侧整体只有 9.4%**，其中最大的一块是 `CPU experts 3.76 ms/window`（缺失专家由处理器算的那部分）。
   这就是「解码再想快，只能让 GPU 那 31.85 ms 变短」的意思。

---

## 4 两处必须写下来的纠正（都是我前几轮的错）

1. **解码相位的开关不是 `STRATA_TRACE`。** `generate.cpp:14044` 逐字：
   `static const bool dec_timing = std::getenv("STRATA_DECODE_TIMING") != nullptr;`。
   本轮先用 `STRATA_TRACE=1` 跑了一遍，结果**一行相位都没打印**（只有一个 `MEDIAN 42.80` 的空跑）。
   教训：**仪器的开关名字不要凭印象**，先去源码 grep 打印点。
2. **`VRAM hits` 有两个不同单位的读数，不能并列。**
   - 旧 `decode GPU stages (ms/window)` 行里的 `VRAM hits 10.99` → 单位是 **ms/window**（`profile_report()` 按 stage 归集）；
   - 本轮 DT 行的 `VRAM hits 21.22` → 单位是 **µs/layer-window**（`d1.hits / (w * L)`），×47 层 ≈ 1.0 ms/window。
   同一个名字、差 10 倍。谁要把两行抄进同一张表，就会得到矛盾结论 —— 这正是 `AUDIT9` 立的那条「列名必须绑定来源」的同类错误。

顺带一条**正面的**新读数：长写作 prompt 的 decode **确实在吃草稿**（`drafts accepted 94 of 138`、avg T 2.30、1.89 token/window），
而短回答请求是 `0 of 0`。这解释了 `P127` 的 `RT_SKIP` 为什么在生产里 96% 生效，也说明 `W807` 的长生成发散测量是在**开关真正生效的条件**下做的。

---

## 5 解码侧还剩什么（有数据的三条）

| 项 | 读数 | 还能动吗 |
|---|---|---|
| GPU-reach wait 31.85 ms（72%） | M≈2 的量化专家 GEMV | **只能改内核**（要重建镜像 + 回归），没有现成旋钮 |
| draft 3.82 ms（8.6%）买 0.89 额外 token/window | 68.1% 接受率 | **唯一还没系统扫过的**：草稿深度 / `--spec-min-p` 的取值 |
| CPU experts 3.76 ms（8.5%） | 缺失专家在处理器上算的那部分 | 与 `--pcie-frac`（现 0.20）耦合，属于"搬运 vs 计算"的老平衡 |

⇒ 下一轮如果继续做解码，**先扫草稿深度**（成本低、不需要重建镜像、且已有 68% 接受率的基础），
再看 `--pcie-frac` 与 `CPU experts` 的折中。内核那条（M<=4 的专家 GEMV）留作重建镜像级的工作。

---

## 6 生产状态与证据

| 项 | 读数 |
|---|---|
| 镜像 / 引擎 | `0.2.4p4` / 0.1.49.2（二进制未动） |
| 配置 | env **12 项**（无 `STRATA_DECODE_TIMING`、无三个候选键），`--prefill auto`、`RT_SKIP=7`、`CPU_SHARE=auto` |

| 件 | 说明 |
|---|---|
| `albus/w808/scan_hip_defaults.py` | 扫描器（8 个候选的来源） |
| `albus/w808/w808_gen_{P,H,F,O}.json` | 四臂逐条 `prompt_ms/decode_ms/output_tokens/decode_tps` |
| `/data/w808_hipdef_*.txt` · `w808c_dectiming_*.txt`（166 上） | A/B 全程 + 相位车（含 DT 行原文、trap 恢复） |
| `albus/r5/{ab_p35,ab_p36}.sh` · `mt_gen.py` | 驱动器 / tok/s 客户端 |
