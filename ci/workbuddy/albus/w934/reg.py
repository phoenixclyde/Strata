# -*- coding: utf-8 -*-
"""W934: R65 结项 + R77（cherry-pick fatal error 自退）+ 队列"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R65":
        f[6] = "1"
        f[7] = "DONE"
        f[8] += (
            " 【W934 评估 2026-11-04 09:0x｜纯只读】**上游未再更新**：三路互证 —— `git fetch --force --tags` 后 "
            "`upstream/main` = **ffa80d73**（v0.2.10, 2026-11-02）、`git ls-remote` 绕过本地 ref 得同一 SHA、"
            "最新 tag = v0.2.10 ⇒ 落后 **708** / 领先 37（与 W917 一致）。"
            "**708 条构成**：split/多卡/DFlash2/RCCL **224**（31.6%）、非 Linux 平台（Windows/Metal/SYCL/Arc）**135**、"
            "UI/App/Terminal/Setup/文档 **109**、新架构（gfx11xx/gfx12xx/RDNA/RX9xxx/RTX/sm_/Blackwell/Ada）**44**"
            "（有重叠）；**「gfx906/MI50」在 708 条里出现 0 次**。冲突面：generate.cpp 99、CMakeLists 49、"
            "arch_defaults_test 17、arch_defaults.cpp 11（已核：全是 gfx12/1151/1010/1030）、hpp 5、native_mmvq 4、qsa_select 3。"
            "**逐条核了 7 条候选**：`e1b27d54`（fatal GPU error 自退）**值得**（我们 0 处、上游 4 处，cherry-pick 实测 1 处冲突）；"
            "`9aea047e`（答案晚一个请求）待定；`058f6532`/`9a352550` **只改 src/split**（多卡）排除；"
            "`285fa48b`（lookup_default.hpp）**我们没这个文件**；`5a13c34f`（PLE raise soft limit）**已被 --ulimit memlock=-1 绕过**；"
            "`de830800`（CPU share 默认 1024→3072）**我们已经是 3072**。"
            "**判决：不做整体 rebase** —— 收益 0.2%（1-2/708）、成本是 37 条 × generate.cpp 99 次改动的冲突 + "
            "引擎 0.1.55→0.1.56 全量重建 ⇒ 量级不匹配。只 cherry-pick，已立 R77。"
            "**方法论**：查上游更新必须三路互证（fetch 后的 ref + ls-remote + tag），W917 只看了第一个而远端静默不更新"
        )
        lines[i] = "\t".join(f)
        print("R65 -> DONE")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))

# R77
rows = io.open(p, encoding="utf-8").read().split("\n")
while rows and rows[-1] == "":
    rows.pop()
rows.append("\t".join([
    "B4上游移植", "R77",
    "cherry-pick `e1b27d54`（fatal GPU error 自退）：GPU 出致命错后引擎 `_Exit(3)` + server 503 并自动重启，"
    "而不是带着死上下文继续返回 400；带 10 分钟 3 次的防抖",
    "W934 §2", "count", "1", "0", "OPEN",
    ("**W934 立（2026-11-04 09:2x，零停服）**：全量 rebase 判否后唯一的确定候选。"
     "**现状**：我们树里 `fatal GPU error` / `ERR fatal` 命中 **0**，上游 4 —— 现在若 gfx906 发生 illegal memory access "
     "（这类错误在我们跑实验时出现过），引擎会带着死的 device context 继续跑，之后**每个请求都 400 直到人工重启**。"
     "**改动**：`generate.cpp` +43（`exit_gpu_fatal`/`exit_if_gpu_fatal`，含 `STRATA_INJECT_FATAL=N` 测试钩子）、"
     "`serve/server.py` +46（把 ERR 行判为引擎死亡 → 503 retryable + 标记 ended）、`src/dsv41/ds4_main.cpp` +38、新增测试。"
     "**cherry-pick 实测**（临时 worktree）：**1 处冲突**（generate.cpp），server.py 的 hunk 干净。"
     "**判据**：①编译通过；②`STRATA_INJECT_FATAL=2` 注入后第 2 个请求得 503、引擎重启、后续请求正常；"
     "③不注入时行为与现在逐字节一致（它只在 sticky fatal error 时才触发）。**依赖**：需重建二进制（换对象重链，约 5 分钟），"
     "不改数值 ⇒ 不需要 KL 门"),
    "W934",
]))
rows.append("")
io.open(p, "w", encoding="utf-8").write("\n".join(rows))
print("R77 appended")

# 队列
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 09:2x 修，`W934`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70~~ → ~~R75~~ → ~~R76~~ "
            "→ ~~R65（上游未再更新；708 条里 96% 是 split/新架构/非Linux平台/UI；不整体 rebase）~~ → "
            "**R77**（cherry-pick fatal error 自退） → **R74**（W4A4 精度门） → R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))
print("done")
