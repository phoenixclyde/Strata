"""W1035 第 24 段：窗口 A 结果（含失败原因）+ 候选③ 结构性否掉 + 候选① 成为领先假说。

同时记一条操作教训：引擎 stderr 不进 docker logs，别再用 fprintf(stderr) 类的开关做窗口。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035u"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 窗口 A（`STRATA_MMQ_DEBUG_J=1`）——两次都空手，但把候选③否掉了】**："
          "两次窗口（485 tok / 2050+4046 tok）`pick_J` 行数都是 **0**；**不是 env 没生效**——"
          "容器内 `/proc/20/environ` 核到 config 的 9 个 `STRATA_*` 全在（env 由 `serve/server.py` 从 config JSON 注入），"
          "真因是**引擎 stderr 不进 `docker logs`**（`pick_J` 走 `fprintf(stderr)`，日志里只有 stdout 的 expert-cache 行）。"
          "⇒ **操作教训：以后不能用 stderr 型开关做窗口判据**。"
          "**绕开后读源码得到结构性判决**：`moe_mmq.cu:504` 的 `Context::run()` **每次调用只 `pick_J` 一次、只发一个 kernel**"
          "（`mul_mat_q_case<type>`），launch 数 = MoE 分组数（按层×组 ≈ 96 量级），"
          "665 ms ÷ 96 ≈ **6.9 ms/launch**，比 kernel launch 开销（µs 级）高三个数量级 ⇒ **候选③（调度/建表）被否**。"
          "剩下 **① 权重搬运** 为领先假说：`p.tab`/gather 路径每次 prefill 把专家拼进连续缓冲，成本 ∝ 字节、与 token 数无关，"
          "正好解释「固定项」；而 3.49 GiB ÷ 665 ms = **有效 5.6 GB/s**，对 PCIe 4.0 x16（应 ~20 GB/s）偏低 ⇒ "
          "**优化目标是拷贝路径（pinned / 异步 / 合并），不是 GEMM 核**。")

SEC = """
**24. 窗口 A 空手而归，但拿到两个硬结论：候选③ 被否，候选① 上位。**
按上一条的三步设计，先跑最便宜的 ③（`STRATA_MMQ_DEBUG_J=1`，纯打印）。跑了两次，**`pick_J` 一行都没出**。

**先查是不是我自己搞错了**（这一步不能省，否则结论会错在"开关没生效"上）：
容器内 `docker exec ... cat /proc/20/environ` 拿到引擎进程的真实环境——config 里的 **9 个 `STRATA_*` 全在**，
说明 env 是 `serve/server.py` 从 config JSON 注入的，**我的改动确实生效了**。
真因是：`pick_J` 用 `fprintf(stderr, …)`，**引擎的 stderr 不进 `docker logs`**（日志里能 grep 到的 `expert cache` 是 stdout）。
⇒ **操作教训：以后不要拿"打到 stderr"的开关做窗口判据**，这类窗口只会白停一次机。

**于是绕开开关，直接读源码判结构**（零停机）：

| 事实 | 位置 | 推出什么 |
|---|---|---|
| `Context::run()` 每次调用**只 `pick_J` 一次**，随即 `mul_mat_q_case<type>` **发一个 kernel** | `moe_mmq.cu:504` | launch 数 = MoE 分组数（层×组，≈96 量级） |
| 665 ms ÷ 96 ≈ **6.9 ms/launch** | 算术 | 比 kernel launch（µs 级）高 **三个数量级** |

⇒ **候选③（调度/建表）作为固定项主体被否掉**。这不需要窗口，属于结构判决。

**候选① 上位**：`p.tab` / gather 路径每次 prefill 要把参与专家**拼进连续缓冲**，成本 ∝ **字节数**、与 token 数无关——
正好是"固定项"的形状。定量：3.49 GiB ÷ 665 ms = **有效 5.6 GB/s**；PCIe 4.0 x16 实测满速，正常 H2D 能到 20 GB/s 量级
⇒ **瓶颈在拷贝路径**（未 pinned / 非异步 / 小片拷贝），不在 GEMM 核，也不在调度。

**这条改写了 `R95` 的方向**：不是"找更快的小批 GEMM kernel"（`P297` 已否），也不是"减少 launch"（本轮否），
而是**把每次 prefill 的专家权重搬运从 5.6 GB/s 提到接近链路带宽**——理论上 665 ms → 190 ms 量级，2K 预填直接 −15%。

**下一手（仍需窗口）**：`--pcie-frac` 从 0.20 调到 0.0（若语义是"允许走 PCIe 的比例"），
预测 **b 随借用字节线性下降**；若 b 不动，则搬运不走这条通道，候选① 也要打问号。
**我不在没验证的情况下把它写成结论**——`P418` 里记的是"领先假说"。
"""

PLAN_ADD = """
**补充 11（同日，窗口 A 与结构判决）**：`STRATA_MMQ_DEBUG_J=1` 两次窗口（485/2050/4046 tok）`pick_J` 均 0 行；**非 env 失效**（`/proc/20/environ` 的 9 个 `STRATA_*` 全在），真因是**引擎 stderr 不进 `docker logs`** ⇒ **纪律：不要用 stderr 型开关做窗口判据**。改读源码：`Context::run()` 每次只 `pick_J` 一次、只发一个 kernel ⇒ launch≈96、**6.9 ms/launch** 比 launch 开销高三个量级 ⇒ **候选③ 否**。**候选① 上位**：gather 每次拼连续缓冲，成本∝字节、与 token 无关；3.49 GiB ÷ 665 ms = **有效 5.6 GB/s**（PCIe 4.0 x16 应 ~20）⇒ **瓶颈是拷贝路径**，不是 GEMM 核/调度。下一手：`--pcie-frac 0.0`，预测 b 随借用字节线性下降。
"""

MEMSEC = """
- 04:3x–04:4x **窗口 A 空手（两次）**：`STRATA_MMQ_DEBUG_J=1` 下 `pick_J` 0 行；**env 没失效**（`/proc/20/environ` 9 个 `STRATA_*` 全在），**引擎 stderr 不进 docker logs** ⇒ **纪律：别用 stderr 开关做窗口判据**。读源码得结构判决：`Context::run()` 每调用一次 `pick_J`+一个 kernel ⇒ **6.9 ms/launch 不可信 ⇒ 候选③ 否**；**候选①（权重搬运）上位**：3.49 GiB ÷ 665 ms = **5.6 GB/s**，PCIe 4.0 x16 应 ~20 ⇒ 瓶颈在拷贝路径。下一手 `--pcie-frac 0.0`（预测 b 线性下降）。生产已还原（md5 `53ac61e0…`，health ok）。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "窗口 A（`STRATA_MMQ_DEBUG_J=1`）" in t:
        return "P418 窗口 A 已记"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加窗口 A 结论"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "24. 窗口 A 空手而归" in t:
        return "§24 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§24 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 11（同日，窗口 A 与结构判决）" in t:
        return "方案补充 11 已存在"
    anchor = "**另撤回**：用 `round(n/1000)` 分档比较两 campaign 是错的"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n", t.find("该拟合作废", i))
    if j < 0:
        return "段尾未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j+1] + PLAN_ADD + t[j+1:])
    return "方案补充 11 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "窗口 A 空手" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
