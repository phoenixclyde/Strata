# W773：P46 io-预取族的 decode 面（`STRATA_IO_PREFETCH`）

日期 2026-10-10 23:32 ~ 2026-10-11 00:12 ｜ 引擎 0.1.41（`160611838796d4b172ec3a642ccd988d`）｜ MI50 32GB (gfx906)
｜ 发车 PID 3019757 ｜ 4 臂交错 `A B A2 B2`，`ARMS_FAIL=0`，pull 9/9

## 0 为什么只测这一个

侦察把 `P46` 那条"族行"（`STRATA_{IO_PREFETCH,FILL_AHEAD,FS_AHEAD,FETCH_THREADS}`）**拆开了**，四条不是一个东西：

| 子项 | 源码/文档依据 | 判定 |
|---|---|---|
| **`STRATA_IO_PREFETCH=1`** | `docs/DETAILS.md:223-227`：Linux file-tier I/O path，**未命中专家 + 下一层路由预测的**专家改由 I/O 线程 whole-blob `pread` 预读；`generate.cpp:4179-4188`；**上游声明输出逐位相同**（greedy IQ3_XXS / Q2_0 哈希相等） | **本轮测它**（唯一直接对口 decode） |
| `STRATA_FETCH_THREADS` | `expert_source.hpp:619`：只作用于 GGUF-in-place 的未命中装配，默认 8 | **同路径，不组合测**（W723） |
| `STRATA_FILL_AHEAD` | `docs/DETAILS.md:280-284`：面向上线**填充**时间（Gen3 NVMe 上 ready 70 s vs 920 s） | 不对口 decode，未测 |
| `STRATA_FS_AHEAD` | `docs/DETAILS.md:1437-1444`：只是 `STRATA_FS_SLOTS` 的子开关，而后者**上游在每台测过的机器上都是负的**（decode 比 0.91-1.00） | **不单独测** |

**启用前提（源码定死，`expert_source.cpp:560-587`）**：Linux + 有 mapped base + paths 可 open + **`direct_` 为空（不是 unbuffered）** => 才置 `io_pf_=true`；
`generate.cpp:4182-4188` 的**两个分支都会打印**（ON 或 not available）=> **必须读引擎自己的启动行**才知道生效与否（"用户传参 != 运行期生效值"）。

## 1 设计（单变量，断言逐位）

| 臂 | config 的 `env` 段 | 其它 |
|---|---|---|
| `A` / `A2` | 生产原样（`HSA_OVERRIDE_GFX_VERSION=9.0.6` + `STRATA_PREFILL_CPU_SHARE=0`） | `args` **逐位不动** |
| `B` / `B2` | 上者 + **`STRATA_IO_PREFETCH=1`** | 同上 |

- 造臂断言：`A/A2` 的差异键 = `['log','port']`；`B/B2` = `['env','log','port']` 且 **env 只多这一个键**、`args` 逐位不动。
- 负载 `_w773_speed.py`：`32768` 与 `128000` 各 **2 runs**、`max_tokens 256`、greedy、每 run 头部新 nonce => **`reused` 全 0**（4 臂 16 个读数，`非 0 = none`）。
- 该客户端**新加抓了 `expert tiers` 行与 `file tier I/O this request` 行** ---- 那是本族的**机制指标**。
- 过闸门：heredoc 抽取本机实跑（`HEREDOC_RUN_OK`）+ 远端 `bash -n OK` + `py_compile OK` + 两侧 md5 一致。

## 2 机制证据（**本车的判据本体，与读数无关**）

| 层 | 原文 |
|---|---|
| 配置 | `env` 含 `STRATA_IO_PREFETCH: "1"` |
| **运行期** | 引擎 `/proc/12` 的 environ 含 **`STRATA_IO_PREFETCH=1`** |
| 启动 | **`strata generate: file tier io prefetch ON (STRATA_IO_PREFETCH=1): whole-blob preads, the layer's uncached experts and the predicted ones read by 8 I/O threads (STRATA_IO_PF_THREADS, default 8)`** |
| **实际动作** | 每请求 **`io prefetch: 0 read ahead (0.0 MB by pread), 0 used, 0 unused, 0 skipped (cached), 0 dropped`** ---- **4/4 读数全 0** |
| **为什么** | 同一行：`the OS read 998.5 MB from storage (1 major faults) for **42282.7 MB** of expert reads; **page cache held 78191.7 MB** at the read`；启动日志：`the file tier reads through the file cache (... **0.0 GiB of experts read from the files**)` |

**=> 参数把机制开起来了，但它无对象可用**：专家读几乎全命中 page cache / RAM copy（本机 128.7 GiB RAM + `--resident-budget-gib 76`），
**每 42 GB 的专家读里只有约 1 GB 真从 storage 来** => **没有"未命中的文件读"可供预读** => 预取 0 次。

## 3 读数（三口径；**都不可判，见 §4**）

| 口径 | len 32768（ON/OFF 中位比） | len 128000 |
|---|---|---|
| `decode tok/s`（引擎自报） | **1.0013** | **0.9469** |
| `ms / drafts-offered 轮` | 1.0597 | 1.0458 |
| `ms / checkpoint` | 1.0410 | 1.0569 |

（`tok/s` 受**草稿净出污染** ---- 本车 `gen` 从 41 到 256、`offered` 从 21 到 207，两个口径都受它影响。
`ms/offered` 与 `ms/ckpt` 也**不是干净口径**：各轮耗时本身受**命中率**影响，而命中率在 82.2%~95.0% 间摆动。）

## 4 噪声底（本车**不可判小效应**）

臂内 spread（同臂同长度的两个 run 之差 / 中位）：

| 口径 | 观察 |
|---|---|
| `decode tok/s` | **0.0% ~ 27.1%**（B 的 32768 恰好 0%，B2 的 32768 达 27.1%） |
| `ms/offered` | 8.4% ~ **60.3%** |
| `ms/ckpt` | 1.1% ~ **132.6%** |

=> **远大于"可能的效应"**。对照：W760 那次同形状自比的噪声底是 **0.3%**（64K 上下文、每臂 1 冷 + 4 温、同一段文本）。
本车用**不同 nonce 的不同文本**、每格只 2 runs => 噪声底大一个量级。

**=> 本车的结论不能从读数得出，只能从机制得出。**

## 5 结论与判定

**`STRATA_IO_PREFETCH=1` 在本机无收益，且机制上不可能有**（预取 0 次）。

- 它**不是"参数无效"** ---- 引擎确实把它 ON 了（运行期 environ + 启动行都证实）。
- 它是"**瓶颈不在 file-tier I/O**"：专家的文件读几乎全被 page cache 吃掉。
- **判定：REJECTED（本机配置下前提不成立）**，登记为 `P54`。
- 该族其余：`STRATA_FS_AHEAD` 不单独测（依赖上游已证负的 `FS_SLOTS`）；`STRATA_FETCH_THREADS`（同路径）与 `STRATA_FILL_AHEAD`（面向上线）**仍未测** ---- `P46` 保留为 CANDIDATE。

**这条结论的方法学价值**：**"参数生效"与"参数有用"是两件事，必须分别取证** ----
本轮若只看"env 设了/日志说 ON"，会误判为"已生效、值得期待"；只有去读**它自己的动作计数**（`0 read ahead`）才知道它什么都没做。
这与既有的「用户传参 != 运行期生效值」是同一族判据的**下一步**：**运行期生效 != 实际动作**。

## 6 局限（照实写）

- **读数不可判**（噪声底 10-27%），所以"无收益"的依据是**机制**（预取 0 次），不是"读数打平"。若要在读数上判，需要**同文本多次重复**（像 W760 那样）与更高的 run 数。
- 未测 `STRATA_FETCH_THREADS` / `STRATA_FILL_AHEAD`（前者同路径、后者不对口 decode）。
- 未测 `STRATA_IO_PF_THREADS` / `STRATA_IO_PREFETCH_DEPTH`（`IO_PREFETCH` 生效的前提下它们才有意义）。
- 本车的"专家几乎全在缓存"是**本机 RAM 预算下的现象**；若把 `--resident-budget-gib` 调小或 pack 更大、专家装不进 RAM，file-tier I/O 会变成主路径，那时这条结论不适用。

## 7 落盘

`deploy/tmp/_w773_rc.sh`（驱动器）· `_w773_speed.py`（客户端，**新增抓 `expert tiers` 与 `file tier I/O` 行**）· `_w773_an2.py`（分析器，三口径 + 机制）·
`_w773_{A,B,A2,B2}.log`（各 10 KB）· `_w773_speed_{A,B,A2,B2}.json` · `_w773_ab.out`（8,070 B）· `_w773_pfcheck2.py`（机制取证）·
`PARAM_REGISTER.tsv` 的 `P54` + `P46` 更新 · `W713_PLAN.md §6.1` 第 46 条。
