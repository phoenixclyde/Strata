import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

BLOCK = '''
### 回写 · W1023（把生产的 llama.cpp 更新到最新：做了，实测 −4%，已回滚）

机主令「生产容器的 llama.cpp 也更新到最新」。做了完整一轮：查到最新、移植、编译通过、部署、测量、回滚、留档。

**一、「最新」是哪两个东西（先分清）**

| 概念 | 值 | 说明 |
|---|---|---|
| master HEAD | `45b6604b20f17b7d7638042306c0cd1b6af5999c`（2026-11-05 16:47Z） | 只比最新 tag 多一条 `model: add support for xing4_0 (#31589)`，与引擎无关 |
| **最新 tag（采用作候选）** | **`b12129` = `3259ab6e5dd86fad1931962d784702cb53c7877b`** | 可读、可复现、可被 release_check 校验 |
| 生产现用 | `b11062` = `3cf03257…`（2026-09-20） | 差 46 天 |

**二、46 天里上游对 MMQ 做了什么（取自 GitHub commits API + PR 正文）**

- `#31047` **linearize MoE data layout for MMQ/MMF**：把「每专家的列区间」改成 `mmid.cu` 预计算的 **tile 分配表**，并把原先只给 RDNA3/4 的「小 tile 更优」推广到所有 GPU。PR 自报 **MI50 Q4_0 microbatch 64：1343→1657 t/s（1.23×）**、gemma4 26B MoE 454→649（1.43×）。
- `#31188` / `#31296` MMQ 里融合 MoE gate/up + GLU（含 NVFP4）。
- `#31247` Q8_1 correction sum 修正（**改数值**）。
- `#31679` mmvq/mmid 的 max batch 改用「最高编译架构」判断。
- `#29050` CDNA2 的 MFMA indexer；`#31373` RDNA4_M 家族 —— 与 gfx906 无关。

**三、移植面：4 类、34 处，全是机械的**

| 旧（b11062） | 新（b12129） | 处数 |
|---|---|---:|
| `ggml_cuda_mmq_get_config(type, J, fallback, cc)` | `…, cc, prec_src1)` | 5 |
| `mul_mat_q_case<type>(ctx, args, s)` | `mul_mat_q_case<type, prec_src1>(…)` | 24 |
| `new_pool_for_device(int, int)` | `(context &, int, int)` | 1 |
| W4A4 的 `DECL_MMQ_CASE(NVFP4)` | `DECL_MMQ_CASE_W4A4(NVFP4)`（`GGML_PREC_Q4`） | 2 |

另：b12129 **没有** `ggml/src/ggml-cpu/iqp.cpp`（v0.2.11 构建的硬依赖），但没有任何地方引用它，所以只是 Dockerfile 里那句 `test -f` 要跟着改。全量编译 **154/154、LINK_OK**，二进制 44,496,832 B、md5 `54ff1635…`、`--version` = 0.1.57。

**四、实测：三档全部回退，超 2×CV**

| 量 | b11062（现役） | b12129 | 差 | CV |
|---|---:|---:|---:|---:|
| prefill@2K tok/s | **530.43**（回滚后复测 531.42） | **509.11** | **−4.02%** | 0.75% |
| prefill@8K | **716.02** | **683.13** | **−4.59%** | 0.26% |
| prefill@16K | **780**（`P261` 六档，跨日） | 766.02 | −1.79% | 0.08% |
| decode tok/s | 33.64（本次回滚后 34.61） | 35.48 | +2~5%（CV 3.97% 内） | — |
| TTFT@2K | 3.95 s | 4.09 s | +3.5% | 0.79% |

**五、数值是对的（否则问题会更大）**

48-token 贪心指纹（同一 prompt、temperature 0）：
- 968-token 英文：**逐字节完全相同**（224 字符）；
- 短英文：前 118 字符相同，新版多 4 字符（48 token 预算边界）；
- 1565-token 中文：两者都在 48 token 预算内，差异只在 reasoning 与 content 的分配。

⇒ MoE 布局改了，但**我们的 prefill 算术没被算错**。回滚的理由是性能，不是正确性。

**六、为什么拿不到 PR 那个 1.23×**

`#31047` 的收益来自 **`mmid.cu` 预计算 tile 分配表**这条路径，对象是 **Q4_0 + microbatch 64**。
我们的专家权重是 **Q4_K / Q5_K**，且 `moe_mmq.cu` **自己算 `expert_bounds`**（pointer-table MMQ 的设计就是不经过 `mmid`）⇒ 新布局那条路**一次都没跑**。
同时 PR 把「小 tile 更优」推广到了所有 GPU —— 对 gfx906 可能是负向的，但**这只是一条候选解释，没有 profiler 证据，不作为结论**。

**七、结论与留档**

- `b12129` **DONE_NEG**，生产回滚到 `strata-0.1.57-001`（`5e63174d…`），ledger 记 `ROLLBACK`，config md5 回到 `53ac61e0…`；
- 移植**不丢**：`exp/lcpp-b12129` = `4db10037`（5 文件），主 tree 干净（0 dirty），随时可再试；
- 实验构建 `build-lcpp` 与二进制 `strata-0.1.57-002` 保留，`build-r28` 未动；
- 生产镜像/容器**未改**：`RELEASE_CHECK: PASS`（10/10，pin 仍是 b11062）。

**八、教训：上游 PR 的倍数自带「路径前提」**

`1.23×@MI50` 是真的，但它属于「Q4_0 + mmid 新布局」；我们的路径是「Q4_K + 自建 bounds」，抄不到。
这与本项目 `#22174 +17%`、`#31188` 性能栏、`v_mfma` 三次同型：**引用外部倍数必须写清「谁的实现、哪条路径、什么形状」**，否则它只是线索。
'''
if "回写 · W1023" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK

# §0.1 的依赖 pin 行：补上这次尝试与结论
old_pin = "自 0.2.8p2 起未变 | `ci/release_check.py` 三行（pin / tree / build refs）；"
new_pin = ("自 0.2.8p2 起未变；**b12129（最新 tag）已试并回滚（−4.0/−4.6%，`P354`）** "
           "| `ci/release_check.py` 三行（pin / tree / build refs）；")
if old_pin in s:
    s = s.replace(old_pin, new_pin, 1)

s = s.replace("| 进度分母 | **283 条 / 已结 203 / 71.7%** |", "| 进度分母 | **286 条 / 已结 206 / 72.0%** |", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P354",
  "llama.cpp 最新 tag b12129 = 3259ab6e：全树编过、二进制可跑、数值一致，但 prefill −4.0/−4.6% ⇒ REJECTED，已回滚",
  "W1023", "DONE_NEG",
  "**W1023 立**：master HEAD `45b6604b`（11-05），最新 tag **b12129 = `3259ab6e5dd86fad1931962d784702cb53c7877b`**（比 b11062 晚 46 天）。"
  "移植 4 类 API 后全量 154/154、LINK_OK，二进制 md5 `54ff1635…`。实测 prefill@2K **530.43→509.11（−4.02%，CV 0.75%）**、@8K **716.02→683.13（−4.59%，CV 0.26%）**、@16K 780→766.02（−1.79%，跨日基线）；"
  "decode 33.64→35.48（CV 内）。48-token 贪心指纹在 968-token 英文 prompt 上**逐字节相同** ⇒ 数值正确，回滚理由是性能。已 `rollback.sh` 回 `strata-0.1.57-001`（`5e63174d…`），config md5 回 `53ac61e0…`。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1023"),
 ("B8工程", "P355",
  "b12129 移植清单（4 类 34 处）留档在 `exp/lcpp-b12129` = 4db10037，主 tree 保持可编 b11062",
  "W1023", "DONE",
  "**W1023 立**：`ggml_cuda_mmq_get_config` +prec（5）、`mul_mat_q_case<type,prec>`（24）、`new_pool_for_device(context&,int,int)`（1）、`DECL_MMQ_CASE_W4A4`（2）；"
  "另 b12129 无 `ggml-cpu/iqp.cpp`（无引用，仅 Dockerfile 的 `test -f` 需改）。移植放在实验分支，`gfx906/mi50` 回退到 `372106ed`（dirty 0），`build-lcpp` 与 `strata-0.1.57-002` 保留作下次起点。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1023"),
 ("B8工程", "P356",
  "为什么 #31047 的 MI50 1.23× 抄不到：它走 mmid 的 tile 分配表（Q4_0 microbatch 64），我们的 K-quant 专家用自建 bounds",
  "W1023", "DONE_NEG",
  "**W1023 立**：PR 正文自报 MI50 Q4_0 mb64 1343→1657 t/s（1.23×）、gemma4 26B 454→649（1.43×）；其机制是 `mmid.cu` 预计算 tile 分配并推广小 tile。"
  "我们的专家是 Q4_K/Q5_K，`moe_mmq.cu` 自己算 `expert_bounds`（pointer-table MMQ 不经 mmid）⇒ 新路径未执行；−4% 的机制**未定位**，不写成结论。"
  "判据：引用外部倍数必须写清实现/路径/形状（同 `#22174 +17%`、`#31188`、`v_mfma` 三次）。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1023"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
ID = lines[hi].split("\t").index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
