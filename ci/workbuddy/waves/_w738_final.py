# -*- coding: utf-8 -*-
"""W709 步23：净化核验交付件，并追加 W709c 记忆"""
import hashlib, io, os

BAN = ['\u21d2', '\u2192', '\u2014', '\u2013', '\u2026', '\u2265', '\u2264', '\u2260', '\u2212', '\u00d7']

for p in [r'D:/strata166/W709_PARAM_OPTIMUM.md']:
    t = io.open(p, encoding='utf-8').read()
    n0 = len(t)
    for a, b in [('\u21d2', '=>'), ('\u2192', '->'), ('\u2014', '--'), ('\u2013', '-'), ('\u2026', '...'),
                 ('\u2265', '>='), ('\u2264', '<='), ('\u2260', '!='), ('\u2212', '-'), ('\u00d7', 'x')]:
        t = t.replace(a, b)
    bb = t.encode('utf-8')
    open(p, 'wb').write(bb)
    tt = bb.decode('utf-8')
    print('%-34s %6d B  md5=%s  CR=%d  lines=%d  BAN=%s' % (
        os.path.basename(p), len(bb), hashlib.md5(bb).hexdigest(), bb.count(b'\r'),
        len(tt.splitlines()), {hex(ord(k)): tt.count(k) for k in BAN if tt.count(k)} or 'CLEAN'))
    for k in ['--prompt-cache-every 8192', '-74.6%', '-74.8%', 'reused=8192', 'PASS=15', 'd2b10f0c4e8293ba010614c7acc70bea']:
        assert k in tt, k
    print('  关键串全在位')

SEG = """

## W709c ---- 多轮复用：默认值漏掉的一段（本波最值钱的发现）

### 三条机制判据（实测拼出来的）
1. `--prompt-cache-every` **默认 16384** => 只有 prompt > 16384 token 才有 fresh-token checkpoint。
2. **可复用前缀必须与 prefill chunk（8192）对齐**：
   - 18,083-token prompt（默认 16384）=> `reused=16384`，温 TTFT 40.2s -> **5.8s**（这一档**本来就是工作的**）；
   - `--prompt-cache-every 4096` => **`reused=0`**（4096 不与 8192 对齐）=> 无效；
   - `--prompt-cache-every 8192` => `reused=8192` => **有效**。
3. `--prompt-cache-tail` 与 `--prompt-cache-every` **重复**：它要 "an existing chunk boundary"，
   而默认 16384 已在同一位置放 checkpoint => 无增量（实测温 TTFT 5.787 vs 5.828、reused 两臂同为 16384）。

### 采纳 P34 `--prompt-cache-every 8192`（盲区 = 8192~16384 这一段）
- 交错 A/B（~10,000-token prompt，各 2 轮）：默认 -> 温 **23.072 / 23.074**、`reused=0`；
  8192 -> 温 **5.861 / 5.877**、`reused=8192` => **-74.6%**。
- **实机验收**（部署后，引擎日志同口径自证）：
  `prompt 9982 = 0 reused + 9982 read in 23354 ms` vs `prompt 9993 = 8192 reused + 1801 read in 5801 ms`
  => **冷 23.48s -> 温 5.91s = -74.8%**，`2 checkpoints`。
- 代价：checkpoint 计入 `--prompt-cache N`(=6) 上限（~118 MB/个）=> 上限约 0.7 GB RAM；
  实测 VRAM +47 MB 级、RAM available 82 GB、解码专家缓存命中 95.1% => **无可见代价**。
- `P21 --prompt-cache-tail` 与 `P22 --prefill auto:16384` 均转 **REJECTED**。

### 终态
- register：**ADOPTED 16 / REJECTED 12 / CANDIDATE 7**；
  LIVE config md5 **`d2b10f0c4e8293ba010614c7acc70bea`**；复验 **PASS=15 / FAIL=0 / SKIP=1**。
- 交付件：`D:/strata166/W709_PARAM_OPTIMUM.md`（含判据定义 / 全部 sweep 原始读数 / 采纳与否决 / 未测清单 / 方法论教训）。

### 教训（与 W709a/W709b 并列，已写进交付件 §7）
**判"某 flag 无效"前必须先自证"测的场景落在该机制的有效域内"** —— 本波同一个坑踩了两次
（6.8k prompt 测需要 chunk 边界的 `--prompt-cache-tail`；4k interval 因**不对齐**而"无效"）。
"""
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
b = SEG.encode('utf-8')
assert b.count(b'\r') == 0
with open(P, 'ab') as f:
    f.write(b)
t = io.open(P, encoding='utf-8').read()
print()
print('memory %d B CR=%d  has W709c=%s' % (os.path.getsize(P), open(P, 'rb').read().count(b'\r'), 'W709c' in t))
