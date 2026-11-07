# -*- coding: utf-8 -*-
"""追加 [W-Strata-32]：上下文优化（ctx 131072→262144 + kv k8v4）实测与落地。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-32] 上下文优化：**131072 → 262144 翻倍，速度不降反升**（已落地到 serve）

**发现来源**：`--kv k8v4` 的帮助（INT8 K 精确 + 旋转 Q4_0 V，**816 B/cell vs int8 的 1056**）与 `--kv q4_0`（int8 的一半）此前从未试过；模型训练窗口本就是 **262144**，我们只开到 131072。

**一次性 generate 六臂（每臂 ~72 s，`expert cache N slots` 是代价币种）**，脚本 `_ab_ctx166.py`、日志 `_ab_ctx.txt`：

| Arm | 专家槽 | 预填 tok/s |
|---|---|---|
| ctx131 **int8**（原状） | 10797 | 468.5 |
| **ctx262 int8** | **10021** | 466.4 |
| **ctx262 k8v4** | **10327** | 466.0 |
| ctx262 q4_0 | 10636 | 464.9 |
| ctx131 k8v4 | 10949 | 467.8 |
| ctx262 int8 + `--kv-resident 32768` | **11209** | 466.7 |

⇒ **上下文翻倍只吃 776 槽（≈1.76 GiB）**；`--kv k8v4` 在 ctx262 下回收 306 槽、`--kv q4_0` 回收 615 槽、`--kv-resident 32768` 回收 1188 槽（比原状还多 412）。**预填速度在所有臂上都不变（464.9~468.5）**。

**落地（serve，`_apply_ctx262.py`，日志 `_apply_ctx262.txt`）**：配置改为 `--max-context 262144 --kv k8v4`，其余逐字不变；旧配置备份在 `/data/strata-ud-iq4_xs.json.bak-131k-int8`。

| serve 实测 | ctx131 int8（旧） | **ctx262 k8v4（现）** | 差 |
|---|---|---|---|
| prefill 中位 | 438.8 | **457.5**（453.1/457.9/457.5，spread **1.0%**） | **+4.3%** |
| decode 中位 | 42.9 | **45.0**（37.5/45.0/45.0） | **+4.9%** |
| 专家槽 | 10289 | 9758 | −531（−5%） |
| RAM 常驻 | 32.24 GiB | 33.45 GiB | +1.2 GiB |
| VRAM 余 | 576 MiB | 574 MiB | 同 |
| n_ctx | 131072 | **262144**（已从本机 `/v1/models` 确认） | **×2** |

⇒ **槽少了 5% 反而更快**：与 k8v4 的 KV 写流量更小自洽（1056 → 816 B/cell）。
⇒ 代价：RAM 多 1.2 GiB（128 GB 完全够）；解码 spread 16.6%（一次 37.5 的低点），但中位与预填同向。

**给 WorkBuddy 的对应改动**：上下文 `262144`、**输入 229376 + 输出 32768**（= 262144）。清单已更新：`D:\\strata166\\configs\\workbuddy-strata166.md`。

**下次可试（未验证）**：`--kv k8v4 --kv-resident 32768` 组合（一次性测里 `int8+kv-resident` 给出最多槽 11209、预填不变），但 **KV 流到 pinned RAM 在长上下文下的解码时延未测**，不要盲上。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
