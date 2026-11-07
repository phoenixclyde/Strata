# -*- coding: utf-8 -*-
"""W1003-c：给「补了」的那批内容发号。

机主第三问「补的号呢？」——补记里那张六通道表没有 ID 列，正文还写着
"本节不新立条目"，等于给检查器开了一张免检通行证。本脚本做四件事：
 1) §6.2 新21（R86）判据改为 W1003 收窄口径；
 2) §6.5 补记的六通道表加「子号」列 → R86-C1..C6；
 3) 删掉"不新立条目"那句错话，改成登记说明；
 4) PROGRESS 增 6 条子账 + P289/P290，并更正 R86 本体里过期的 88.6%/+84%/+11% 口径。
"""
import io, os, shutil, sys

ROOT = r"D:/workbuddy_space/strata_ws/deploy"
PLAN = os.path.join(ROOT, "W832_OPT_PLAN_V2.md")
PROG = os.path.join(ROOT, "PROGRESS.tsv")
BAK = ".bak_w1003c"

def rd(p):
    return io.open(p, encoding="utf-8", errors="replace").read()

def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)

plan = rd(PLAN)
n_ok = 0

# ---------- 1) 新21 判据 / 备注 ----------
old_gate = ("| 单内核增益 <20% ⇒ 判否；stride 与 `moe_mmq_tab` 步进不同步 ⇒ 直接停 "
            "| canonical 基线已有：Q5_1 [2560,640] 1.53 ms = 5.47 TMAC/s（峰 25%）；A/B 需停服独占 |")
new_gate = ("| **W1003 收窄：只做 down**（gu=Q4_K/Q5_K repack 实测净亏 1.0–3.9× ⇒ 永不 repack）；"
            "立项条件 = R95 之后 **且** down-only 端到端 ≥5%（实测上限 −2.6~−3.3%，默认不开工）；"
            "stride 与 `moe_mmq_tab` 步进不同步 ⇒ 直接停 "
            "| canonical Q5_1 [2560,640] 1.53 ms = 5.47 TMAC/s（峰 25%）；"
            "W1003 三臂：down w32 0.79–0.81、Q8_0 0.54–0.61；六通道子号 **R86-C1…C6** 见 §6.5 补记 |")
if old_gate in plan:
    plan = plan.replace(old_gate, new_gate, 1)
    n_ok += 1
else:
    print("!! 新21 判据锚点未命中")

# ---------- 2) 六通道表加子号列 ----------
old_tbl_start = "| 通道 | 落点（file:line） | 状态 | 本轮补的是什么 |"
i = plan.find(old_tbl_start)
if i < 0:
    print("!! 六通道表锚点未命中")
    sys.exit(1)
j = plan.index("\n\n", i)
old_tbl = plan[i:j]

new_tbl = """| 子号 | 通道 | 落点（file:line） | 现状 | 账本 |
|---|---|---|---|---|
| **R86-C1** | 权重上传 | arena 装载时一次性 repack，**不进热路径**（专家在 host arena 71.7 GiB，prefill 每 chunk 借 2606 槽，借/换出须保持 repacked 布局） | 设计定稿，代码未动 | OPEN（P285/P287 供判据） |
| **R86-C2** | 调度分派 | `src/prefill/moe_mmq.cu:498` `Context::run`：`expert_stride` 由 `expert_bytes/type_bytes` 换成 `repack_gcn_nbytes`；`Product` 加 `layout`（同层 gu=canonical、down=repacked，不能整层切换） | NOT_STARTED | OPEN |
| **R86-C3** | 激活对齐 | `quantize()` 已产出 grouped MMQ 布局；缺我们自己钉 `block_q8_1_mmq`（128 值 / 144 B、DS4 layout）的尺寸与偏移断言 | PARTIAL | PARTIAL |
| **R86-C4** | 融合 | `prefill.cpp:5300` `gu.w_rows = 1280` 已是单次调用 | 理由更正（非「prefill 无红利」） | NA |
| **R86-C5** | 验收 | 逐位等价 + 六长度档 + 2×CV + KL/top-1 + `STRATA_REPACK_D` 灰度 + 镜像回滚 | NOT_STARTED | OPEN |
| **R86-C6** | 混合分派 | 原「按 `expert_bounds` 分段」 | 解散：w32 在 down 全行数档 0.79–0.81，没有「留给 canonical 的大段」 | WITHDRAWN |"""

plan = plan[:i] + new_tbl + plan[j:]
n_ok += 1

# ---------- 3) 删掉"不新立条目"那句 ----------
old_line = "归 R95 名下；本节不新立条目，免得队列里长出没有账本的 ID。"
new_line = ("归 R95 名下。~~本节不新立条目~~ —— 这句是错的（W1003-c 第三问）："
            "「不新立 ID」的结果是这批结论没有任何号，检查器看不见它。"
            "已改按号登记：六通道 **R86-C1…C6**（上表），举一反三三条 **P290**，"
            "R86 本体判据回写 §6.2 新21。")
if old_line in plan:
    plan = plan.replace(old_line, new_line, 1)
    n_ok += 1
else:
    print("!! 「不新立条目」锚点未命中")

# ---------- 4) 补记末尾追加登记说明 ----------
anchor = "   前者是后者的 **3–5 倍量级**；R86 的立项条件因此写成「R95 做完或判否之后」。"
add = anchor + """

### 号（机主第三问的直接答案）

上面这张表的每一行现在都有号：**R86-C1 … R86-C6**（子号，父条目 R86 / §6.2 新21）；
举一反三三条 = **P290**；六通道落点定稿这件动作 = **P289**。
三个都已进 `PROGRESS.tsv`，`plan_lint` 判据 A/D 从此能看见它们——
上一版没有号，所以门"绿"只是因为它根本不知道有这回事。"""
if anchor in plan:
    plan = plan.replace(anchor, add, 1)
    n_ok += 1
else:
    print("!! 举一反三末尾锚点未命中")

# ---------- PROGRESS ----------
shutil.copy2(PROG, PROG + BAK)
shutil.copy2(PLAN, PLAN + BAK)
wr(PLAN, plan)

lines = [l for l in rd(PROG).split("\n") if l.strip()]
hdr = lines[0]
body = [l for l in lines[1:] if not l.startswith("#")]
ids = {r.split("\t")[1] for r in body}

def row(block, rid, item, kind, cnt, done, status, note, ref):
    return "\t".join([block, rid, item, "W1003", kind, str(cnt), str(done), status, note, ref])

new_rows = []
if "R86-C1" not in ids:
    new_rows += [
        row("B4上游移植", "R86-C1", "R86 的 C1 权重上传：arena 装载时一次性 GPU 侧 repack（不进热路径，借槽/换出保持 repacked 布局）",
            "count", 1, 0, "OPEN",
            "**W1003-c 立（2026-11-05 22:4x，机主「补的号呢」）**：此前只写在 §6.5 补记的无 ID 表里 ⇒ 无号即无账。尺寸账已由 P287 给出（Q5_1 中性、Q8_0 +2.3%），本条的活是装载路径本身。",
            "deploy/W832_OPT_PLAN_V2.md §6.5 补记 R86-C1"),
        row("B4上游移植", "R86-C2", "R86 的 C2 调度分派：`Context::run` 三路分派 + `expert_stride` 换 `repack_gcn_nbytes` + `Product.layout`（同层混布局）",
            "count", 1, 0, "OPEN",
            "**W1003-c 立**：落点 `src/prefill/moe_mmq.cu:498`。必须支持「同层 gu=canonical、down=repacked」，整层切换会砸掉 gu。",
            "deploy/W832_OPT_PLAN_V2.md §6.5 补记 R86-C2"),
        row("B4上游移植", "R86-C3", "R86 的 C3 激活对齐：自钉 `block_q8_1_mmq` 尺寸/偏移断言（128 值 / 144 B、DS4 layout）",
            "count", 1, 0, "PARTIAL",
            "**W1003-c 立**：`quantize()` 已产 grouped 布局，两臂共用同一份激活（W1001 起），但断言仍缺 —— 缺它就无法证明移植后激活逐字节同构。",
            "deploy/W832_OPT_PLAN_V2.md §6.5 补记 R86-C3"),
        row("B4上游移植", "R86-C4", "R86 的 C4 融合（上游 #31188 MoE gate/up+GLU）：本树是否成立",
            "count", 1, 1, "NA",
            "**W1003-c 闭**：`prefill.cpp:5300` `gu.w_rows=1280` 本来就是一次调用，上游省的是第二次 launch，此处不存在。理由更正过（旧说法「prefill 无红利」是错的）。",
            "deploy/W832_OPT_PLAN_V2.md §6.5 补记 R86-C4"),
        row("B4上游移植", "R86-C5", "R86 的 C5 验收链：逐位等价 + 六长度档 + 2×CV + KL/top-1 + `STRATA_REPACK_D` 灰度 + 镜像回滚",
            "count", 1, 0, "OPEN",
            "**W1003-c 立**：判据先写死、未跑。端到端上限 −2.6~−3.3% 仍低于 5% 门 ⇒ 本条只在 R95 之后且立项通过时启动。",
            "deploy/W832_OPT_PLAN_V2.md §6.5 补记 R86-C5"),
        row("B5本机缺口", "R86-C6", "R86 的 C6 混合分派（原按 `expert_bounds` 分段 repacked/canonical）",
            "count", 0, 0, "WITHDRAWN",
            "**W1003-c 解散**：三臂扫描 w32 在 down 全行数档 0.79–0.81，没有「留给 canonical 的大段」；原前提（320 行慢 15%）是 mx 的 `use_w32` 规则造成的。计 0，移出分母。",
            "ci/repack_ab/WIDTH_SWEEP.tsv"),
    ]
if "P289" not in ids:
    new_rows.append(row("B5本机缺口", "P289", "R86 六通道执行落点定稿并编号（C1–C6，含 file:line 与同层混布局）",
                        "count", 1, 1, "DONE",
                        "**W1003-c**：此前六通道只是 §6.5 里一张无 ID 的表 + 一句「不新增 ID」⇒ 门看不见。现编号 R86-C1…C6，parent 仍是 R86/新21，不另开条目定义。",
                        "deploy/W832_OPT_PLAN_V2.md §6.5 补记"))
if "P290" not in ids:
    new_rows.append(row("B6判定探针", "P290", "repack 的三条判断写死：mx `use_w32` 阈值不可照抄 / 上游两笔融合对 prefill N/A / 性价比排序 3–5 倍",
                        "count", 1, 1, "DONE",
                        "**W1003-c**：①我们 32→1024 行 w32 全胜（0.79–0.955），照抄 `n_assign<2*BN_ID*ne02` 等于把上游调参搬进瓶颈；②#29948/#31188 省第二次 launch，我们一次就 1280 行；③dequant 8–18% / wait copy 7–15% 是 down repack 的 3–5 倍 ⇒ R86 排在 R95 之后。",
                        "deploy/W832_OPT_PLAN_V2.md §6.5 补记 举一反三"))

# 更正 R86 本体的过期口径
fixed = []
for l in body:
    f = l.split("\t")
    if len(f) >= 10 and f[1] == "R86":
        f[2] = ("Q5_1 down 的权重布局重排（只做 down；gu=Q4_K/Q5_K 实测净亏 1.0–3.9× ⇒ 永不 repack）"
                "：down 占专家总字节 35%、down 内 Q5_1 占 86%（`AUDIT24` 修正 88.6%）")
        f[8] = (f[8].rstrip() + " **W1003 更正**：item 里旧的「+11% prefill」是外证折算，本机三臂实测 down-only "
                "端到端上限 −2.6~−3.3%（<5% 门）；六通道拆成 R86-C1…C6，C4 结 NA、C6 解散。")
        l = "\t".join(f)
    fixed.append(l)

out = hdr + "\n" + "\n".join(fixed + new_rows) + "\n"
wr(PROG, out)

print("plan anchors ok:", n_ok, "/4")
print("added rows:", len(new_rows))
