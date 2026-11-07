import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
n61 = n60 = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) != 10:
        continue
    if f[1] == "R61":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W923 实测 2026-11-04 01:1x｜4 次重启，生产已恢复】**PMC 在这套自建 gfx906 包里采不到，R61 判工具不可用**。"
                 "attach 路径 W917 已证不可用（需 `ROCP_TOOL_ATTACH=1`），故走重启注入："
                 "`HSA_TOOLS_LIB` + `ROCPROF_COUNTERS=VALUBusy MemUnitStalled FetchSize` + `ROCPROF_COUNTER_COLLECTION=1` + `ROCPROF_OUTPUT_*`（变量名从库 strings 核实）。"
                 "**三次尝试全部静默失败**：①基础 6 个 env ②确认 collection ③加 `ROCPROF_LOG_LEVEL=debug` —— "
                 "每次 health 正常（245/255 s）、请求 http=200（2.9/2.0 s），**输出目录始终为空、日志无任何 profiler 行**。"
                 "**诊断**：进程 env 确实带着 6 项；库 `librocprofiler-sdk-tool.so -> .so.1` 存在；**`ldd` 全部满足、`not found` = 0**；"
                 "**`grep -c HSA_TOOLS_LIB /opt/rocm/bin/rocprofv3` = 0** ⇒ rocprofiler-sdk 7.16 在这套包里不采纳 `HSA_TOOLS_LIB`（静默），"
                 "不是 env 设错。剩余路只剩 `LD_PRELOAD`（会拦截服务全部符号，风险高）或改 `librocprofiler-register` 默认附件（要重建组件）。"
                 "**新纪律**：涉及库注入的验证，先读官方启动脚本（`rocprofv3` 这种 Python 入口）看它实际设什么，"
                 "**不要从 library 的 strings 猜变量名**——strings 只证明变量被读过，不证明注入路径会被激活")
        lines[i] = "\t".join(f); n61 = 1
    elif f[1] == "R60":
        f[6] = "0"; f[7] = "CLOSED"
        f[8] += (" 【W923 判定 2026-11-04 01:1x】**关闭（依据算术预判，非 PMC 实测）**。`W916` 推导：峰值指令率 6.624 T instr/s、"
                 "dot4 峰 26.5 TMAC/s；生产折算 4.55 TMAC/s = 17.2%，但 MMQ 只占 prefill 34.6%（W903）⇒ **MMQ 相位内 ≈13.2 TMAC/s = 峰值 50%**；"
                 "若按 W904 微基准的 0.75 instr/MAC 配比，50%×3 = **150% > 100% 物理不可能** ⇒ 真实配比远优于微基准，"
                 "**VALUBusy 落在 50–65%，已越过 R61 的 40% 门** ⇒ stream-k 解决的『in-flight bytes 不足』不是瓶颈。"
                 "**口径**：这是算术预判不是实测；若将来 PMC 打通（LD_PRELOAD 或修 register 默认附件）须复核，"
                 "判据不变（VALUBusy ≥40% 判死、≤25% 才做）")
        lines[i] = "\t".join(f); n60 = 1
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))
print("R61 DONE_NEG:", n61, " R60 CLOSED:", n60)

p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 00:1x 修，`W923`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → "
       "~~R72 已结（上限 <0.2%，计算阶段判死）~~ → **R61（PMC 定 R60 生死）** → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 01:1x 修，`W923`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → "
       "~~R61 已结（PMC 工具不可用）~~ → ~~R60 已关（算术预判 VALU 50–65%）~~ → **R58**（MMQ vec_dot 三段计数）"
       " → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
if old not in s:
    # 容错：按更宽的模式找
    import re
    m = re.search(r"> \*\*执行顺序（2026-11-04 00:1x 修[^\n]*", s)
    if m:
        s = s.replace(m.group(0), new, 1)
        print("order replaced via regex")
else:
    s = s.replace(old, new, 1)
    print("order replaced")
io.open(p, "w", encoding="utf-8").write(s)
