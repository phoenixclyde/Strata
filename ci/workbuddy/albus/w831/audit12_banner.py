# -*- coding: utf-8 -*-
"""给 W826/W827/W828/W829/W830 加 AUDIT12 横幅或事后注记（幂等）。"""
import io

DEP = "D:/workbuddy_space/strata_ws/deploy/"

BANNERS = {
 "W828_UPSTREAM_028_PORT.md": ("head", """## AUDIT12 更正摘要（2026-10-31）

> 本文件已过 AUDIT12（W826–W831 对抗审计）。三处 P0/P1 已就地更正，明细见 `AUDIT12_W826_W831.md`：
>
> 1. **§6.1 的 read 三档不可比** —— `strata-0.1.54n` 缺 W793/rocBLAS（`rocblas` 字符串 0 个 vs 0.1.53 的 3 个），
>    而 rocBLAS 正打在 prefill 的 f16 GEMM 上。**"升级 0 回归 0 收益"只对 decode 成立。**
> 2. **层数 = 48（原写 60）** —— `native_experts.txt` 的 layer 0..47、`48×512=24576`。受影响：§6.14 的每窗口字节/带宽、
>    §6.15 的并集 94 GB、§6.16 的搬运 72 GB/15 GB/s（更正后 52 GB/11 GB/s，反而与 W829 的 12 GB/s 实测对上）。
> 3. **§6.8 的 exact 表是 19 项（原写 15）**，且 `GDN_HEAD/GDN_PP` 我们本就开着，"一项都没开"不成立。
>
> 另：§6.15/§6.16 的 TTFT 曲线是在 **0.1.54n（无 rocBLAS）** 上量的，生产已是 `n2`，常数项 **1197→915 ms**；
> "对外口径"的 500 tok≈1.9 s / 3K≈5.2 s / 8K≈11.7 s 应各减约 0.28 s（且 8K 由 7.2K 实测验算约 12.5 s，原 11.7 s 是外推）。

"""),

 "W829_OPT_PLAN.md": ("head", """## AUDIT12 更正摘要（2026-10-31）

> 已过 AUDIT12。**§0/L4 的 batch KV 估计全错**：原文 214 MiB / 856 MiB / 1.9–3.4 GiB，
> 实测是 **2.95 GiB/slot**（214 MiB 是 32K 的口径，差 14 倍）⇒ batch 2 即 **−27% 槽位**、batch 9+ **装不下**。已就地更正。
> 另：**数值债只覆盖 5 项不是 8 项**；`prefill 内部` 四项只占 61.2%；`时间构成` 与 `--batch` 两处结论均已加限定。

"""),

 "W830_PATCH_LOSS_INCIDENT.md": ("head", """## AUDIT12 更正摘要（2026-10-31）

> 已过 AUDIT12。本文件一处**假绿**已更正：`WEB-UI` 当时判"没丢"，是因为标记用了 **上游自带** 的 `saveApiKey`；
> 部署的 `app.js` 与上游 v0.2.8 字节相同，真正缺的是 **PCIe 卡的 `· peak NN MB/s` 4 行**（已由 W831 补回）。
> 另外 §5 的 `1206→843` 是**单次复核读数**，结论以 §6 的 **1190→915 ms**（ABBA 各两轮）为准。
> 门禁本身也因此修过：标记改用 `ALBUS-*` 前缀，并同时校验 tree / image / served 三处。

"""),
}

TAILS = {
 "W827_UPSTREAM_028_ASSESS.md": """
## 9 事后注记（AUDIT12，2026-10-31）

本节"暂不升（DEFERRED）"在 **约 2 小时后被推翻**：W828 把生产升到了 0.1.54。
§5 列的四条触发条件当时 **一条也没满足**（`--spec` 仍 4、无 `--batch`、无 gfx906 修复、#4051 未真炸），
所以这次是**决策反转（用户要求"升上游最新"）**，不是条件触发。留此注记，避免单看本文误以为"按条件升级"。
另：本文 §3 称 `#4420`/`#4518` 不命中、`#4474`/`#4051` 命中，其中 #4474 的"槽位 −85"后来实测为 **−88**（22.04→21.79 GiB），方向一致。
""",

 "W826_NEXT_SESSION.md": """
## 5 事后注记（AUDIT12，2026-10-31）

实际顺序与本清单**相反**：先升了 0.1.54（W828 §6.2），calibrate 才在 **0.1.54n** 上跑（W828 §6.3/§6.7）。
所以 §1 的"先在 0.1.53 上跑 P0"已作废；而 calibrate 两次给出的建议**互相矛盾**（W828 §6.7），
其中"每值重启"那类臂不可信 —— 结论是：**calibrate 只可作为候选生成器，不可直接采纳**。
另 §2 的"8 项总量"实测只翻了 5 项（W828 §6.10 / AUDIT12）。
""",
}

for fn, (where, block) in BANNERS.items():
    p = DEP + fn
    s = io.open(p, encoding="utf-8").read()
    if "AUDIT12 更正摘要" in s:
        print("skip (already)", fn)
        continue
    lines = s.split("\n")
    # 插到标题行之后
    assert lines[0].startswith("# "), fn + " 首行不是标题"
    out = "\n".join([lines[0], ""] + block.split("\n") + lines[1:])
    io.open(p, "w", encoding="utf-8", newline="\n").write(out)
    print("head-banner", fn, len(s), "->", len(out))

for fn, block in TAILS.items():
    p = DEP + fn
    s = io.open(p, encoding="utf-8").read()
    if "AUDIT12" in s:
        print("skip (already)", fn)
        continue
    if not s.endswith("\n"):
        s += "\n"
    io.open(p, "w", encoding="utf-8", newline="\n").write(s + block)
    print("tail-note", fn, len(s), "->", len(s) + len(block))
