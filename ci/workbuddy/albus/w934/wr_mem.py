# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 09:2x W934 · R65 结项：上游未再更新，708 条 96% 与我们无关，**不做整体 rebase**，只 cherry-pick 1 条
- **上游三路互证**（W917 只看了第一条而 SSH 远端静默不更新，连错三轮）：`git fetch --force --tags upstream` 后 `upstream/main` = **ffa80d73**（v0.2.10, 11-02）；`git ls-remote upstream HEAD` 绕过本地 ref 得同一 SHA `ffa80d73133ea5c5…`；最新 tag = v0.2.10。⇒ **上游没动，落后 708 / 领先 37**。
- **708 条构成**：split/多卡/DFlash2/RCCL **224**（31.6%）、非 Linux 平台（Windows/Metal/SYCL/Arc）**135**、UI/App/Terminal/Setup/文档 **109**、新架构（gfx11xx/gfx12xx/RDNA/RX9xxx/RTX/sm_/Blackwell/Ada）**44**（有重叠）。**「gfx906/MI50」出现 0 次** —— 上游的 AMD 面 = RDNA。
- **冲突面**：generate.cpp **99**、CMakeLists **49**、arch_defaults_test 17、arch_defaults.cpp 11（已核全是 gfx12/1151/1010/1030）、hpp 5、native_mmvq 4、qsa_select 3。
- **7 条候选逐条判**：①`e1b27d54`（fatal GPU error 自退）**值得** —— 我们 0 处、上游 4 处，现状是 GPU 致命错后引擎带死上下文继续、之后每请求 400 直到人工重启；cherry-pick 实测 **1 处冲突**（generate.cpp），server.py 干净。②`9aea047e`（答案晚一个请求）待定。③`058f6532`/`9a352550` **只改 src/split**（多卡）排除。④`285fa48b`（lookup_default.hpp）**我们树里没这文件**。⑤`5a13c34f`（PLE raise soft limit）**已被 `--ulimit memlock=-1` 绕过**。⑥`de830800`（CPU share 默认 1024→3072）**我们 config 里就是 3072** —— 当时的选择与上游新默认一致。
- **判决：不做整体 rebase** —— 收益 0.2%（1–2/708），成本是 37 条 × generate.cpp 99 次改动的冲突 + **引擎 0.1.55→0.1.56 全量重建 + 镜像重打包**，量级不匹配。已立 **R77**（只 cherry-pick e1b27d54，判据：编译 + `STRATA_INJECT_FATAL=2` 注入后第 2 请求得 503 且引擎重启 + 不注入时逐字节一致）。
- **生产零改动**：无重启、无编译；临时 worktree `/tmp/w934` 已删。
- **队列**：`~~…~~ → ~~R65~~ → **R77** → **R74** → R49 → R50 → R30′`。进度 **161 条 / 100 已结 = 62.1%**，主线 **133 / 100 = 75.2%**。
- 产物：`deploy/W934_R65_REBASE_VERDICT.md`；`PROGRESS.tsv` R65(DONE) + R77(OPEN)；`W832` 队列。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
