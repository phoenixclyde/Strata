# -*- coding: utf-8 -*-
"""W1004：把 W972–W1001 该入方案而没入的东西补进去。

审计口径：账本（PROGRESS/REGISTER）已经更新、但 §6.2 定义行仍是旧说法，或
方案里根本没有这件事。六类缺口：
 A 定义缺失：R94/R95/R96 只有队列一句话，没有 §6.2 行
 B 定义过期：R88（W990 证伪）、R90（W974 已上 v0.9.0）、R93（W987 结案）
 C 方案与账本冲突：--pool-workers 现值写 0（实为 10）、X1 OPEN（账本 NA）、X2 OPEN（前提不成立）
 D 判据未入：W958 token 序列作废、W969 三 regime + t≈1.3+n/785
 E 版本未入：v0.9.0 / ggml 0.29.0 / CUDA 指纹策略
 F 参数册缺口：--pool-workers 10 没有 ADOPTED 行
"""
import io, os, shutil, sys

D = r"D:/workbuddy_space/strata_ws/deploy"
PLAN = os.path.join(D, "W832_OPT_PLAN_V2.md")
PROG = os.path.join(D, "PROGRESS.tsv")
REG = os.path.join(D, "params", "PARAM_REGISTER.tsv")
BAK = ".bak_w1004"

def rd(p): return io.open(p, encoding="utf-8", errors="replace").read()
def wr(p, s): io.open(p, "w", encoding="utf-8", newline="\n").write(s)

plan = rd(PLAN)
ok = []

def append_cell(text, anchor_prefix):
    """在 anchor_prefix 开头那一行的最后一个单元格末尾追加 text"""
    global plan
    i = plan.find(anchor_prefix)
    if i < 0:
        ok.append(("MISS", anchor_prefix[:24])); return
    j = plan.find("\n", i)
    line = plan[i:j]
    k = line.rfind(" |")
    if k < 0:
        ok.append(("NOCELL", anchor_prefix[:24])); return
    plan = plan[:i] + line[:k] + "；" + text + line[k:] + plan[j:]
    ok.append(("ok", anchor_prefix[:24]))

# ---- B：三条定义行过期 ----
append_cell("**W990 证伪**：2K GPU timeline 与 wall 只差 **15 ms**（3668 vs 3683）⇒ 没有「串行」可重叠，"
            "真靶子是小批 GEMM（R95）；`W978` 借用填充否证（7.62→3.11 GiB 同耗时）⇒ 本条降为方向保留、不再排队",
            "| **新23** | **R88**")
append_cell("**W974 已上线 v0.9.0**（`cd959bae`，ggml 0.29.0，exe `-090`，tag r32）；`b12099` 实为 master `feaf8000`（不是 0.8.0 标签）；"
            "**W988 降 PARTIAL**（质量门从未跑，欠账转 R94）；策略改为**按 `ggml-cuda/` 目录指纹触发重建**，不按 tag 盲重编",
            "| **新25** | **R90**")
append_cell("**W987 结案**：8192 / 16384 / 32768 三值齐（16K 用 8192 掉 5.75%），**维持 16384**；`W988` 补 32768 后仍不显著",
            "| **新28** | **R93**")

# ---- A：R94/R95/R96 定义行 ----
anchor = "| ~~新26~~ | ~~R76~~ |"
if anchor in plan and "| **新30** | **R95** |" not in plan:
    rows = """| **新29** | **R94** | **v0.9.0 基线的质量门**：对金标算 KL 与 top-1 一致率（先测自一致地板，再比 0.4.1） | KL ≤0.0139、top-1 ≥99%；不先测地板就不许拿 run 间差当结论 | `W988` 立：R90 判 DONE 时漏跑质量门 ⇒ 降 PARTIAL，欠账转本条 |
| **新30** | **R95** | **小批 GEMM 效率**：2K prompt 的 gate/up 1.91×、down 1.87×、dequant 3.9×、wait copy 14×（占 68%） | J=64 是 K-quant 设计下限（`W992`，候选 A「启用 J<64」作废）；先 C（dequant 融合）后 B（小专家 GEMV 分流）；`\\|Δ\\|≥2×CV` | `W990` 立；相位分解来自引擎自带 `STRATA_PREFILL_TIMING`（`prefill.cpp:2981`），不用改代码 |
| **新31** | **R96** | **MoE gate/up + GLU 融合**（上游 #31188，2026-10-30 合并） | **N/A**：我们 gu 本来就是 `prefill.cpp:5300` 的一次 1280 行调用，上游省的是第二次 launch | `W995` 立、`W1003` 判 N/A；不再排队 |
"""
    plan = plan.replace(anchor, rows + anchor, 1)
    ok.append(("ok", "新29/30/31"))

# ---- C：参数轴表 + X1/X2 ----
old_pw = "| `--pool-workers` | 0（=20） | **无差异** | 本节 |"
new_pw = ("| `--pool-workers` | **10**（`W989` 采纳；0 = 20） | **10 优于 20**：prefill@2K 524.45 vs 511.73（**+2.49%**，band 1.00%）、"
          "TTFT −2.0% | `W989`（本节的 0 vs 13 只说明「13 不比 20 好」） |")
if old_pw in plan:
    plan = plan.replace(old_pw, new_pw, 1)
    plan = plan.replace("⇒ 对外只能说：**这四个旋钮在这台机器上已经没有可分辨的收益**，不能说\"已经调到最优\"。",
                        "⇒ 对外只能说：**这四个旋钮在这台机器上已经没有可分辨的收益**，不能说\"已经调到最优\"。\n\n"
                        "> **W989 更新（2026-11-05 19:3x）**：上表测的是 0(=20) vs 13。真正被采纳的是 **10**——20 个 worker 对 22 核是**过订阅**，"
                        "减半后 2K prefill **+2.49%**（band 1.00%）、TTFT −2.0%，已落生产（args 35→37）。"
                        "所以本节的「无差异」只适用于 13，**不适用于 10**。", 1)
    ok.append(("ok", "P1-b 参数轴表"))
else:
    ok.append(("MISS", "P1-b"))

old_x1 = "| X1 | P141 `--ple-io ram` + drop_caches | OPEN | **W814 已量到 read −8~−23%，从未进生产**（最被低估的一条） |"
new_x1 = ("| X1 | P141 `--ple-io ram` + drop_caches | **NA** | `W976`：`ram` 就是 **mmap + mlock**，与 `mmap` 实测等价"
          "（decode 39.7 / prefill 545·548）；已在 args 显式 `--ple-io mmap`（Locked 0、Rss 103→73 GiB）⇒ 没有「再加 ram」的空间 |")
if old_x1 in plan:
    plan = plan.replace(old_x1, new_x1, 1); ok.append(("ok", "X1"))
else:
    ok.append(("MISS", "X1"))

old_x2 = "| X2 | P147 `--ulimit memlock=-1` | OPEN | 容器 `ulimit -l=8192KB`，PLE mlock 每轮报 `Cannot allocate memory` |"
new_x2 = ("| X2 | P147 `--ulimit memlock=-1` | **NA** | `W977`：容器 memlock soft/hard 均 **-1**（上限）、`VmLck`/`VmPin` 均 0、"
          "宿主 `Mlocked` 仅 25 MB ⇒ 前提不成立；且结论是**不锁**（`hipHostRegister` ≠ pin，锁了反而抢 THP） |")
if old_x2 in plan:
    plan = plan.replace(old_x2, new_x2, 1); ok.append(("ok", "X2"))
else:
    ok.append(("MISS", "X2"))

# ---- D：判据两条 ----
anchor_d = "- prefill 类改动必须看 `--lengths 2000,8000,16000` 三档，任一档掉出 2×CV 即回退；"
add_d = anchor_d + """
- **token 序列不可跨臂比**（`W958`）：同配置两次跑只有 **7/64** token 相同（专家换入窗口决定该 token 走 CPU 还是 GPU，
  `generate.cpp:12706`）⇒ 升级/移植的验收只认「六长度档性能 + 对金标 KL/top-1（先测地板）」，不认两臂 token 逐字相同；
- **三个 regime 不可混比**（`W969`/`W978`）：**冷读**（500–800）、**热读**（同 prompt >2×）、**带前缀复用**
  （引擎 tok/s 只算读入 token，`1910 reused + 5 read` 只除那 5 个）是三种口径；冷读拟合 `t ≈ 1.3 s + n/785`，
  2.3K 时固定成本占 38%、60K 占 2% ⇒ 报速率必须写 regime 且 `reused=0`；"""
if anchor_d in plan:
    plan = plan.replace(anchor_d, add_d, 1); ok.append(("ok", "判据 2 条"))
else:
    ok.append(("MISS", "判据锚点"))

# ---- E：§6.5 新块 ----
block = """
---

## §6.5 补记 · W972–W1001（2026-11-05 22:5x）—— 机主「昨天到今天还有该入而没入的吗」

审计方法：把两天的轮次（`W955`–`W1001`）逐个在 W832 里 `grep` 轮次号，再与 `PROGRESS`/`PARAM_REGISTER` 对照。
分两类：**账本已经更新、方案正文还是旧的**；**方案里根本没有这件事**。两类共六项，逐条处置如下。

| 号 | 缺口 | 现已写入哪里 | 判据 / 事实 |
|---|---|---|---|
| **P291** | `W958` 的判据改写从没进方案 | 本节「判据」区新增一条 | 两臂 token 序列不可比（7/64），验收改为六长度档 + 对金标 KL/top-1 |
| **P292** | `W969`/`W978` 的三个 regime 与截距模型 | 本节「判据」区新增一条 | 冷读 500–800 / 热读 >2× / 带复用不可当速率；`t ≈ 1.3 s + n/785` |
| **P293** | `W974` 的版本真相与重建策略 | §6.2 新25 + 参数册 | v0.9.0 = `cd959bae`、ggml 0.29.0、exe `-090`、r32；按 CUDA 目录指纹重建 |
| — | `R94`/`R95`/`R96` 只有队列一句话 | §6.2 新增 **新29/新30/新31** | 三条各有定义、判据、来源，不再「方案有、正文无」 |
| — | `R88`/`R90`/`R93` 定义行过期 | §6.2 新23/新25/新28 备注列 | 证伪 / 已上线降 PARTIAL / 已结案，各附轮次号 |
| — | `--pool-workers` 现值写成 0；X1/X2 状态与账本冲突 | §4.5 参数轴表、X1/X2 表 | 实为 **10**（+2.49%@2K）；X1 退 `ram` 已无可加，X2 前提不成立 |

**为什么这些会漏**：`plan_lint` 判据 A/D 只查「有号 → 有账」「方案有号 → 账本有行」，
**不查「账本更新了、方案正文没改」**——R88/R90/R93 三条正是这种：账本对、方案错，门全绿。
这次不新加判据（正文与账本的语义差没法机械判），改为**每轮回写时把「被改写的既有条目」单独列一行**，
见本节最后那张表。

### 两年（11-04 / 11-05）轮次覆盖现状

| 轮次段 | 内容性质 | 在方案里的位置 |
|---|---|---|
| `W955`–`W962` | 0.8.0 移植 / 逐位判据作废 / 0.8.0 慢 6% | 判据区（`W958`）+ 新25 备注 + 已结案 |
| `W963`–`W970` | 三个 regime / R90 上线 0.8.0 | 判据区（`W969`）+ 新25 备注 |
| `W972`–`W978` | NVMe / v0.9.0 / PLE mmap / mlock / 六档基线 | 新25 备注 + `P260`/`P261` + X1/X2 表 |
| `W979`–`W987` | 门的三次修正 / R93 结案 | 「判据」区（n≥10、三分）+ 新28 备注 |
| `W988`–`W995` | R94 / pool-workers=10 / R95 归因 / R87 判否 | 新29/新30 + §4.5 参数轴 + 已结案 |
| `W997`–`W1003` | R86 三臂扫描 / 六通道 | W1003 / W1003-b 两块 |
"""
if "## §6.5 补记 · W972–W1001" not in plan:
    plan = plan.rstrip("\n") + "\n" + block
    ok.append(("ok", "§6.5 新块"))

for f, p in [(PLAN, PLAN + BAK), (PROG, PROG + BAK), (REG, REG + BAK)]:
    shutil.copy2(f, p)
wr(PLAN, plan)

# ---- PROGRESS ----
lines = rd(PROG).split("\n")
hdr = lines[0]
body = [l for l in lines[1:] if l.strip() and not l.startswith("#")]
ids = {l.split("\t")[1] for l in body if len(l.split("\t")) > 1}

def row(block, rid, item, kind, cnt, done, status, note, ref):
    return "\t".join([block, rid, item, "W1004", kind, str(cnt), str(done), status, note, ref])

new = []
if "P291" not in ids:
    new.append(row("B6判定探针", "P291", "判据改写：两臂 token 序列不可比（W958），验收改为六长度档 + 对金标 KL/top-1",
                   "count", 1, 1, "DONE",
                   "**W1004 补登记**：`generate.cpp:12706` 专家换入窗口决定该 token 走 CPU/GPU，同配置两次跑只有 7/64 相同 ⇒ 升级/移植验收不认 token 逐字，质量必须走 serve + `STRATA_DUMP_FIRST_LOGITS` 对金标。此前只活在 W958 件里。",
                   "deploy/W832_OPT_PLAN_V2.md §6.5 判据"))
if "P292" not in ids:
    new.append(row("B6判定探针", "P292", "三个 regime 口径（冷读/热读/带复用）+ 冷读拟合 t≈1.3 s+n/785",
                   "count", 1, 1, "DONE",
                   "**W1004 补登记**：`W969` 定三 regime，`W978` 把 1.7 s 修正到 1.3 s（NVMe+mmap 后）。2.3K 时固定成本占 38%、60K 占 2% ⇒ 比速率必须写 regime 且 reused=0，否则 600/800/500 三个数会互相打架。",
                   "deploy/W832_OPT_PLAN_V2.md §6.5 判据"))
if "P293" not in ids:
    new.append(row("B10环境与版本", "P293", "v0.9.0 版本真相（cd959bae / ggml 0.29.0 / -090 / r32）+ 按 CUDA 目录指纹重建",
                   "count", 1, 1, "DONE",
                   "**W1004 补登记**：`W974` 证实 v0.9.0 相对 feaf8000 在 `ggml-cuda/` 逐字节相同、只差版本串 ⇒ 以后按 CUDA 目录指纹触发重建，不按 tag 盲重编；方案新25 里的 `b12099` 实为 master `feaf8000`。",
                   "deploy/W832_OPT_PLAN_V2.md §6.2 新25"))
for i, l in enumerate(body):
    f = l.split("\t")
    if len(f) >= 10 and f[1] == "X2" and f[7] == "OPEN":
        f[6] = "1"; f[7] = "NA"
        f[8] = (f[8].rstrip() + " **W977 结（2026-11-05 01:22）**：容器 memlock soft/hard 均 -1、`VmLck`/`VmPin` 均 0、"
                "宿主 `Mlocked` 25 MB ⇒ 原前提（锁不住）不成立；且决定不锁（HIP 注册≠pin，锁了还抢 THP）。")
        body[i] = "\t".join(f)
wr(PROG, hdr + "\n" + "\n".join(body + new) + "\n")

# ---- REGISTER ----
reg = rd(REG)
if "\t--pool-workers\t10\t" not in reg:
    line = "\t".join([
        "P265", "CLI", "--pool-workers", "10", "cpu/prefill", "ADOPTED", "-", "P26", "P129",
        "W989：prefill@2K 524.45 vs 511.73（+2.49%，band 1.00%）、TTFT −2.0%；args 35→37",
        "**W989 采纳（2026-11-05 19:3x）**：默认 0 = 每物理核一个（22 核 → 20 workers + host），对 22 核是过订阅；"
        "减半到 10 后 2K/8K prefill 均不劣、TTFT 更快。P26 的 REJECTED 只针对 **21** 这个值，不覆盖 10。"
        "账本同一件事见 PROGRESS P265。",
    ])
    reg = reg.rstrip("\n") + "\n" + line + "\n"
    wr(REG, reg)
    ok.append(("ok", "REGISTER P265"))

for s, a in ok: print(s, a)
