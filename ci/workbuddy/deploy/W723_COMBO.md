# W723 ---- 三项组合可行性：P28 `STRATA_GR_SPLIT` / P29 `STRATA_SPEC_GUMBEL` / P32 `--kv-grow`

- 日期：2026-10-09 20:0x（本机时间）
- 缘起：机主问「这三个组合起来可以吗？」
- **结论先说**：**技术上可共存（三处机制互不互斥），但不建议组合测** ---- 三项**全在分辨力以下**，
  且 **P28 与 P29 同在 spec/MTP 路径**（组合 => 归因不可分）；P28 另有一票否决（破坏位一致）。
  **唯一值得单独验的组合点是 P32 x P31**（`--kv-grow` 与 conversation cache 在 K/V 保留上真交互）。

---

## 0 一个必须先纠正的前提：P28 在本机**是可达的**（区别于 P30）

P30 的判据是「HIP 分支 `return false`」=> **结构性不可达**。**P28 不是这种情况**：
它的实现在 `#if defined(STRATA_HIP_GFX906)` 之内（`fused_gr.cu:1748`），而 **gfx906 构建正是定义了这个宏**
（`-DSTRATA_HIP_GFX906`，W718 实测 `compile_commands.json` 出现 26 次）。所以：

- P28 的代码**编进去了、运行期可达**；只是 `split_on` 默认为 false（env 未设）；
- 它的宿主 `fused_gr_read_multi` **在本机确实被调用**（见 §1）=> `STRATA_GR_SPLIT=1` 一设就会生效。

=> 「默认关」不等于「不可达」；**P28 是"可达但已被否"，P30 是"不可达"**，两者不同类。

---

## 1 路径分布：不是三个并列项，而是 2 + 1

| 项 | 宿主 | 机制 | 路径 |
|---|---|---|---|
| P28 | `fused_gr_read_multi`（`fused_gr.cu:1760/1762`；**W735 更正**行号，原写 1762/1766） | env `STRATA_GR_SPLIT` | **spec/MTP** |
| P29 | sampler pick（`sampler.cu:1242/1320`） | env `STRATA_SPEC_GUMBEL` | **spec/MTP** |
| P32 | 弹性 K/V（`layer.cpp:520` / `generate.cpp:3788`） | CLI `--kv-grow` | 显存 |

**P28 与 P29 同路径** -- 证据：

- `fused_gr_read_multi` 的调用者 = `mtp.cpp:723/838/946/957`（草案层）+ `verify.cpp:940/1555/1573/1588`（验证窗口）；
- P29 的用途原文（`sampler.cu:66`）："GUMBEL-MAX COUPLING ... The pick is argmax_i p_i / E_i ... a drafter whose
  candidate set differs from the target's still agrees with it on the tokens they share (support invariant).
  **The MTP drafter keys on the draft's token id**" ---- 它本身就是为 spec couple 设计的；
- 现役 config 开着 `--spec 4` / `--spec-min-p 0.70` / `--mtp /data/mtp/rt` => **这条路径在跑**。

---

## 2 组合的三个问题

### 2.1 分辨力：各项的收益上限本来就在门槛下

| 项 | 收益上限 | 来源 |
|---|---|---|
| P28 | ~3% / verify window | 文档 `AMD_HIP.md:482` + 源码注释 |
| P29 | 0（我们默认贪心 => 空操作） | `server.py:576`；config 无 sampling 段 |
| P32 | +89 槽（0.91%） | 204 MiB / 2.30 MiB per 槽（W720；**W735 更正**单位，原 93/0.95%） |

三者**同属 W721 的"0~3% 桶"**（非重复计算类）。三项相加的上限也不足 5%，仍低于解码分辨力
（9.5~15%）。**组合不会让桶 C 变成桶 A。**

### 2.2 归因：P28 x P29 同路径 => 组合即不可分

P28 改的是**目标模型的 GR 读**（重排求和 => 数值微变 => logits 微变 => 接受率可能变）；
P29 改的是**采样 pick 的耦合方式**（=> 接受率也可能变）。两者都作用在"接受率"这一个观测上：
**一起开，接受率一变，分不清是谁干的。** 这正是项目"单变量"铁律要防的事。

### 2.3 一票否决：P28 破坏位一致（与收益无关）

源码注释（`fused_gr.cu:1751-1753`）原文：

> "Its fixed-order finish sums the K slices in another order than the single-token fused_gr_read, so the
> multi-token read is then no longer bitwise equal to T single-token calls (gr_parity's contract); off by
> default for that reason."

=> 与 P10（`--prefill` 改答案）同类的"不改答案 / 保位一致"否决项。**这一条与组合无关，单独就否。**

---

## 3 唯一值得单独验的组合点：P32 x P31

`--kv-grow` 与已采纳的 P31 `--conversation-cache-mib 4096` **在 K/V 保留上真交互**：
`generate.cpp:9315-9319` 原文 ---- "STRATA_KV_GROW_HOLD=1 (opt-in): keep the K/V as long as the longest parked
conversation; **default: trim to this request alone, as 0.1.40**"，调用
`kvg_trim(n + 256, hold_on ? conversations.longest_tokens() + 256 : 0)`。

=> 开 `--kv-grow` 会**按请求回收 K/V**，而 parked conversation 的 K/V 保留正取决于 `KV_GROW_HOLD`。
**这是与 P31 的真实耦合点**，若要动 P32，必须**连同 P31 一起看**（而不是与 P28/P29 绑一起）。
不过 P32 的收益上限（0.95%）本身在分辨力下，所以**当前仍判 REJECTED**，此交互点只作"若将来重估"的备忘。

---

## 4 判定与建议

| 组合 | 结论 |
|---|---|
| P28 + P29 | **不可组合测**：同路径，归因不可分；且 P28 单独已被否 |
| P32 + (任一) | **无收益相加**：P32 是显存路径，与另两个正交，组合只是多开一个 <=1% 的项 |
| 三项全开 | **不可取**：跨路径多开 => 缓存 / 显存 / 接受率三个观测同时动，任何变化都归因不清 |
| **P32 + P31** | **唯一有交互意义的组合**（K/V 保留）；但 P32 仍在分辨力下 => 暂不动，留备忘 |

**一句话**：这三项**能共存**（无互斥），但**不该组合验** ---- 它们不是"互补的三件事"，而是
"两项挤在同一条已被否的路径上 + 一项在分辨力下的显存路径上"。要验，只能**单变量**；要组合，
只有 P32 x P31 有意义。

---

## 5 证据索引

| 件 | 位置 |
|---|---|
| P28 实现 + 注释 | 容器内 `src/kernels/cuda/fused_gr.cu:1748-1775`（`#if defined(STRATA_HIP_GFX906)`） |
| P28 宿主调用者 | `src/core/mtp.cpp:723/838/946/957`、`src/core/verify.cpp:940/1555/1573/1588` |
| P29 实现 + 用途 | `src/kernels/cuda/sampler.cu:66-83 / 1111 / 1242 / 1320` |
| P32 条件 | `src/program/generate.cpp:3788-3803`；`src/core/layer.cpp:520` |
| P32 x P31 交互 | `src/program/generate.cpp:9315-9320`（`STRATA_KV_GROW_HOLD`） |
| 现役参数 | `data/strata-huihui-ud-iq4_xs.json`（`--spec 4` / `--spec-min-p 0.70` / `--mtp` / `--conversation-cache-mib 4096`） |
| P29 贪心口径 | `src/serve/server.py:576-577`；config 无 sampling 段 |

> 过程脚本：`C:\Users\clyde\AppData\Local\Temp\_w723rec{,2,3,4}.py`；原始输出 `_w723rec{,2,3,4}.txt`。
> 本轮**只读**：未停服务、未起容器、未改任何 config / register。
