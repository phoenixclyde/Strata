import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

BLOCK = '''
### §6.6 R99 — 把生产 llama.cpp 升到最新：四阶段方案（单变量、每阶带退出判据）

**为什么需要一个方案而不是一次换版。** 三件事实同时成立：①最新 tag `b12169`（`3ed7284f…`，2026-11-06）
比现用 `b11062` 晚 46 天；②`b12129`（中间版本）实测 **−4.0/−4.6%**；③`b12169` 相对 `b12129` 的 40 个提交里，
碰 MMQ 的只有 **`69ee2ecc` = #31047**（6 文件 +230/−231），而它把 `mmq_args.expert_bounds` 换成了
`tile_spec` —— 我们的 pointer-table 路径必须重写这段才能编。**一次换全树 = API 适配错误与上游性能差异混在一起，
事后无法归因**，所以拆成四阶段，每阶段只动一个变量。

| 阶段 | 做什么 | 判据（硬） | 失败怎么办 |
|---|---|---|---|
| **S0 冻结对照** | 同机、同 config 复测 b11062：三档 bench + 48-token 贪心指纹 | 与 W1022/W1023 记录差 ≤1% | 差 >1% 先查环境，不进 S1 |
| **S1 单提交** | 树 = `ref/llama_b12129` + patch `69ee2ecc`；写 `bounds → tile_spec`（device kernel，参照 `mmid.cu:120-140` 的 seam 对齐），改 `moe_mmq.cu:505` 的 `mmq_args` 构造与 `:504` 的 `pick_J`（`ntj` 语义） | **门1 数值**：968-token 英文 prompt 的 48-token 贪心输出与 b11062 **逐字节一致**；**门2 速度**：2K/8K 至少一档 ≥ +2×CV | 门1 不过 = spec 布局错，**禁止**进 S2；门2 ≤0 ⇒ **R99 关闭**（gfx906 不适用 #31047） |
| **S2 全树** | 完整 `b12169` 树（网络慢则镜像 + `-C -` 续传，或只补 39 个提交的 diff） | 与 S1 的性能差 ≤1%、指纹仍逐字节一致 | 差 >1% 说明其余提交有回退，二分定位后再定 |
| **S3 验收** | 六档 bench（2K/8K/16K/32K/60K/130K）+ decode + TTFT + 多轮；质量相对门（KL ≤0.0139 / top-1 ≥99%，`P330` 口径） | 任一档超 2×CV 即回滚；质量门不过即回滚 | 回滚到 `strata-0.1.57-001`，R99 记 DONE_NEG |
| **S4 落生产** | 改 `third_party/ggml/VERSION.txt`（**fork 覆盖**，commit 里写明上游 v0.2.11 声明的是 b11062）、`ci/docker/Dockerfile-gfx906-0.2.11` 的 `LLAMA_CPP_SHA/BUILD/TREE` 与去掉 `iqp.cpp` 的 `test -f`、重建镜像与容器（带 `--ulimit memlock=-1:-1`，`diff_container.py` 18 键差 0）、`ci/release_check.py` 10/10 | 五处 pin 一致 + `RELEASE_CHECK: PASS` | 任一不一致即视为发布失败，按 `strata-release` 回滚 |

**收益的诚实估计（算术，不是实测）**：2K 的 prefill 相位里 MMQ 相关是 gemm gate/up **816 ms** + gemm down **510 ms**，
占 GPU 3191 ms 的 **41.6%**；若 MMQ 快 20%，整条 prefill 约 **−8.3%**。PR 自报的是 MI50 **Q4_0 mb64 1.23×**，
我们的专家是 **Q4_K/Q5_K**，适用性只能实测，不能外推。

**成本**：S1 2–3 h、S2 ~1 h（含下载）、S3 ~2 h（含一次停机 4–6 min 的质量门）、S4 ~1 h；全量编译 5–6 min/次，
部署 1.5 min/次。**最坏情况**：S1 门2 ≤0，2–3 h 后关闭，生产零改动。

**为什么不是「直接上 b12169」**：那会把「spec 布局写错」与「上游变慢/变快」压成一次不可分解的测量；
而 spec 写错**不报错、只是结果错**（kernel 直接解引用 `tile_spec`，无空指针分支），正是本项目最贵的一类 bug。
'''
if "R99 — 把生产 llama.cpp 升到最新" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK

# §0.1 队列：R99 插到最前（它是当前唯一可能带来两位数收益的项）
old_q = "| **唯一队列** | **R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50**"
new_q = "| **唯一队列** | **R99（llama.cpp 最新，四阶段）→ R95（P309 实验）→ R94 → R91 → R89 → R46 → R49 → R50**"
if old_q in s:
    s = s.replace(old_q, new_q, 1)

s = s.replace("| 进度分母 | **291 条 / 已结 211 / 72.5%** |", "| 进度分母 | **295 条 / 已结 211 / 71.5%** |", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROW = ("B8工程", "R99",
       "生产 llama.cpp 升到最新（b12169）：S0 对照 → S1 单提交 #31047 → S2 全树 → S3 验收 → S4 落生产",
       "W1026", "OPEN",
       "**W1026 立（四阶段，单变量）**：S0 同机复测 b11062（三档 + 贪心指纹，差 ≤1% 才进）；"
       "S1 树=`ref/llama_b12129`+patch `69ee2ecc`，写 `bounds→tile_spec`（device kernel，参照 `mmid.cu:120-140` seam），改 `moe_mmq.cu:505` 的 `mmq_args` 与 `:504` 的 `pick_J`（`ntj` 语义）——"
       "**门1 数值**：968-token 英文 48-token 贪心输出与 b11062 逐字节一致；**门2 速度**：2K/8K 至少一档 ≥+2×CV；门1 不过禁止进 S2，门2 ≤0 则 R99 关闭；"
       "S2 全树 b12169（与 S1 差 ≤1%）；S3 六档 bench + 质量相对门（KL ≤0.0139 / top-1 ≥99%）+ 多轮；S4 改 `third_party/ggml/VERSION.txt`（fork 覆盖）/Dockerfile `LLAMA_CPP_*`/去掉 `iqp.cpp` 的 `test -f`/镜像+容器（memlock、18 键 diff 0）/`release_check` 10 项。"
       "收益算术估计：MMQ 占 2K prefill 41.6%（816+510 / 3191 ms），快 20% ⇒ 整条 −8.3%；PR 的 1.23× 是 Q4_0 mb64，Q4_K 适用性待实测。成本 5–7 h。",
       "deploy/W832_OPT_PLAN_V2.md §6.6 R99")
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
ID = lines[hi].split("\t").index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
if "R99" not in have:
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("\t".join([ROW[0], ROW[1], ROW[2], ROW[3], "count", "4", "0", ROW[4], ROW[5], ROW[6]]))
    lines.append("")
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("R99 block + row")
