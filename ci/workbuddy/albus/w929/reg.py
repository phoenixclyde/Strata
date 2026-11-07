# -*- coding: utf-8 -*-
"""W929: M3 结项 + P258 显存账纠正 + R74 先验降权 + 方法纪律"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

# ---------- 1. PROGRESS: M3 -> DONE_NEG, R74 补先验 ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "M3":
        f[6] = "1"
        f[7] = "DONE_NEG"
        f[8] += (
            " 【W929 实测 2026-11-04 00:4x-01:1x｜3 次重启，生产已恢复】两臂同带 "
            "`STRATA_PREFILL_TIMING=1`（观测成本对两臂相同），同 prompt 词数各 3 次、token 数完全配对："
            "**qsa attn 1202 → 1211 ms（+0.75%，噪声内）**；qsa proj +0.23%、gemm gate/up −0.11%、"
            "gemm down −0.09%、dequant −0.37%、GPU timeline 8475 → 8480 ms（+0.06%）；"
            "端到端 TTFT **9.218 vs 9.217 s**。⇒ **k8v8 对 prefill 零差异**。"
            "**显存账纠正**：expert cache **7463 → 7223（−240 槽 / 717 MiB）**，"
            "**不是 P04 记的 9761→8047（−1714 槽 / 3.8 GiB）** —— 后者是旧 pack（2.31 MiB/槽）年代的数，"
            "当前 2.99 MiB/槽且 KV 按需 `kv ensured`；折合 tokens 从 354K 降到 ~66K。按 3.2% 容量损失外推，"
            "decode 影响仅 **−1.1~2.3%**（而非 −7.7~16.6%）。**判 DONE_NEG 的理由**：k8v4 已过 needle 门 6/6，"
            "用 decode 换更小的 KL 数字不划算（decode 占 64–83%，W798）。"
            "**两条副产品（更重要）**：①k8v4 的 V 每次 gather 都做 q4 反量化，换成 int8 后 attn 零变化 "
            "⇒ **4-bit 解包成本 ≈ 0**，直接削弱 R74 的一个卖点；②int8 多读 29.4% 字节而 attn 不变 "
            "⇒ **attention 不是带宽受限**（与 W926 的 O(L^1.20) 拟合一致）。"
            "**测量纪律**：观测 env 是启动时 `getenv` 静态初始化、不能热切换，其代价无法单独测 "
            "⇒ 只能记「未测出」，不能写「免费」也不能写「贵 3.6%」（那 3.6% 是 cache 冷热差）"
        )
        lines[i] = "\t".join(f)
        print("M3 -> DONE_NEG")

    if f[1] == "R74":
        f[8] += (
            " 【W929 先验再降 2026-11-04 01:1x】M3 的 A/B 给出一个直接削弱本条的实测："
            "k8v4 的 V 每次 gather 都做 q4 反量化，换成纯 int8（**零解包**）后 `qsa attn` "
            "只差 +0.75%（噪声内）⇒ **4-bit 解包在这张卡上成本 ≈ 0**。"
            "而 dot8 相对 dp4a 的收益拆开只有两项：(a) 指令数减半（8 元素 2 条→1 条）；(b) 少一次解包。"
            "(b) 已被本轮实测归零 ⇒ **R74 的全部收益只剩 (a)**，而 (a) 的端到端上限 W928 已算为 "
            "**3.22% = 噪声门 3.2%**。⇒ R74 仍保留（精度门是唯一还能翻盘的点，且离线可做、不占重启），"
            "但**优先级应排在 R69/R70 之后**，除非离线 KL 明显低于 0.002（远好于噪声底 0.0032）才值得动内核"
        )
        lines[i] = "\t".join(f)
        print("R74 note appended")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))

# ---------- 2. PARAM_REGISTER: P258 ----------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
rows = io.open(q, encoding="utf-8").read().split("\n")
p258 = "\t".join([
    "P258",
    "REF",
    "--kv int8（=k8v8）的真实代价与收益",
    "不采纳（k8v4 保留）",
    "kv",
    "REFERENCE",
    "P04",
    "-",
    "P50;P247",
    ("**W929 实测（2026-11-04 00:4x-01:1x，3 次重启）**：①**prefill 零差异** —— qsa attn "
     "**1202 → 1211 ms（+0.75%，噪声内）**，GPU timeline 8475 → 8480 ms，端到端 TTFT 9.218 vs 9.217 s；"
     "②**显存代价只有 717 MiB** —— expert cache **7463 → 7223（−240 槽）**，"
     "**纠正 P04 的 3.8 GiB / −1714 槽**（那是旧 pack、2.31 MiB/槽、KV 未按需的年代；现 2.99 MiB/槽、"
     "KV 走 `kv ensured` 动态加载）；折合 ~66K tokens 而非 354K；③**质量更好**（KL 0.0416 < k8v4 0.0704，P50）；"
     "④按 3.2% 容量损失外推 decode 仅 **−1.1~2.3%**（而非 P04 的 −7.7~16.6%）。"
     "**判决：不采纳** —— k8v4 已过 needle 任务门 6/6，用 decode 换更小的 KL 不划算。"
     "**但记档为「长上下文重任务的便宜升级选项」**：只花 717 MiB（不是 3.8 GiB）即可把 KV 质量提到 int8，"
     "将来若做长文档 needle / 多文档对齐，先看这条"),
])
# 插到 P257 之后（保持编号顺序），否则追加
insert_at = None
for i, r in enumerate(rows):
    f = r.split("\t")
    if f and f[0] == "P257":
        insert_at = i + 1
        break
if insert_at is not None:
    rows.insert(insert_at, p258)
    print("P258 inserted after P257")
else:
    rows.append(p258)
    print("P258 appended")
io.open(q, "w", encoding="utf-8").write("\n".join(rows))

# ---------- 3. W832: 方法纪律 ⑧ + 队列 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
anchor = "> **执行顺序（2026-11-04"
rule = (
    "> **方法纪律追加（`W929` 2026-11-04 01:1x）**：⑧**观测项的代价必须做同状态 A/B** —— "
    "启动时 `getenv` 静态初始化的开关不能热切换，其代价只能记「未测出」，"
    "**禁止拿「热 cache 基线 vs 冷 cache 实验臂」的差当作开关代价**（本轮误算 3.6%，实为 cache 冷热）。"
    "⑨**跨代记录必须重测，不可直接引用** —— P04 的「int8 多占 3.8 GiB / −1714 槽」在当前 pack 下实测只有 "
    "**717 MiB / −240 槽**，差 5 倍（每槽 2.31 → 2.99 MiB、KV 改为按需加载）。凡引用旧参数账的量化结论，"
    "先核它的 pack 与槽大小。\n>\n"
)
assert anchor in s
s = s.replace(anchor, rule + anchor, 1)

lines = s.split("\n")
for i, l in enumerate(lines):
    if l.startswith("> **执行顺序（2026-11-04"):
        lines[i] = (
            "> **执行顺序（2026-11-04 01:1x 修，`W929`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3（k8v8 对 prefill 零差异；"
            "显存只 717 MiB，P258 记档）~~ → **R69** → **R70** → **R65** → **R74**（W4A4 精度门："
            "解包卖点已被 M3 归零，只剩指令数减半 = 端到端 3.22% = 噪声门；仅当离线 KL < 0.002 才动内核） "
            "→ R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(lines))
print("W832 done")
