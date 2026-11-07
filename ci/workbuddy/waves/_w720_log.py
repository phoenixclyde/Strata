# -*- coding: utf-8 -*-
import hashlib
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
TXT = """

## W708c ---- 166 Strata 参数面审计（机主问「你现在已经是最优参数配置了吗？该配的都配了？」）

### 结论：不是最优，仍有该配没配
- 判据：源码 `getenv("STRATA_*")` 全扫 = **280 个**（310 个源文件）；`AMD_HIP.md` 28 个；`DETAILS.md` 47 个；
  引擎 `--help` 全文落 `D:/strata166/logs/_help_402.txt`。绝大多数（多卡/NVIDIA/Intel Arc/Windows/调试）无关。
- **已配 12 项 + 3 项自动**（逐条有当前启动块原文）：`k8v4`（816 B/cell）、`262144`、`spec 4/min-p 0.5`、
  `expert-cache auto -> 9758 槽/21.98 GiB`、`expert-profile` 24576 pairs、`resident-budget 76 -> resident RAM mode
  33.45 GiB page-locked`、`prefill auto -> chunk 8192`、`ple-io direct`；自动：PCIe 13.2 GB/s -> `pcie_frac 0.36`、
  21 pool workers、1/2/3/4/6-token 图全捕获。
- **未配候选（按收益 x 可测性）**：(1) **`--expert-profile-save`**（每次重启丢弃自适应，help L261-264）；
  (2) **`--prefill auto:16384`/`auto:32768`**（help L235-237；**预填臂内极差仅 1.4% ⇒ 可测**）；
  (3) **`--calibrate` 定 `--spec-min-p`**（help L219-220，0.5 只是 setup 默认值）；
  (4) **`STRATA_PREFILL_CPU_SHARE=auto`**（<1024 prompt 快 19~35%，2K+ 不变）；
  (5) `--prompt-cache-tail`；(6) `pin=N`（长文档数量级）；(7) `STRATA_GR_SPLIT=1`（~3%/window，但落在解码极差下）；
  (8) `STRATA_SPEC_GUMBEL=1`；均见 `D:/strata166/W708c_PARAM_AUDIT.md`。
- **防误配**：`--expert-cache-per-layer` 看着诱人（help 说默认到达顺序只有 2.97%），但**我们已是 PROFILE 策略、
  解码命中 94.6~96.4%**，远好于该文档数字 ⇒ 不动。

### 顺带补到一条直证（上一轮审计判"证据不足"的那句）
当前启动块原文：`profile ... 24576 ranked pairs` / `expert cache 9758 slots` /
`RAM budget 76.00 GiB: 14818 of the 33.45 GiB of experts the GPU cache does not hold` /
`resident RAM mode: 33.45 GiB of experts in RAM (page-locked), 9758 in the GPU cache; adaptive swaps exchange them
with the GPU cache (no file reads)` => **9758 + 14818 = 24576 = 全量** ⇒ "全部专家常驻"**成立且有算式级直证**。
审计当时判无证据，是**我引用不全**（我引的 `resident RAM: 33.45 GiB` 那行跨多个启动块反复出现）。
**教训：引用启动期读数必须锚到"最后一次 `engine started` 之后的块"。**
- `W708_STRATA402_BENCH.md` 已回写（17,478 B / `47369d18…`，§3 与 §8 第 6 条）。

### 产物
- `D:/strata166/W708c_PARAM_AUDIT.md`（7,149 B / `5ad8b032…` / CR=0 / BAN 空）
- `D:/strata166/logs/_cfg_402.txt`（28,671 B：容器 env / 配置 JSON / 当前启动块 / 完整 help / docs 开关 / /src/data 可写）
- `D:/workbuddy/_z_rk81/_strata_envs.json`（280 个环境开关 + file:line）
"""
b = TXT.encode('utf-8')
open(P, 'ab').write(b)
bb = open(P, 'rb').read()
print('appended %d B -> total %d B  CR=%d  md5=%s' % (len(b), len(bb), bb.count(b'\r'), hashlib.md5(bb).hexdigest()))
