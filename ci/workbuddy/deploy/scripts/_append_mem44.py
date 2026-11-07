# -*- coding: utf-8 -*-
"""向 2026-10-07.md 追加 [W-Strata-23]：0.1.40.1 首次构建失败的根因与修法。"""
import os, sys, io
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-23] 0.1.40.1 首次构建失败 —— 根因是**复核 grep 的路径少了一层 `src/`**（我的错，非上游问题）

**现象**：`docker build` 第 8 步（打补丁 + grep 复核）以 `exit code 2` 失败，且日志里**看不到脚本自身输出**
（被我的轮询 `tail -25` 挤掉 —— 定式：轮询要留全量日志，别只 tail）。

**取证**：本机先复现（解 zip + 跑同一份 `patch_gfx906.py --root <tree>`）→ **rc=0，4 条 grep 全命中 1 次**。
⇒ 排除脚本，锁定容器环境。再用 `docker build --progress=plain` 重放（前 11 步走缓存，只重跑第 12 步），拿到原文：

```
#12 [patch] src/kernels/cuda/fused_gr.cu :: ... 已改（96423 -> 96502 chars）   ← 补丁脚本改的是 /src/src/kernels/...
#12 grep: /src/kernels/cuda/fused_gr.cu: No such file or directory            ← 复核查的是 /src/kernels/...
```

**根因**：仓库根 == `/src`（Dockerfile `cp -a "$inner"/. /src/`），而 Strata 仓库内部路径**本身带 `src/` 前缀**。
- 补丁脚本 `ROOT=/src` + 仓库相对路径 `src/kernels/cuda/fused_gr.cu` ⇒ `/src/src/kernels/...` **正确**
- 我 Dockerfile 里的复核 grep 写成了 `/src/kernels/...` ⇒ **不存在** ⇒ grep 返回 2（grep 找不到文件是 2，不是 1）
- 4 条里只有 `include/strata/platform/hip_compat/strata_hip.h` 恰好对（该路径仓库内**不带** src/），所以只错 3 条

**修法**：3 条 grep 改为 `/src/src/kernels/cuda/fused_gr.cu`、`/src/src/core/mtp.cpp`、`/src/src/core/vmm.cpp`；
并在 Dockerfile 里加了防回归注释。构建改成 `--progress=plain` 落全量日志。

**[!] 三条可复用定式**：
1. **Docker 里跑源码树，先确认「仓库根挂在哪」** —— 用 `/src` 当根时，仓库内部 `src/` 会变成 `/src/src/`。复核路径必须按「挂载点 + 仓库相对路径」拼，不能凭印象。
2. **grep 的退出码要分清**：0=命中、1=没命中、**2=文件/路径错误**。看到 2 别往"内容不匹配"方向查。
3. **`set -eux` 链式命令里，任何一条非零就整体中止** —— 补丁本身是成功的（日志能看到 `PATCH_V2_OK`），失败的是紧随其后的**校验**。设计上这是好事（fail-closed 生效），但排查时先看是哪一条断的。

**成本**：一次完整构建的前 11 步（含 apt 装工具链 ~9 分钟）白跑；修好后走缓存，只需重跑第 12 步起。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
