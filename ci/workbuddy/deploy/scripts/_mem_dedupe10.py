# -*- coding: utf-8 -*-
"""去重 W-Strata-09，并追加 W-Strata-10（131072 压测读数）"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
t = open(p, encoding='utf-8').read()

MARK = '## [W-Strata-09]'
first = t.find(MARK)
assert first >= 0, 'W-Strata-09 不存在'
second = t.find(MARK, first + 1)
if second >= 0:
    t = t[:second].rstrip() + '\n'
    print('去重：删掉了第 2 份 W-Strata-09（%d 字符）' % (len(t) - second))
else:
    print('无重复')

TXT = """

## [W-Strata-10] 166 提到 **131072 上下文**：代价极小，长预填线性无衰减

### 一、配置变更
`--max-context 8192 → 131072`（其余不动：`--kv int8 --spec 4 --spec-min-p 0.5 --resident-budget-gib 76 --expert-cache auto --prefill auto`）。
依据：官方 UD 示例的 8192 是给 **12 GB 卡**的默认；166 有 32 GB 显存、KV int8 只 1056 B/cell ⇒ 长上下文几乎不占显存。
模型训练窗 262144，**131072 无需 rope 外推**。`/v1/models` 已回 `"n_ctx": 131072`。
备份：`/data/strata-ud-q4_k_xl-8k.json.bak`。

### 二、代价（实测）
| | ctx 8192 | ctx 131072 |
|---|---|---|
| GPU 专家缓存 | 8495 slots / 24.79 GiB | **7875 slots / 22.99 GiB** |
| RAM 页锁定常驻 | 46.94 GiB | **48.74 GiB** |
| 合计 | 24576 = 全部（零读盘） | **24576 = 全部（零读盘）** |
| prompt chunk | 8192 | 8192（不变） |
⇒ **只花 1.8 GiB 显存换 16 倍上下文**，专家仍全常驻。

### 三、读数（ctx 131072，连跑 4 轮）
| 轮次 | prompt tok | 预填 t/s | 解码 t/s | 备注 |
|---|---|---|---|---|
| R6 短 prompt 冷 | 290 | 69.2 | 25.5 | 重启后首请求，缓存未热 |
| R7 长冷 | 21589 | **467.1** | 30.3 | 冷预填 46.0 s |
| R8 同 prompt 复跑 | 21589 | **69652**（21584/21589 复用） | 34.4 | **TTFT 0.31 s** |
| R9 巨长冷 | **71787** | **468.5** | 29.0 | 冷预填 **152.6 s**，5 checkpoints |

- **预填速率在 21.6k 与 71.8k 上几乎同值（467 vs 468）⇒ 线性、无衰减**，这是这一波最有价值的结论
- 即 131072 满窗冷预填约 **280 s**；配合前缀复用，实际多轮对话只付增量
- 解码冷启动首请求明显低（25~27），热了以后 34~42 ⇒ **别拿首请求当稳态读数**
- 解码专家缓存命中 87.7%→91.5%→92.8%（随请求累积升温）；`--suffix-draft` 偶发 15/15 全中

### 四、结论：166 这套已经是"可用生产态"
- 端点 `http://172.17.0.6:8090/v1`，模型 `qwen3.8-flash-next-ud-q4_k_xl`（UD-Q4_K_XL 111 GB / 4-bit）
- 全 24576 专家常驻（GPU 22.99 GiB + RAM 48.74 GiB），稳态零读盘，VRAM 33.91/34.34 GB
- 相对本机 9070XT（IQ2_XS）：**解码快约 1.2~1.25×、位宽高一档、MTP 真有效**；**预填慢约 1.5×**（K-quant prompt kernel CUDA-only）

### 五、技能已更新
`~/.workbuddy/skills/flashnext-engine-selection/SKILL.md` 新增 **§7 gfx906 单卡路线**（镜像配方、hip_compat 必打补丁、
MTP 两个坑、pkill/僵尸两条自伤、资源耗时、全部实测读数），供下次复现。
"""

open(p, 'w', encoding='utf-8').write(t.rstrip() + '\n' + TXT)
print('写入完成，size', os.path.getsize(p), 'B')
