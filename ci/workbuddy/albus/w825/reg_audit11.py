# -*- coding: utf-8 -*-
"""AUDIT11 落账：审计覆盖 + 两处 CORRECTION + 判据规则。内层引用统一用「」。"""
import csv, os

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "params", "PARAM_REGISTER.tsv"))
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], [r for r in rows[1:] if r and r[0].strip()]
ids = [r[0] for r in body]
print("before:", len(body), "rows, last", ids[-3:])

M = "measurement"; G = "governance"

NEW = [
    ["P167", "audit", "AUDIT11 覆盖范围（W810–W825，8 份文档）", "deploy/AUDIT11_W810_W825.md",
     G, "REFERENCE", "—", "—", "P160/P165",
     "用 `albus/w825/audit_scope.py` 从 31 份审计文档的范围声明区提取轮次、与全部轮次求差集，"
     "再用 `audit_gap2.py` 全文复核（避免「只在前 40 行没出现」的误判）："
     "审计链 AUDIT6→AUDIT10 连续覆盖 W776–W809；**W810/W815/W816/W820/W822/W823/W824/W825 零提及**，即本轮范围"
     "（含并入的 W812/813/814、W817/818/819、W821）。",
     "**P0=3 / P1=12 / P2=9，撤回 3 条（含审计者自己 1 条）**。"
     "最重要的结论：**没有任何一次生产改动依赖错误数字**（5 项改动逐项回溯）。"
     "系统性缺陷的新形态 = **把一次冷启动读数当稳态基线**（区别于 AUDIT8/9/10 的「总量口径判漂移」）。"],

    ["P168", "env", "启动后首请求带约 1.0 s 冷启动（判据规则）", "n/a",
     M, "REFERENCE", "`STRATA_TRACE` 或用 `mt_read` 时标注请求序号", "—", "P167",
     "原始件 `w816_det_*.txt` 的 `TR` 行逐字：首请求 `read 69 tokens (batched) in 1018.3 ms`，"
     "第二次 `167.7 ms`，其后稳定 57–65 ms；同一批三次启动一致。"
     "用它解释 W822 的 427 与今天实测 525：`6.17 − 5.02 = 1.15 s ≈ 1018 ms`。",
     "**规矩**：任何启动后的读数必须标注「第几个请求」。首请求只能与「同为首请求」的臂配对比较，"
     "**不能当稳态基线**。这条同时更正 W822 的「生产 427 tok/s」（真实稳态 **525**）与 W810 各臂 ready 的离散（60–290 s）。"],

    ["P169", M, "生产 prefill 基线 427 → 525 tok/s（2636 token）", "525",
     M, "CORRECTION", "—", "—", "P168",
     "今天（10-30 02:0x）在同一语料 `sha16=989c7369da9433ce`、同 2636 token 上实测 **5.02 s = 525 tok/s**；"
     "连发三次 5.02 / 4.84 / 4.73 s（531 / 492 tok/s）。同口径 1500/3000/6000 字符测得 3.85 / 4.78 / 7.05 s，"
     "对 W824 的 A 臂 3.34 / 4.66 / 7.73 ⇒ +15.3 / +2.6 / **−8.8%**（长文本确实因 `ATTN_REDUCE12` 变快）。",
     "W822/W825 引用的 427 是**冷启动首请求**，偏低 **18.6%**，已就地把两份文档改正。"
     "注意：2636 token 与 4568 token 的 tok/s **不能直接比**（固定开销摊薄不同），427 vs 525 只在同 token 数下成立。"],

    ["P170", "engine", "换权重的速度代价（原写 −16%/−14%）", "实为：仅解码 −14%",
     M, "CORRECTION", "—", "—", "P169",
     "`W822:4` 原写「旧 IQ4_XS 508 / 48.9，新档慢 16% / 14%」。AUDIT11 复核：①**508 无测量条件记录**"
     "（哪一次、是否首请求、暖冷缓存皆未写），而对照组 IQ4 已被删 ⇒ **不可复核**；②427 是冷启动值，稳态 525。"
     "⇒ 提示侧「慢 16%」**不成立为结论**（可能持平甚至略快）；**确定存在的代价只有解码** 42.0 vs 48.9 = **−14%**。",
     "换档的账应改写为「**用约 14% 解码速度换上游 +4.2pp top-1（本机从未验证）**」。"
     "同时登记一条不可逆后果：IQ4 已删（174.5 GiB），「换权重的精度收益」在本机**已无法复核**，除非重下 88 GB。"],

    ["P171", "env", "STRATA_GDN_HEAD=1 / GDN_PP=2 在 gfx906 上未验证", "1 / 2",
     "prefill", "PENDING", "—", "—", "P165",
     "两者来自 **gfx1151 的 exact 表**（`arch_defaults.cpp:61-62`，在 Aurora/S23 上 byte-identical 验证过），"
     "但**不是在 gfx906 上验的**；`prefill/kernels.cu:1375` 只说 the same arithmetic in the same order。"
     "本机从换权重前就一直开着，**从未量过 KL**。",
     "补进数值债账本（P165 现有 6 项 → **8 项**）。它俩属于「从别的架构抄来、理论上 exact、本机未验」这一类，"
     "与 RT_SKIP/kv 那类「上游明说会改位」不同，风险低但账上不能留空。"],

    ["P172", "upstream", "0.1.53 对 x86 的实质变更 ≈ 版本号", "—",
     G, "CONFIRMED", "—", "—", "P152/P167",
     "`src/kernels/cpu/portable.cpp:1` 逐字 `the CPU kernel symbols on a non-x86 build (aarch64: DGX Spark / GB10)`；"
     "`nv_defaults.*` 是 NVIDIA 默认值；`moe_fused_iq.cu` 是 sm_121(GB10) 的瓦片阈值。"
     "加上 W824 的全树校验（543/548 一致、22 个差异全在 `src/dsv41/*`、二进制里 `dsv41` 字符串 0）。",
     "W824 原写「4 个参与编译的文件」技术上不错但会误导：对**本机 x86_64 + gfx906** 的实质变更 ≈ **只有版本号**。"
     "这也解释了 A/B「三项全为正但幅度小」——本来就不该有效益。已就地更正 W824。"],

    ["P173", M, "0.1.53 的 A/B 判据带用错（P152 补证）", "三项全正、超同长度地板",
     M, "CORRECTION", "—", "—", "P152/P167",
     "W824 §1 原写「三档全在 4.4% 内（同二进制漂移带 4.6%）」。复核：那个 4.6% 是 **1453 格**的 A/A2 带；"
     "**4568 格 A/A2 只差 0.1%**（8.26 vs 8.27），B53 的 +3.3% **超它 33 倍**；1453 格 +9.1% 也超 2 倍；且**三项全为正**。",
     "正确表述：「三项全为正、多数超出同长度地板，但**未做 ABBA 配对**，不能判为真回归」。"
     "结论（升级理由是正确性而非速度）不变，但「无可测差异」这个措辞过强，已就地更正。"],

    ["P174", M, "ATTN_REDUCE12 的 −3.8% 经相位逐项加总核实（P156 补证）", "闭合到 1 ms",
     "prefill", "CONFIRMED", "—", "—", "P156",
     "AUDIT11 把 N1/A1 的 **20 个相位逐项加总**：N1 合计 **7033** vs total **7034**（差 1 ms）；"
     "A1 合计 **6765** vs total **6765**（**精确闭合**）。`qsa attn 1089→810（−279 ms）` + 其余净 +11 ms = **−268 ≈ −269**。",
     "这是全轮**唯一**经得起最严格核对、且被采纳的收益。P156 的采纳决定**维持不变**。"],

    ["P175", M, "跨容器实例的 prefill 重复性 0.1%（措辞更正）", "—",
     M, "CORRECTION", "—", "—", "P156/P167",
     "W824 §9.2 原写「**同容器内**重复性 0.1%」。但 `w824_arm.sh:18,21` 每臂都 `rm -f` 后 `docker run` ⇒ N1/N1b 是"
     "**两个容器实例**。能稳到 0.1% 的原因是**用 GPU 事件计时的相位表**，不是「同一容器」。",
     "措辞已更正。这条区分的实际意义：**相位表（GPU）稳 0.1%，decode 的 tok/s（wall）同批漂 12–16%** —— "
     "不能把 0.1% 套到 decode 上，否则会得出「decode 不该有噪声」的错误预期。"],
]

added = []
for r in NEW:
    if r[0] in ids:
        print("skip", r[0]); continue
    body.append(r); added.append(r[0])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr); w.writerows(body)

print("added:", added)
print("after:", len(body), "rows; cols_ok:", all(len(r) == 11 for r in body))
