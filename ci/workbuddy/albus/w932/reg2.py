# -*- coding: utf-8 -*-
"""W932: R75 DONE_NEG、R70 改判采纳、P259 改 ADOPTED、R76、方法纪律 10"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue

    if f[1] == "R70":
        f[7] = "DONE"
        f[8] += (
            " 【W932 改判 2026-11-04 08:4x｜DONE_NEG → DONE，采纳 auto:16384】"
            "**W931 的 64K 数据被污染，结论反转**：`ci/bench_pair.py` 的 `text_of(words, seed)` 使"
            "**短 prompt 成为长 prompt 的前缀**（同 seed 前 N 词相同），W931 的 8192 臂 64K 记录是 "
            "`8192 reused + 53054 read`（不是纯 prefill）⇒ 71.130 s 无效；"
            "**只采信日志 `0 reused` 的记录后**：8192 = **81.0–81.5 s（752–756 tok/s）**、"
            "16384 = **76.2–76.5 s（801–803）** ⇒ **16384 快 6.2%，不是慢 7.6%**。"
            "全长度（0 reused）：6.4K ≈0、16K **+1~3%**、32K **+5%**、64K **+6.2%**、"
            "**130K +8.1%**（165.1 s/788.7 vs 177.9 s/729.6）⇒ **越长优势越大**。"
            "decode 无影响（n=9 median **80.58 tok/s**，CV 2.2%，对照 79.05 为 +1.9% 噪声内；"
            "首轮 n=4 得 71.69 是预热不足）。多轮复用 **99.68%**（对照 99.72%，−0.04pp）。"
            "显存无净代价（expert cache 7463 / VRAM free 920 MiB 均不变；仅 prefill 期间 borrows 1578→2606）。"
            "按负载加权 **≈ +2.2% prefill**（>64K 占 24.8% 是主要贡献）。"
            "**`auto:32768` 仍不采纳**（借 62.5% cache，32K 上比 16384 慢 1.9%）。"
            "**已落生产**：config `fcf4df5b`"
        )
        lines[i] = "\t".join(f)
        print("R70 -> DONE (adopted)")

    if f[1] == "R75":
        f[6] = "1"
        f[7] = "DONE_NEG"
        f[8] += (
            " 【W932 实测 2026-11-04 07:5x-08:4x｜7 次重启】**假设证伪**：R66 三补丁把 16384 chunk 的 borrows "
            "**2606 → 1904（−27%，省 2.05 GiB）**、8192 chunk 的 **1578 → 1226（−22.3%）**，"
            "但 64K 的 TTFT **完全不动**（16384: 76.557→76.451，−0.14%；8192: 81.493→81.344，−0.18%）"
            "⇒ **borrows 不是长 prompt 变慢的原因**，而且 16384 本来就不慢（W931 的 71.130 是 reused 污染数据）。"
            "**结论**：两条单独都不成立，组合也不成立；R66 三补丁维持 DONE_NEG（对 prefill 无收益、对 decode/质量无害），"
            "**不再作为后续组合的候选**。实验二进制 `9d9cbe17` 已回滚，生产恢复 `a97f4479`"
        )
        lines[i] = "\t".join(f)
        print("R75 -> DONE_NEG")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))

# R76
rows = io.open(p, encoding="utf-8").read().split("\n")
while rows and rows[-1] == "":
    rows.pop()
rows.append("\t".join([
    "B3内存与缓存", "R76",
    "`auto:16384` 下的**部分前缀复用**：长文档多轮（第二次只在末尾加几句）时，"
    "8192 chunk 能复用整 8192，16384 chunk 复用 0 ⇒ 量化这类场景的代价",
    "W932 4.3", "count", "1", "0", "OPEN",
    ("**W932 立（2026-11-04 08:4x，零停服）**：已采纳 `auto:16384`，但有一个角落没测 —— "
     "日志显示 64K 请求在 8192 模式下能 `8192 reused`（因为短 prompt 是它的前缀），"
     "而 16384 模式下 `0 reused`（15348 的前缀凑不满一个 16384 块）⇒ **复用粒度 = chunk 大小**。"
     "多轮完整对话不受影响（实测 99.68%，因为只有 ~6.6K = 1 chunk）。"
     "**做法**：构造长文档场景 —— 首轮 30K tokens，第二轮在同一文档末尾追加 200 tokens 后追问；"
     "分别在 8192/16384 下量 turn2 的 `reused` 与 TTFT。**判据**：若 16384 的 turn2 重读量显著变大"
     "（复用率从 ~99% 掉到 <90%），则需按场景二选一，或改 `--prompt-cache-every` 与其对齐"),
    "W932",
]))
rows.append("")
io.open(p, "w", encoding="utf-8").write("\n".join(rows))
print("R76 appended")

# P259 -> ADOPTED
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
pr = io.open(q, encoding="utf-8").read().split("\n")
for i, l in enumerate(pr):
    f = l.split("\t")
    if f and f[0] == "P259":
        f[3] = "auto:16384（2026-11-04 采纳）"
        f[5] = "ADOPTED"
        f[10] += (
            " **【W932 采纳 2026-11-04 08:4x】**W931 的「64K 上 16384 慢 7.6%」是**污染数据**"
            "（`bench_pair` 的 seed 使短 prompt 成为长 prompt 前缀，那条记录是 `8192 reused + 53054 read`）。"
            "只采信 `0 reused` 后：**8192 = 81.0–81.5 s / 752–756 tok/s、16384 = 76.2–76.5 s / 801–803 tok/s ⇒ +6.2%**；"
            "130K **+8.1%**（165.1 s/788.7 vs 177.9 s/729.6）；16K +1~3%；32K +5%；6.4K ≈0。"
            "**decode 无影响**（n=9 median 80.58 tok/s、CV 2.2%，对照 79.05）。**多轮复用 99.68%**（对照 99.72%）。"
            "**显存无净代价**（expert cache 7463 / VRAM free 920 MiB 均不变；仅 prefill 期 borrows 1578→2606）。"
            "按负载加权 **≈ +2.2% prefill**。**`auto:32768` 不采纳**（借 62.5% cache，32K 上比 16384 慢 1.9%）。"
            "**回滚**：`cp .bak_w932 → config` + restart"
        )
        pr[i] = "\t".join(f)
        print("P259 -> ADOPTED")
        break
io.open(q, "w", encoding="utf-8").write("\n".join(pr))

# W832 纪律 + 队列
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
anchor = "> **执行顺序（2026-11-04"
rule = (
    "> **方法纪律追加（`W932` 2026-11-04 08:4x｜最高优先级）**：⑩ **prefill 的每一个数据点都必须带 `0 reused`** —— "
    "服务端日志固定格式 `prompt N tokens = R reused + (N-R) read in T ms`，`R > 0` 的一律作废。"
    "两个具体陷阱：①`ci/bench_pair.py` 的 `text_of(words, seed)` 用 `random.Random(seed)`，"
    "**同一 seed 生成的短 prompt 是长 prompt 的前缀**（同 seed 前 N 词相同）⇒ 同 seed 跑不同长度会部分复用；"
    "②同一参数连跑两次（不重启）⇒ 第二次**全部**命中 prompt cache（实测 TTFT 掉到 0.17–0.20 s），"
    "median 被拉低、CV 爆到 16%。**本轮教训**：W931 因未筛 `reused` 把 16384 判成长 prompt 慢 7.6%，"
    "实际是快 6.2%，结论整整反了一次。\n>\n"
)
assert anchor in s
s = s.replace(anchor, rule + anchor, 1)

ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 08:4x 修，`W932`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70"
            "（**已采纳 `auto:16384`**：六长度全不劣、130K +8.1%、decode 与多轮复用不受影响）~~ → ~~R75"
            "（假设证伪：补丁压 borrows 27% 但 TTFT 不动）~~ → **R76**（16384 下的部分前缀复用） → "
            "**R65**（只读） → **R74**（W4A4 精度门） → R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))
print("done")
