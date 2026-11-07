# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：第四轮 3/4 挂掉的根因（我自己的脚本 bug）+ 修正"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-15] 第四轮 A/B **4 个 arm 挂了 3 个** —— 全是我自己的脚本 bug，已定式修正

### 一、唯一有效的一条数据
| Arm | 结果 |
|---|---|
| `--prefill 16384` | **439.4 tok/s**（vs 轮内基线 433.2~436.6，**+1.5% = 噪声**） |
| `--ple-inflight 2048` | ❌ 未启动 |
| `--pcie-frac 0.0` | ❌ 未启动 |
| restore | ❌ 未启动（**服务一度处于停止状态**） |
> ⚠️ 我先前把 439.4 归给了 `ple-inflight`，**是错的** —— 那是 `--prefill 16384` 那条。已更正。
> 官方结论也印证：静态 16K chunk **无端到端收益**（`AMD_HIP_PERFORMANCE.md` "rejected experiments"）。

### 二、[!] 三个参数面硬约束（都是引擎明确校验的，别再踩）
1. **`--ple-inflight` 合法范围 [1, 1024]**（`generate.cpp:1740-1744`，默认 256）
   ⇒ 我填 2048 → 引擎直接 `invalid --ple-io/--ple-row-cache/--ple-inflight/--ple-delay-us` + return 2 拒启动
2. **`--prefill` 是 serve 模式硬要求**：缺失时引擎在**载完模型后**才报
   `strata serve: needs --spec T, --mtp DIR and --prefill CHUNK` 然后退出（**白等 4 分钟**）
   —— 与 `--mtp` 同一条规则。`--prefill auto` 合法，等于默认。
3. **`--pcie-frac` 只吃浮点**，写 `auto` 会被 `atof` 解析成 0.0（静默错），要用"省略该参数"来表达默认
- 同类已知约束：`--kv` 只接受 fp16|int8|q4_0|k8v4；`--ple-io` 只接受 direct|mmap|ram（Windows 上 ram 会被拒）

### 三、[!] 通用 flag 改写器的定式（教训）
我写了个"删掉某 flag 再重加"的通用函数，用 `DEFAULT` 表示"保持引擎默认（即省略该参数）"。
**这个抽象对"可选参数"成立，对"必填参数"是致命的**：`--prefill` 被省略后引擎拒启，而且报错发生在
模型全部加载完之后 —— 看起来像"启动了但没 ready"，与真故障难区分。
⇒ **定式：改写配置后必须跑前置断言（fail-closed）**，至少检查
(a) 必填 flag 仍在位且取值非空/合法 (b) 数值参数在引擎声明的区间内。
本轮已把断言加进 `setarg3.py`（`assert '--prefill' in a`、`assert 1<=ple_inflight<=1024`），
断言不过就**跳过该 arm 而不是带着坏配置去启动**。
⇒ 另一条通用教训：**"参数被静默吞掉"与"服务真的起不来"在现象上无法区分**，
所以拒启动类的错误必须**前置**（配置阶段校验），不能等引擎来说。

### 四、修正版第四轮（正在跑，5 个 arm，全部带断言）
`baseline` → `--ple-inflight 1024`（合法上限，4× 默认）→ `--pcie-frac 0.0` → **`--adapt-every 0`** → `restore`
其中 `--adapt-every 0`（关掉请求期的自适应换入换出）是**最高预期**：官方测量口径里特意设了它。
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('appended, size', os.path.getsize(p), 'B')
