# AUDIT17 整改台账（逐条结清）+ W863 新发现

> **AUDIT19 后续（2026-11-01 19:0x）**：本件 15 条**全部维持已结**，无回退。
> 但它里面所有「占峰值 x%」用的分母（~700 GB/s）已被实测取代 —— **读屋顶 803–884 GB/s**，
> 重算见 `AUDIT19_ROOFLINE_REMEDIATION.md §2`。本件的**结论**不受影响，**比例数字**以 AUDIT19 为准。
>
> **【AUDIT22 再更正 · 2026-11-02】这条指针本身也需要加一层限定**：`AUDIT19` 的 884 GB/s 是**大块连续读**的屋顶，`W875`（`P250`）实测 M≈3–4 的 GEMV 只有 **280–350**。
> 所以「比例数字以 AUDIT19 为准」只在**形状接近大块读**时成立；本件里涉及 HC / QSA / 专家 GEMV 的百分比，**不能**按 884 读「还剩多少」。

> 2026-11-01 15:1x–15:3x。本件是 **AUDIT17 的收口**：每条给「判 / 落在哪 / 证据」，不再留「下一轮」。
> 同时登记 W863 自己查出来的 5 条（其中 2 条是**制度级**问题）。
> 口径：**能机器验的都给命令**；不能验的明确写「文档级」。

---

## 0 总判

AUDIT17 的 **15 条全部结清**（P0 3 / P1 6 / P2 5 / P3 1），另新增 **W863-1…5**。
其中真正改变结论的是三条：

1. **P0-1 结清后，「每 token 的 dense GEMV」从「59% / 16% 两个互相矛盾的数字」变成一个可对账的数**：
   **37.8%（16.99 / 44.98 ms 每窗口）**，且与引擎日志逐字节吻合（499 矩阵 / 3619.14 MiB）。
2. **P1-4 结清后，R 表从「公式」变成 216 格实测表**，并已上生产（0.1.55h），实测 **+4.0%**。
3. **W863-1 是 AUDIT17 漏掉的制度漏洞**：文档承诺的运行期回滚开关 `STRATA_MMVQ_WAVE_ROWS`
   **在代码里根本不存在**（只有一行注释）。凡是「文档说能回滚」的地方，以后必须用 `strings`/`nm` 验一次。

---

## 1 AUDIT17 逐条

| 编号 | 原判 | 现状 | 落在哪 / 证据 |
|---|---|---|---|
| **P0-1** | 「每 token dense GEMV」两轮都算错且矛盾 | **结** | `W863_R22_DENSE_BYTES.md`：从 GGUF 张量表逐层枚举（GDN 6 张量 63.42 MiB / QSA 7 张量 55.45 MiB，36/12），与日志 **499 矩阵 / 3619.14 MiB** 逐字节吻合；每窗口 dense Q8_0 = **4263.24 MiB**，占 **37.8%**；除数三分开写（窗口 / 接受 token ÷1.79 / 列 ÷2.26） |
| **P0-2** | W861 §3 表不可复现（22% vs 45–71%） | **结** | AUDIT17 当轮已在 `W861_DECODE_BANDWIDTH.md` 加更正横幅；W863 复核横幅仍在、且与 W862 重测值一致 |
| **P0-3** | gfx906 hsaco 三个字节数、文件名与尺寸配对错 | **制度结，文档待标** | 规则已立：每次 codegen 记「文件名 + 字节 + md5 + config」四件套（见 §3 铁律 6）。`W861_HIPBLASLT_GFX906.md` 已加四件套要求；三个历史字节数**不再作为证据引用**（结论靠结构论证） |
| **P1-1** | W857 的 ring 负对照是单臂无重复却写成定论 | **结** | `W857_R17_MMQ_AND_R15.md` 顶部横幅：**降级 UNRESOLVED**，写明 B 臂 TIMING 丢失、每档 n=1、要重跑须两臂都带 TIMING 且 ≥2 rep 交错 |
| **P1-2** | W856 的 hipBLASLt「P0=BLOCK」没回填 | **结** | `W856_TRIPLE_LINE.md` 顶部横幅：「已被 W858 §1 解掉，终局见 W861」 |
| **P1-3** | W862 改了生产源码树但没部署（潜在静默变更） | **结** | 选择「① 保留并上生产」：0.1.55h 已部署（`W863_R23_DEPLOY.md`），源码树现在是**分支提交** `78fa2a72`，不再是游离的工作树改动 |
| **P1-4** | R 表是公式不是实测表 | **结** | `W863_WAVE_ROWS_TABLE.md`：9 形状 × ncols 1..8 × R∈{1,2,4} = **216 格**；整层 n1 1.000 / n2 1.156 / n3 1.829 / n6 1.593；已替换公式并上生产 |
| **P1-5** | W861 hipBLASLt `DONE_NEG` 理由引用作废数字 | **结** | `W861_DECODE_BANDWIDTH.md` §4 顶部：改为结构论证（gfx906 无矩阵指令 ⇒ VALU ⇒ 与 rocBLAS 同构 + 17 个 `MI*` 字段无维护 ⇒ 有静默算错风险） |
| **P1-6** | 「不动进程」被当成「不动资产」 | **结** | 见 §3 铁律 5（改工作树=改生产资产，须登记文件名/备份/回滚）；本轮 `W863_R23_DEPLOY.md` §5 就是按这条做的 |
| **P2-1** | 自足内核基线比生产慢 4% | **结** | 结论保留在 `W863_WAVE_ROWS_TABLE.md`：lab 只筛方向、落数回真实 kernel（本轮 216 格全部用真实 kernel） |
| **P2-2** | 手工重编两次污染结论（漏 `-DNDEBUG` 慢 47%、错 include 慢 45%） | **结 + 工具化** | 本轮**没有手工抄 flag**：编译/归档/链接三条命令全部由 `ninja -t commands strata` 逐字取出（`albus/w863/d11_build3.sh`），从机制上消灭这类污染 |
| **P2-3** | W857 相位表「各 3 次」实为 2 warm + 1 rep | **结** | 与 P1-1 同一横幅处理；本轮 A/B 明确写「丢弃前 2 请求 + 每臂 3 次」 |
| **P2-4** | 账本没有 W862 行、R22 状态不符 | **结** | `PROGRESS.tsv`：R22 → DONE（W863-1）、R23 → DONE（W863-3），备份 `.w863bak` / `.w863b` |
| **P2-5** | 「除列数」与「除接受 token」混用 | **结** | 已在 `W863_R22_DENSE_BYTES.md` §4 用一张表把三个除数并排写死；并升级为铁律 4 |
| **P3-1** | W858 两份文档对 B 线价值表述不一致 | **结** | `W858_THREE_LINES.md` 加统一口径横幅：**结构等价 + 上游路径未维护**，不再挂性能数字 |

---

## 2 W863 新发现（5 条，其中 2 条制度级）

| 编号 | 问题 | 级别 | 处置 |
|---|---|---|---|
| **W863-1** | **文档承诺的 `STRATA_MMVQ_WAVE_ROWS` 回滚开关在代码里不存在**（全树只命中一行注释，无 `getenv`） | **制度** | 已实现（`wave_rows_env()`）；判据：`strings` 0→1、`nm wave_rows_for|kWaveRows` 0→2。**新铁律 9：凡文档说「env 可回滚」，必须用 `strings` 验一次** |
| **W863-2** | `deploy/params/gen_config.py` 的 `META` 停在旧部署（`exe=/src/build-906/strata`、tokenizer/PLE 指 `huihui-ud-iq4_xs`），现在跑 `--write` 会把生产 config 写坏 | **P1** | 本轮改 config 改走「备份 + 定点改 `exe` 一个字段」。修 gen_config 需连同 PARAM_REGISTER 一起对齐 0.2.9，列入下一轮 |
| **W863-3** | `build.ninja` **无法重生成**：`CMakeLists.txt:1973` 的 `add_subdirectory("/llama.cpp/ggml")` 需要 166 上没有的 checkout；且 ninja 每次都先跑 `VerifyGlobs` 而确有一个 glob 不符 ⇒ 必然触发重生成 ⇒ `ninja` 直接可用性为零 | **P1** | 绕开方式：只用 `ninja -t commands` 取命令（`d11_build3.sh`）。根治要么补 `/llama.cpp` 挂载、要么把该 `add_subdirectory` 改成条件式（可提上游） |
| **W863-4** | **R23 的收益被窗口长度卡死**：生产典型验证窗口 **T≈2**（drafts ≈0.9/窗口），1.52× 只在 T=6 成立；实际墙钟 4.0% | **P0（认知级）** | 见 `W863_WAVE_ROWS_TABLE.md` §4 与 `W863_SINGLE_STREAM_PLAN.md`；机理是 `generate.cpp:13128` 用 `--spec-min-p 0.70` 截断草稿链 |
| **W863-5** | **本地 clone 是 shallow/grafted**（`.git/shallow` 18 行），导致 ①`git merge-base` 直接报错 ②`rev-list --count` 把「落后两个版本」算成「落后 1 个提交」③在 main 上 rebase 会把它当根提交整树重放（本轮真踩了，已 abort 恢复） | **P1（方法级）** | **新铁律 10：任何「落后几个提交」的结论，必须先用 GitHub API 或 `git rev-parse <tag>^{commit}` 交叉验证，不能只看本地 `rev-list`**。本轮据此发现 fork main 实际停在 **v0.1.40.2**，已对齐到 v0.2.9 |

---

## 3 本轮新增/确认的铁律（写入记忆件 §1）

| 序 | 铁律 | 触发它的证据 |
|---|---|---|
| 4 | **每 token 折算必须写明除数**（窗口 / 接受 token / 列，三者差 2.5–2.6 倍） | AUDIT17 P0-1 |
| 5 | **改 `pr/strata-fork` 工作树 = 改生产资产**：须登记「改了哪个文件 / 备份在哪 / 怎么回滚」 | AUDIT17 P1-6 |
| 6 | **codegen 产物记四件套**：文件名 + 字节 + md5 + config | AUDIT17 P0-3 |
| 7 | **重编不许手抄 flag**：一律从 `ninja -t commands` 逐字取（本轮因此免疫 P2-2 的 47% / 45% 污染） | AUDIT17 P2-2 |
| 8 | **判「功能在不在二进制里」只认**：①编译行 `-D` ②独有符号/字符串 ③无条件横幅（不认 CMake 选项与 cache） | W856（老）＋ W863-1（新） |
| 9 | **文档说「env 可回滚」必须验**：`strings <bin> \| grep <VAR>`，为空就是没有 | W863-1 |
| 10 | **历史/落后结论必须交叉验证**：本地是 shallow clone，`rev-list` 会骗人；用 GitHub API 或 tag 解引用 | W863-5 |

---

## 4 复核命令（可机器跑）

```bash
# P1-3 / P1-4：生产是不是跑在 0.1.55h，且二进制有 R 表
docker exec strata166-407 ps -eo cmd | grep -c strata-0.1.55h
nm -C /home/albus/strata166/data/bin/strata-0.1.55h | grep -c 'wave_rows_for\|kWaveRows'   # 期望 2
strings -a /home/albus/strata166/data/bin/strata-0.1.55h | grep -c STRATA_MMVQ_WAVE_ROWS    # 期望 1

# W863-5：本地 clone 是不是浅的
git -C /home/albus/strata166/pr/strata-fork rev-parse --is-shallow-repository                # true

# §1 P0-1：账目对不对
grep -a "native projection matrices" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -1
# 期望 499 ... 3619.14 MiB

# 分支对齐（只往 fork 推；upstream 的 push URL 是 DISABLED-no-push-to-upstream）
git -C /home/albus/strata166/pr/strata-fork config --get-all remote.upstream.pushurl
```
