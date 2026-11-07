
---

## §6.5 回写 · W1002（2026-11-05 21:5x）—— 方案重新归一

**先认错**：W986–W1001 期间我把执行序一路追加进 `deploy/W986_PLAN_V3.md`
（V3.0→V3.9，共 10 版），而本件 §0.0 写死「**方案只有这一份，别处不自持队列**」。
`tools/plan_lint.py` 判据 E 一直在报「未登记的方案文件：W986_PLAN_V3.md」，
但那一阵没人跑它（rc=1 也没人看见）。⇒ **本节的队列重新成为唯一排序处**；
`W986_PLAN_V3.md` 已标 SUPERSEDED，只作历次修订的证据留档。

### 当前唯一执行序（V3.9 内容，搬回本节）

| 序 | 项 | 判据 / 现状 |
|---|---|---|
| 1 | **R97 混合分派原型** | 按 `expert_bounds` 段行数：小段走 repacked w32、大段留 canonical；六长度档 + 2×CV，prefill@2K ≥5% 才继续 |
| 2 | **R96 gate/up + GLU 融合** | PR #29948 已合并、有跨硬件对照；源码可行性先判，不动权重布局 |
| 3 | **R86 完整移植** | 三条通道状态见 `ci/repack_ab/PORT_STATUS.md`；**当前 NOT_DONE**，R97 加权 ≥5% 才进 |
| 4 | R91 dot8 六阶段 | P1 量化器逐元素一致先决 |
| 5 | R95 小批 GEMM | 2K 的 gate/up 1.91×；J=64 是 K-quant 下限 |
| 6 | R94 质量门 | KL ≤0.0139、top-1 ≥99%（R90 的欠账） |
| 7 | R89 / R46 / R49 / R50 | 移植与候选，并行不占 GPU |

**已结案、不再排队**：R87 q8_1 复用（DONE_NEG，我们早有且 gather 仅 0.2–0.7%）、
R93 chunk 重标（8192/16384/32768 三值齐，维持 16384）、R88 预取（主机缝隙仅 15 ms，证伪）、
`--pcie-frac` 双向与 auto、`--pool-tasks`、会话/检查点缓存、`--mmap-experts`。

### 判据（不变，写死）

- 所有臂 **n≥10**；基线 `--restart-baseline`；**2×CV（当次 run）**；**不显著即回退**；
- prefill 类改动必须看 `--lengths 2000,8000,16000` 三档，任一档掉出 2×CV 即回退；
- 动生产只走 `ci/cfg_apply.py`；重编先读 `ci/build.sh` + r32 cache，验收 = 产物 md5 复现生产；
- **「测完有实际数据才能判断」**：静态分析、代理实验、外网数字都只能预判，不能直接关条目
  （W999 判否被 W1000 撤回就是教训）。

### 交付门（W1002 新增，见 `ci/README.md`）

`pre-commit` / `pre-push` / `downstream-gate.yml` 都会跑 `ci/round_gate.py --ci`；
本机收尾跑 `albus/w1002/round_close.py --report <本轮 reply.md>`（四个 lint 一起过）。
**完整移植状态是机器可读的** `ci/repack_ab/PORT_STATUS.md`，不许靠报告里一句话。
