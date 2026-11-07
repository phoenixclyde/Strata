# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 08:4x W932 · R75 证伪 + 抓到一个测量方法系统缺陷 + **`--prefill auto:16384` 采纳**（7 次重启）
- **R75 假设证伪**：R66 三补丁把 16384 chunk 的 borrows **2606→1904（−27%）**、8192 chunk 的 **1578→1226**，但 64K TTFT **完全不动**（76.557→76.451 / 81.493→81.344）⇒ **borrows 不是长 prompt 变慢的原因**。
- **抓到测量方法缺陷（本轮最重要，影响所有历史 prefill 数据）**：`ci/bench_pair.py` 的 `text_of(words, seed)` 用 `random.Random(seed)`，**同一 seed 生成的短 prompt 是长 prompt 的前缀**（同 seed 前 N 词相同）⇒ 同 seed 跑不同长度会部分复用；另一表现：同一参数连跑两次不重启 ⇒ 第二次**全部命中 prompt cache**（实测 TTFT 掉到 0.177–0.199 s，median 被拉成 30.174、**CV 16.2%**）。
- **修法 = 纪律 ⑩（最高优先级，已进 W832）**：**只采信服务端日志 `0 reused` 的记录**（格式 `prompt N tokens = R reused + (N-R) read in T ms`）。`bench_pair` 本身也应改成 `seed*100003 + words` 使不同长度不共享前缀。
- **W931 结论更正（我自己的错）**：W931 的 8192 臂 64K = 71.130 是 `8192 reused + 53054 read` 的污染数据。**只取 0 reused**：8192 = **81.0–81.5 s（752–756 tok/s）**、16384 = **76.2–76.5 s（801–803）** ⇒ **16384 快 6.2%，不是慢 7.6%**。W931 的「倒 U」里"长 prompt 上 8192 更好"这一半完全错。
- **`auto:16384` 采纳（已落生产）**：全长度 0 reused —— 6.4K ≈0、16K +1~3%、32K +5%、64K **+6.2%**、**130K +8.1%**（165.1 s/788.7 vs 177.9 s/729.6）⇒ **越长优势越大**（与"chunk 越大 GEMM 的 M 越大、权重复用越好"一致）。**decode 无影响**（n=9 median **80.58 tok/s**、CV 2.2%，对照 79.05 = +1.9% 噪声内；首轮 n=4 得 71.69 是**预热不足**，W920 老教训复现）。**多轮复用 99.68%**（对照 99.72%）。**显存无净代价**（expert cache 7463 / VRAM free 920 MiB 均不变，仅 prefill 期 borrows 1578→2606）。按负载加权 **≈+2.2% prefill**。**`auto:32768` 不采纳**（借 62.5% cache，32K 上比 16384 慢 1.9%）。
- **R66 三补丁彻底关闭**：两个 chunk 尺寸下都无收益（−0.14~−0.18%），不再作为任何组合的候选。
- **生产变更**：`--prefill auto` → **`auto:16384`**（唯一变更）、config **`fcf4df5b`**、engine 恢复 `a97f4479`（实验件 `9d9cbe17` 已回滚）、borrows 2606、`/health ok`、restarts=0。回滚法：`cp .bak_w932 → config` + restart。
- **新条目 R76（OPEN）**：16384 下的**部分前缀复用** —— 日志显示 8192 模式能 `8192 reused`、16384 模式 `0 reused` ⇒ **复用粒度 = chunk 大小**。长文档多轮（末尾追加几句）这类场景没测，需量化。
- **队列**：`~~…~~ → ~~R70~~ → ~~R75~~ → **R76** → **R65** → **R74** → R49 → R50 → R30′`。进度 **160 条 / 98 已结 = 61.2%**，主线 **132 / 98 = 74.2%**。
- 产物：`deploy/W932_R75_AND_CHUNK16384_ADOPT.md`；`PROGRESS.tsv` R70 改判 DONE + R75(DONE_NEG) + R76(OPEN)；`PARAM_REGISTER` P259 改 ADOPTED；`W832` 纪律 ⑩ + 队列。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
