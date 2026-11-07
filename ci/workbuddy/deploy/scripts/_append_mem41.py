# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：PLE I/O 三档 A/B 结果（假设被证伪）+ 预填分解行的位置"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-13] **PLE 假设被证伪**：`--ple-io ram` 反而慢 48%；`mmap` 只是噪声级

### 一、同轮四档实测（18,074-token 冷 prompt，每档重启后测）
| Arm | `--ple-io` | 引擎日志读数 | ms/token | 启动耗时 | 备注 |
|---|---|---|---|---|---|
| ① direct（轮首） | direct（默认） | **397.3 tok/s** | 2.66 | 200 s | O_DIRECT，表不进 RAM/页缓存 |
| ② mmap | mmap | **416.3 tok/s** | 2.58 | 220 s | 只比 ① 快 4.8%，同轮噪声量级 |
| ③ **ram** | ram | **224.2 tok/s** | **4.61** | **400 s** | **慢 45~48%**，且要多花 ~160 s 锁 26.8 GB |
| ④ direct（轮首复原） | direct | **433.2 tok/s** | 2.46 | 300 s | 同轮对照 |

**结论（与我上一条的预判相反，如实记）**：
1. **`--ple-io ram` 明显更差** ⇒ 预填的每-token 常数开销**不是 SSD 读带宽/延迟**，
   而是"**进 26.8 GB 映射逐个缺页**"这套机制本身（TLB/缺页路径的开销），**数据在不在内存里都躲不掉**
2. `mmap` 的中性结果同向印证：换成缓冲缺页也只换来 4.8%
3. **跨轮基线漂移实测 9%**（轮首 direct 397.3 / 上轮同档 436.6 / 433.3；轮内复跑 433.2）
   ⇒ **重启型 A/B 只在同轮内可比**；每轮必须自带一次基线复核（我脚本里第 ④ 档就是干这个的）
4. `ram` 档还把 `Mem used` 推到 84 GB、available 掉到 41 GB，属于额外风险，**不要用**

### 二、预填的 per-stage 分解在哪（本轮查清）
- `generate.cpp:7570-7574` 里引擎本来就会打一行完整分解：
  `strata generate: prefill N tokens in C chunks, X ms (Y tok/s); experts streamed S (D by DMA, host H ms), resident R; PLE P ms`
  —— 对应 `PrefillStats{tokens, chunks, ms_total, experts_streamed, experts_dma, ms_experts_host, experts_resident, ms_ple}`
- **但它在 `--serve` 下不打**：实测全部日志里 "chunks" 出现 **0 次**
  ⇒ 想要这行必须走**一次性 `generate` 模式**（需 `--tokens` / `--tokens-file` 的 token id 列表，
  得先用容器里的 tokenizer 把测试文本编码出来）
- `--stats` 的另一半（`generate.cpp:8263` 的那处 `if (o.stats)`）打的是**解码的 ms/token 六项**：
  `ms_ple / ms_embed / ms_layers / ms_head / ms_readback / ms_sample` —— 注释明确说这六项"fix 各不相同"，
  是定位解码瓶颈的正解

### 三、方法学（本轮新增）
- **"同轮对照"是重启型 A/B 的必要条件**，不是可选项（实测跨轮漂移 9% > 多数待测效应）
- 怀疑某个机制时，**先查它有没有现成的 breakdown 输出**（本轮就是靠翻 `PrefillStats` 找到的），
  比继续猜快得多
- 假设被证伪也要立刻回写：我上一条把 PLE IO 模式列为"最大一招"，实测证明是错的，必须改写而不是留着
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('appended, size', os.path.getsize(p), 'B')
