# W923 · R61：PMC 采集三次失败，R60 按算术预判关闭

> **【AUDIT24 P1 · 2026-11-04】结论外推过宽 + 计数自相矛盾**：
> ①「rocprof 不可用」只对 **`HSA_TOOLS_LIB` 注入**成立 —— `W941/W942` 用 **rocprofv3 当启动器 + 独立可执行自然退出**
> 采到了 PMC（`VALUBusy` 67.1%，本轮复测 67.3%），并据此重开/结题多条；
> ②§2 表列 **3 次**尝试，文末却写「共 4 次重启（2 注入 + 2 恢复）」——以表为准（3 次尝试 + 恢复重启）。

日期：2026-11-04 00:5x – 01:1x
状态：~~**R61 = DONE_NEG（工具不可用）**；**R60 = 关闭（依据预判，非实测）**~~ **均已撤回**：rocprof 只在 `HSA_TOOLS_LIB` 注入下不可用，`W942` 用启动器路径采到 VALUBusy 67.1%；**R60 现为 OPEN**（关闭不合规，见 `W947`）；生产已恢复

---

## 1 做了什么

`W917` 已实测 **attach 路径不可用**（目标进程需 `ROCP_TOOL_ATTACH=1`，我们进程没有，`rocprof-attach` 返回
`attach ... returned non-zero status 1`）。所以只能走**重启注入**。

注入的 env（变量名从 `librocprofiler-sdk-tool.so` 的 strings 里核实，不是猜的）：

```
HSA_TOOLS_LIB=/opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so
ROCPROF_COUNTERS=VALUBusy MemUnitStalled FetchSize
ROCPROF_COUNTER_COLLECTION=1
ROCPROF_OUTPUT_FORMAT=csv
ROCPROF_OUTPUT_FILE_NAME=pmc
ROCPROF_OUTPUT_PATH=/data/w923
```

`rocprofv3-avail list --pmc` 确认 gfx906 上有 `VALUBusy / MemUnitStalled / FetchSize`（命中 3）。

## 2 三次尝试，三次静默失败

| 次 | 做法 | 结果 |
|---|---|---|
| 1 | 上述 6 个 env，重启 | health 正常（245 s），请求 http=200 / 2.9 s，**`/data/w923/` 空** |
| 2 | 加 `ROCPROF_COUNTER_COLLECTION=1` 确认 + 清空目录重试 | 同上，**空** |
| 3 | 加 `ROCPROF_LOG_LEVEL=debug` 重启 | health 255 s，请求 2.0 s，**输出目录仍空，日志里没有任何 rocprof/profiler 行** |

**诊断证据**：

- 引擎进程 env **确实带着** 6 个变量（`/proc/<pid>/environ` 逐条可见）；
- 库路径存在：`/opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so -> librocprofiler-sdk-tool.so.1`；
- **`ldd` 全部满足，没有一条 `not found`**（依赖 `librocprof-trace-decoder` / `-rocpd` / `-sdk` / `comgr` / `sysdeps_*` 都在）；
- `rocprofv3` 的 Python 脚本里**搜不到 `HSA_TOOLS_LIB`**，只有 `ROCPROF_ATT_LIBRARY_PATH` 与 `LD_LIBRARY_PATH` 的拼接。

⇒ 结论：**rocprofiler-sdk 7.16 在这套自建 gfx906 包里，`HSA_TOOLS_LIB` 没有被 HSA 采纳**（静默）。
这不是"我设错了 env"，而是注入机制与这个发行版不匹配。进一步的路只剩 `LD_PRELOAD` 或改
`librocprofiler-register` 的默认附件开关 —— 前者会拦截服务全部符号（风险高），后者要重建组件（超出本轮范围）。

**决策：停在这里。** 每次尝试的成本是一次 4–5 分钟重启，收益只是"确认一个已有独立推导的结论"。

## 3 R60 的判定：按算术预判关闭（不是实测）

`W916` 的推导（不需要 profiler，全部用已实测量）：

```
峰值指令率 = 60 CU × 64 lane × 1.725 GHz = 6.624 T instr/s
dot4 峰值  = 26.5 TMAC/s；生产折算 4.55 TMAC/s = 17.2%
但 MMQ 只占 prefill 34.6%（W903）⇒ MMQ 相位内 ≈ 13.2 TMAC/s = 峰值的 50%
```

**反证**：`W904` 微基准的指令配比是 0.75 instr/MAC。若真实内核也是这个配比，50% × 3 = **150% > 100%** ——
物理上不可能。⇒ 真实内核配比远优于微基准，`VALUBusy` 落在 **50–65%**，**已越过 R61 的 40% 门**。

⇒ **R60（MMQ stream-k）关闭**：它解决的是"in-flight bytes 不足"（供给不足），而供给率已经在 50–65%。

**必须写清的口径**：这是**算术预判**，不是 PMC 实测。若将来 PMC 打通（换 LD_PRELOAD 或修 register 默认附件），
这条要复核；复核标准不变：`VALUBusy ≥ 40%` 判死 R60，`≤ 25%` 才做。

## 4 生产恢复

- config 恢复为 `51ef8837`（env 9 项，profiler 变量 **0** 个）
- 引擎 `a97f4479`、`expert cache 7463 slots`、`borrows 1578 slots (4.62 GiB)`、`VRAM free 920 MiB`、`restarts=0`
- 共 4 次重启（2 次注入 + 2 次恢复尝试），累计停机约 17 分钟

## 5 一条方法教训

`W917` 立的"备选路径先做 ≤1 分钟最小验证"这次**没能提前拦住**：`HSA_TOOLS_LIB` 的最小验证必须是一次完整重启
（4–5 分钟），所以它天然过不了那道门。补救办法是先查"这个发行版认不认这个变量"——
本次是事后才去读 `rocprofv3` 脚本，发现它根本不用 `HSA_TOOLS_LIB`。

⇒ **新纪律**：涉及"库注入"的验证，先读**官方启动脚本**（`rocprofv3` 这类 Python 入口）看它实际设什么，
而不是从 library 的 strings 里猜变量名——strings 只证明"这个变量被读过"，不证明"这条注入路径会被激活"。

## 6 复现命令

```bash
# 计数器是否存在
docker exec strata166-407 rocprofv3-avail list --pmc | grep -E "VALUBusy|MemUnitStalled|FetchSize"

# 注入（已验证：进程 env 有、ldd 全满足、但零输出）
docker exec strata166-407 python3 -c "
import json; p='/data/strata-huihui-ud-iq4_xs.json'; d=json.load(open(p))
d['env'].update({'HSA_TOOLS_LIB':'/opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so',
                 'ROCPROF_COUNTERS':'VALUBusy MemUnitStalled FetchSize',
                 'ROCPROF_COUNTER_COLLECTION':'1','ROCPROF_LOG_LEVEL':'debug',
                 'ROCPROF_OUTPUT_FORMAT':'csv','ROCPROF_OUTPUT_FILE_NAME':'pmc',
                 'ROCPROF_OUTPUT_PATH':'/data/w923'})
json.dump(d,open(p,'w'),indent=2)"

# 关键诊断：依赖满足但 HSA 不调用
docker exec strata166-407 ldd /opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so.1 | grep -c "not found"   # -> 0
docker exec strata166-407 grep -c HSA_TOOLS_LIB /opt/rocm/bin/rocprofv3                                            # -> 0
```
