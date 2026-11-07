import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 01:1x（11-04）W923 · R72 计算判死 + R61 PMC 工具不可用 + R60 关闭
- **R72 = DONE_NEG（计算阶段判死，省下约 20 分钟）**：前提被证伪——R66 省下的 1.03 GiB 是 **borrow 减少（prompt 期间临时占用）**，不是常驻显存。实测每槽 **2.990 MiB**（21.79 GiB/7463）。reserve 832→700/600/500/400/300 只多 **45/78/112/145/178 槽（+0.6%~+2.4%）**，且越低越逼近 256 MiB 红线。decode 命中率实测 91.0–95.7%（稳态 ~93%），容量 +1.9% ⇒ 命中率 **+0.13pp** ⇒ decode **<0.2%**，远低于 2×CV ⇒ 不做。
- **一个易误判的历史点**：日志里有 218 次 `expert cache 9901 slots, 22.31 GiB`，但那是 **旧 pack `huihui-ud-iq4_xs`（每槽 2.31 MiB）**，与当前 `ud-q4_k_xl`（每槽 2.99 MiB）**不可比**，不能当成"曾经有过 9901 槽"的目标。
- **R61 = DONE_NEG（工具不可用，4 次重启）**：attach 路径 W917 已证不可用（需 `ROCP_TOOL_ATTACH=1`）；走重启注入 `HSA_TOOLS_LIB` + `ROCPROF_COUNTERS=VALUBusy MemUnitStalled FetchSize` + `ROCPROF_COUNTER_COLLECTION=1` + `ROCPROF_OUTPUT_*`（变量名从库 strings 核实）。**三次尝试全部静默失败**（第三次加了 `ROCPROF_LOG_LEVEL=debug` 仍无一行），health 正常、请求 http=200。**诊断**：进程 env 带着 6 项、库存在、**`ldd` 无 `not found`**、而 **`grep -c HSA_TOOLS_LIB /opt/rocm/bin/rocprofv3` = 0** ⇒ rocprofiler-sdk 7.16 在这套自建 gfx906 包里**不采纳 `HSA_TOOLS_LIB`**（静默）。剩余路只剩 `LD_PRELOAD`（拦全部符号，风险高）或改 `librocprofiler-register` 默认附件（重建组件）。
- **R60 = CLOSED（依据算术预判，非实测）**：MMQ 相位内 ≈13.2 TMAC/s = 峰值 50%；若按 W904 微基准 0.75 instr/MAC 配比，50%×3 = 150% > 100% 物理不可能 ⇒ 真实配比远优 ⇒ **VALUBusy 50–65%，已过 40% 门** ⇒ stream-k 解决的"in-flight bytes 不足"不是瓶颈。口径必须写明是预判；PMC 打通后复核，判据不变。
- **新纪律（W923 §5）**：涉及"库注入"的验证，**先读官方启动脚本**（`rocprofv3` 这种 Python 入口）看它实际设什么，**不要从 library 的 strings 猜变量名**——strings 只证明"变量被读过"，不证明"这条注入路径会被激活"。W917 那条"≤1 分钟最小验证"对注入类无效（HSA_TOOLS_LIB 的最小验证必须是一次完整重启 4–5 分钟）。
- **生产**：4 次重启（2 注入 + 2 恢复），累计停机 ~17 分钟；已恢复 config `51ef8837`（env 9、profiler 0）、engine `a97f4479`、`expert cache 7463 slots`/`borrows 1578`/`VRAM free 920`、restarts=0。
- 进度 **90/156 = 57.7%**，主线 **90/128 = 70.3%**。队列 `~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → **R58** → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3`。
- 产物：`deploy/W923_R61_PMC_FAILED.md`；`PROGRESS.tsv` R61(DONE_NEG)+R60(CLOSED)+R72(DONE_NEG)；`W832` 队列。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
