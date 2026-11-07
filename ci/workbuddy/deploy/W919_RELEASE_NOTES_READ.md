# W919 · 上游 release notes 逐条读（0.2.2 → 0.2.10），以及 AMD 面的移植评估

> **【AUDIT24 P1 · 2026-11-04】状态行要撤回一半**：本件把「PLE 表未 mlock」写成**现成的损失**（"不需改一行代码"），
> 但 `W920` 两臂（预热后 rep6–9）实测 **prefill / decode 均在噪声内** ⇒ `R67 = DONE_NEG`：
> 补丁本身是对的，只是在当前 `unlimited` 档**完全静默**。另：本件引用的 0.2.10 release notes 文本当时只落在 `/tmp`，
> 仓库里没有留副本（复现需重下一次）。

日期：2026-11-03 22:3x
状态：零停服；~~一条已实证的现成损失（PLE 表未锁定）~~ **已撤回（`W920` 实测为 0，`R67 = DONE_NEG`）**，三条待执行

---

## 0 我上一轮错在哪

我说"上游从 0.2.8 起不再写 release notes"——**错**。我只在仓库 `docs/` 里找
（`docs/release-notes-*.md` 最后一份是 0.2.7），而 GitHub Releases 的正文**从来不进仓库**。
实际上 0.2.10 的 release body 有 **38,007 字节**，0.2.9 有 19,926，0.2.8 有 9,764。

取全文的方法（可复现）：

```bash
curl -s "https://gh-proxy.com/https://api.github.com/repos/Niko1221/Strata/releases?per_page=10"
# 每个元素 .body 就是页面上那段全文，无截断
```

| tag | 标题 | 发布 | body 字节 |
|---|---|---|---|
| v0.2.10 | DFlash2 default drafter / all-cards split / ISTA-DAS Coder | 2026-11-02 23:52 | **38,007** |
| v0.2.9 | Unsloth 1-bit sets / Strix Halo prompts / parallel on Linux | 2026-10-31 08:02 | 19,926 |
| v0.2.8 | Arc B-series pairs / four-card Radeon servers | 2026-10-29 22:40 | 9,764 |
| v0.2.7 | DGX Spark / DeepSeek on the Mac | 2026-10-27 14:54 | 30,567 |
| v0.2.6 / v0.2.5 / v0.2.4 / v0.2.3.1 / v0.2.3 / v0.2.2 | — | 10-21 ~ 10-25 | 4,353 ~ 33,403 |

---

## 1 一个必须先摆出来的事实：gfx906 不在上游的评测面上

全部 10 个 release 里，`gfx906` / `MI50` / `Vega` 只出现 **1 次**：

> **0.2.7**：*"Prefill on one card, decode on another (`--split-serve P,D`…). The idea, the hand-made
> setup (an RTX 3070 reading the prompt, **two MI50 cards making the answer**) and the first
> measurements are by @MarcoTool."*

而且是**用户自己的手工方案**，不是上游的优化；而且结论是负面的（"slower than the normal layer
split on every workload：8K prompt 16% longer、32K 48%、3-turn chat 30%/4%"）。

各 release 提到的 AMD 架构：

```
v0.2.10: gfx1100 gfx1151 gfx1200 gfx1201
v0.2.9 : gfx1151
v0.2.8 : （无）
v0.2.7 : gfx1151
v0.2.5 : gfx1151
v0.2.4 : gfx1200 gfx1201
v0.2.3 : gfx1151
v0.2.2 : gfx1011 gfx1030 gfx1031 gfx1151 gfx1201
```

⇒ **全部是 RDNA2/3/4 与 gfx1151，没有一个 gfx906。** 上游的 AMD 面 = RDNA 面。
所以我们能拿的不是"他们的优化"，而是**与架构无关的框架修复**——下面第 3 节逐条。

---

## 2 现成的损失（已实证，不是推测）：PLE 表 26.8 GiB 一直没锁在 RAM 里

`0.2.10 #4671` 原文：

> *"A systemd service without LimitMEMLOCK may lock 8 MiB, so the **26.8 GiB mlock of the PLE table
> was refused** and the engine ran with a reclaimable table (**the reporter measured up to 6% slower
> decode**)…"*

26.8 GiB 正是我们这个模型的 PLE 表（`W910` 实测 26.82 GiB）。现场证据：

```
$ docker exec strata166-407 grep -i mlock /data/strata-huihui-ud-iq4_xs.log | tail -2
strata: PLE table mlock failed (Cannot allocate memory; raise `ulimit -l`): its pages stay faulted in but may be reclaimed
strata generate: PLE table loaded (not locked) (--ple-io ram chosen by the residency policy) in 0.2 s

$ grep -E "VmLck" /proc/<engine>/status
VmLck:           0 kB
```

限制在哪里：

| 层 | Max locked memory |
|---|---|
| `ulimit -l`（容器内） | 8192 KiB |
| `/proc/1/limits` | soft **8,388,608** / hard **8,388,608** |
| `/proc/<engine>/limits` | 同上（继承） |
| `docker inspect .HostConfig.Ulimits` | `[]`（未设置） |
| `systemctl show docker --property=LimitMEMLOCK` | **8388608** |

容器内 hard 就是 8 MiB，非 root 无法提升（需 CAP_SYS_RESOURCE）⇒ **只能在容器启动参数上改**。

最小可行性验证（不碰生产，1 分钟）：

```
生产容器：            RLIMIT 8 MiB → mlock(256 MiB) rc=-1 errno=12 (Cannot allocate memory)
临时容器 --ulimit memlock=-1：        mlock(256 MiB) rc=0  (ok)
```

**内存账是成立的，而且不会挤掉专家 cache**：

```
FileExpertSource: RAM budget 76.00 GiB: 14819 of the 33.45 GiB of experts ...
FileExpertSource: mapped pinned cache complement ready: resident 33.45 GiB, pinned 33.45 GiB in 117 s
strata generate: the file tier reads through the file cache (RAM copy built (33.45 GiB): 82.8 GiB available ...)
```

PLE 26.8 + 专家 33.45 = 60.25 GiB，**本来就在 76 GiB 预算内**；锁住后在引擎视角仍有 ~56 GiB。
两者机制不同：专家 cache 走 `pinned/mapped`（`VmLck` 不计），PLE 走 `mlock(2)`（计入 `RLIMIT_MEMLOCK`）
⇒ 放开 memlock **只影响 PLE**，不动专家 cache 的策略。

上游给的收益是 **decode 最多 6%**（reporters 的机器，非我们）；我们 decode 占 64–83%（`W798`）
⇒ 端到端量级 **4–5%**，但**必须实测**，不能引用别人的数。

执行代价：`--ulimit` 不能 `docker update`，**必须重建容器**（停 → 带 `--ulimit memlock=-1` 重新 `docker run`
→ 加载 117 s + 服务起来约 230–275 s）。这是破坏性操作，需机主确认。

---

## 3 三条与架构无关、直接命中我们路径的修复（0.2.10）

### 3.1 `#4677` serve stop bound —— **HIP 专用，单请求投机 + park，正是我们的形状**

`243fdb21`，`git show` 原文：

> *"In the single-request speculative paths the accepted rows of a verify window were committed first
> and the output loop cut to max_new or EOS afterwards, so a request's last window could park a
> snapshot with tokens the client never received. `conversation_prefix()` needs the whole snapshot to
> be a prefix of the next prompt, so the snapshot was refused and the older checkpoint was used
> (**about 6% of a 12K-token prompt read again**). `serve_stop_bound()` caps the accepted rows …
> **HIP only (STRATA_USE_HIP), where it was measured.** … on by default, `STRATA_SERVE_STOP_BOUND=0`
> turns it off"*

实测（4×R9700，Qwen3.8 IQ3_S，四个 11–15K 对话，768 token 回答，**对话逐个打开**）：
**4/16 续接回退 → 0/16，复用 98.36% → 99.74%**。

我们的形状完全对上：

| 条件 | 上游实测 | 我们 |
|---|---|---|
| HIP | 是 | gfx906 ✅ |
| 单请求投机 | 是 | `--spec 4` ✅ |
| 对话逐个打开（非 batch 行） | 是（这条正是有效的那个场景） | 单流 ✅ |
| 有 park / 快照复用 | 是 | `CKPT_MOVE_PARK=1` + `--prompt-cache-every 8192` ✅ |

我们树里 `STRATA_SERVE_STOP_BOUND` 命中 **0**（0.2.10 才有）。改动只有
`include/strata/core/serve_stop_bound.hpp`（15 行）+ `generate.cpp` 25 行 + CMake 5 行，
**不改数值**（提交自述"与旧标量循环一致"，带 2,736 例策略测试）⇒ 只需"输出逐位相同 + 多轮 TTFT"两道门，
不需要 KL 门。

### 3.2 `#4590` penalty 窗口 —— 我们是 Qwen，属正确性

`ed76b12f`：*"The repeat, frequency and presence penalties count the tokens the reply has written,
not the last tokens of the prompt"*。症状：**新任务会重复旧 JSON**；报告者 32 seeds 里旧 JSON
从 13 次降到 4 次。`STRATA_PENALTY_PROMPT=1` 可回退旧行为。

我们跑的是 Qwen 系（`arch=qwen4exp`），且用的是**带惩罚的采样**（`--spec-min-p 0.70` 之外还有采样参数）。
这条会**改变输出**，按纪律必须先过 `W913` 的门（KL ≤0.005、top-1 ≥99%）。我们树里命中 0。

### 3.3 `#4741` BF16 projection → Q8_0

`b0b942fa`：*"A pack that keeps a native-eligible projection unquantized (BF16) no longer stops the
engine with 'no native GGUF blocks'"*。我们有 581 个 F32/BF16 张量（0.33 GiB，`W910`），但引擎能正常
起、正常答 ⇒ **未触发**。记档不立项。

---

## 4 0.2.8 / 0.2.9 的 AMD 条目：逐条判"我们有没有"

| 条目 | 机制 | 我们状态 | 判定 |
|---|---|---|---|
| **0.2.8 「Bigger batch windows on AMD」HIP 8→16 行** | `STRATA_WINDOW_MAX_T` 默认 `auto` = **HIP 16 / CUDA 8** | **已在我们树里**（`CMakeLists.txt:102`）；日志 `strata verify: window up to 6 tokens` | **不是差距**；我们 spec 4 只用 6 行，16 行上限有余量 |
| 0.2.8 四卡 Radeon profile | 4×R9700、32 slots、layer split 13,26,39 | 单卡 | 不适用 |
| 0.2.9 nine parallel settings（`STRATA_CKPT_POOL`/`SLOT_CKPT_MOVE`/`QSA_SLOTS`…） | `--parallel`/`--batch` ≥2 | 树里都有（5/50/41 处命中） | **单流不适用**（机主定死单流） |
| 0.2.9 GDN 上 tensor core（`STRATA_GDN_TC`） | gfx906 无矩阵核 | 树里有开关 | 不适用（`W800` 已判：gfx906 空表） |
| 0.2.9 Radeon gfx12 GDN chunked 从 64 token 起 | gfx12 | `STRATA_GDN_CHUNKED` 树里有 27 处 | 架构门挡住，见下 §5.2 |
| 0.2.10 DFlash2 为默认 drafter | 支持列表 = CUDA 8.6/8.9/12.0/12.1、gfx1100/gfx1151/gfx1201、Metal、Arc | **gfx906 不在列表** | 不适用 |
| 0.2.10 all-cards split engine | 2×NVIDIA 或 4×R9700 | 单卡 | 不适用 |
| 0.2.10 8 GB 卡 128K（prompt buffers 用 16 槽而非 128） | 显存不足时降级 | 我们 572 MiB 空闲、32 GB 卡 | 不适用（除非显存吃紧） |

---

## 5 两条"机制可借、架构不借"的（值得进方案，不是照抄）

### 5.1 expert cache 让结果不可重复 —— 上游自述，正好印证 `W913`

`0.2.9` Known problems：

> *"**DeepSeek is not repeatable at temperature 0.** Five identical requests can give up to 5 different
> answers. We traced this to **the expert cache, which moves experts between the CPU and the GPU
> between requests; the two round differently**. With `--set=--no-expert-cache=on`, the repeated
> requests matched in our runs … That costs **8% to 10% of decode on four R9700 cards and 58% on one**."*

`0.2.10` 复述并加了一句：*"On Radeon cards (HIP) the CPU lane computes part of the experts, which adds
the same effect. **We compared engines by KL, not by identical tokens. This was already so in 0.2.9.**"*

这独立证实了 `W913` 的三条结论：①同进程内逐位确定、跨进程 0.0032 KL；②根因是专家 cache 的 GPU/CPU
驻留（我们日志同款：`R4 hit path ON - resident experts are computed on the GPU`、`resident RAM mode:
33.45 GiB of experts in RAM`）；③**"钉死驻留"这条路被代价封死**——单卡 `--no-expert-cache` 掉 58%
decode，我们不可能接受。⇒ `R60`/`R64` 的精度门只能按 **0.0032 KL** 表述，这条不再是推测，是供应商自述。

### 5.2 "同一 prompt 永远走同一条路" + chunked 阈值（0.2.7 / 0.2.9）

0.2.7：*"**The same prompt always takes the same path.** The engine now picks the prompt path from the
prompt's length (96 tokens and more go through the chunked pass). The old timing guess changed answers
between runs."* ← 又一个"非确定性来自路径选择"的已修 bug，我们的树是 0.2.9，**这条已在**。

0.2.9：Radeon gfx12 的 chunked kernel 阈值从更高降到 **64 token**（4K +3.5%、16K +4.7%、32K +6.1%）。
我们日志 `strata serve: prompt chunk auto: 8192 tokens, a 96-slot ring`、`prefill: the CPU share is ON
by default for prompt chunks below 1024 tokens`。**阈值是架构门控的（gfx12），但"阈值该定在哪"这个
参数我们可以自己扫**——这才是可借的部分（见 §7 R70）。

---

## 6 结论：生产参数怎么改、方案怎么改

### 6.1 生产参数

| 项 | 现在 | 建议 | 依据 |
|---|---|---|---|
| 容器 `--ulimit memlock` | 未设（8 MiB） | **`-1`（unlimited）** | §2，PLE 26.8 GiB 未锁，上游实测 decode 最多 −6%；需重建容器 |
| 其余 arg / env | — | **不动** | 0.2.10 没有 gfx906 的默认值变更（`W918` 已核 11 条 `arch_defaults.cpp` 全为 gfx12/1151/1010/1030） |

### 6.2 方案队列（新增三条，插在 R66 之前/之后）

```
~~R59~~ → R67(PLE mlock) → R66(三条 opt-in) → R68(stop bound) → R61 → R60 → R58 → R63 → R64 → R69(penalty) → R65 → …
```

- **R67**：PLE 表 mlock。已实证未锁 + 已验证 `--ulimit` 能解。**先做这个**，因为它是"现成的损失"，
  且不需要改一行代码。判据：TTFT 不变（PLE 只在 decode 侧）、decode `|Δ| ≥ 2×CV`、`VmLck ≈ 26.8 GiB`、
  日志不再报 mlock failed。
- **R68**：`#4677` stop bound cherry-pick。判据：输出逐位相同 + 多轮第 2 轮 prompt 重读量下降。
- **R69**：`#4590` penalty 窗口。判据：先过 `W913` 精度门（KL ≤0.005 / top-1 ≥99%），再看输出是否改善重复。
- **R70（新提出，只读）**：chunked 阈值扫描。借 0.2.9 "gfx12 从 64 token 起"的思路，在**我们**的
  gfx906 上扫 `prefill chunk` 阈值（现在 auto=8192、CPU share 阈值 1024），量 1K/3K/6K 三档 TTFT。
  这条不是移植，是**把上游的调参维度搬过来用**。

---

## 7 复现命令

```bash
# 1) 取全部 release 正文
curl -s "https://gh-proxy.com/https://api.github.com/repos/Niko1221/Strata/releases?per_page=10" -o /tmp/rel.json
python3 -c "import json;d=json.load(open('/tmp/rel.json'));[open('/tmp/relnotes/%s.md'%r['tag_name'],'w').write(r['body']) for r in d]"

# 2) 确认 gfx906 是否出现在 release 面
grep -niE "gfx906|mi50|vega" /tmp/relnotes/*.md

# 3) 确认 PLE 未锁
docker exec strata166-407 sh -lc 'grep -i mlock /data/strata-huihui-ud-iq4_xs.log | tail -2'
docker exec strata166-407 sh -lc 'grep VmLck /proc/$(pgrep -f "strata-0.1.55t --serve"|head -1)/status'

# 4) 最小验证：memlock 放开后 mlock 是否成功
docker run --rm --ulimit memlock=-1 --entrypoint python3 -v /tmp/mlk.py:/tmp/mlk.py \
  strata-gfx906:0.2.9-101 /tmp/mlk.py 256
```

（注：`/tmp/mlk.py` 里 `getrlimit` 的 resource 号写成了 7＝`RLIMIT_NOFILE`，打印出来像 1 MiB 是假的；
`mlock` 的返回码是真的。`RLIMIT_MEMLOCK` = 8。）
