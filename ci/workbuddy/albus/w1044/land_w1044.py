#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1044 close-out: ledger, unique plan write-back, snapshot, recipe, memory."""
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
HAND = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")
RECIPE = os.path.join(ROOT, "deploy", "REBUILD_RECIPE.tsv")

ROWS = [
    ["B5本机缺口", "P513",
     "R103 装机完成：`strata-0.1.57-attn` + `STRATA_GFX906_ATTN_DP4A=1` 落生产，G1–G5 五道预注册门全过",
     "W1044", "count", "1", "1", "DONE",
     "**W1044 实测（两次窗口 + 一次冷启动收尾，共 重启 3 次 / 停机 2165 s / 装机 1 / 回滚 0）**。"
     "**生产换件**：引擎 `a85743d7…`(`kvg`) → **`3b758f88ddad25cdad236be267810a9e`(`attn`, 43,452,008 B)**；"
     "config `ee69ebc2…` → **`3dde880125925d785a49da69fa1ebdfb`**（args 38 逐字未动，env 9→10，只加 `STRATA_GFX906_ATTN_DP4A=1`）。"
     "**register** 新增 `P512`(ENV/ADOPTED)，D5 增量门只放行 `exe` 指针与这一项 env。"
     "**verdict.json**：G1 true（A/B build floor 四点逐字节）、G2 true（4 长度 KL(C)≤KL(D 锚)，零违例）、"
     "G3 true（ratio@20K 0.488、@32K 0.145、上限 0.977）、G4 true（needle off 9/9、on 9/9，含 64K 三深度，cached=0）、"
     "G5 true（8K/16K 墙钟不劣化）⇒ **go=true**。"
     "**冷启动复验**：重启后 exe=attn、config md5 不变、容器内 `/proc/<engine>/environ` 开关 ON、"
     "`kv-grow` 未关、`could not map` 0 条、冒烟 chat 返回 content、disk=build=running 三方一致。"
     "**在产零停机复核**：10,828 token 请求 `qsa attn 1974 ms`、cached=0、health ok（形状不同，不作定量结论）。"
     "**回滚**：`kvg`(`a85743d7…`) 在册，config 备份 `tmp/w1044/cfg_w1044b.bak`(=`ee69ebc2`)，≈45 s。",
     "P498;P499;P511;P512", "KW:go=true|冷启动|2165"],

    ["B6判定探针", "P514",
     "第一次窗口的 32K 点**取样面失效**：周期重复 ids 让参考分布退化，KL 掉到 1e-8，G2/G3 假 FAIL",
     "W1044", "count", "1", "1", "DONE",
     "**W1044 实测**。`set32k.ids.json` 把 20,000 ids 周期重复到 32,768；四臂 logits 跑完，1K/8K/20K 的 KL "
     "与 W1041 **逐位复现**（`0.000371/0.003453/0.187498` vs `0.00037/0.00345/0.18750`），但 32K 点 "
     "`KL(C)=7.08e-08`、`KL(D)=2.11e-08`，比值 3.36 ⇒ G2 违例、G3 `3.36 > 0.977` 判否。"
     "`albus/w1044/diag_32k.py` 实测根因：**32K 参考分布 top1=1.000000 / 熵 0.0000 / 三臂 argmax 同为 506** —— "
     "重复模式让模型把下一 token 预测成完全确定，所有量化扰动只剩浮点尾数，比值是两个噪声相除、无统计意义。"
     "⇒ **判 INVALID（取样面失效）而非「DP4A 有长度悬崖」**，窗口按预注册 fail-closed 判 NO-GO 并完整还原（`kvg`+`ee69ebc2`，停机 1565 s）。"
     "**修法**：`make_ids_v2.py` 生成 `set32k_v2.ids.json` —— 前 20,000 ids 与 W1041 逐字相同（三点仍可对账），"
     "后 12,768 换成 940,927 B 内核源码 tokenize 出的新 ids；重跑 32K 得 `KL(C)=0.001457 / KL(D)=0.010032`，ratio 0.145，G3 稳过。"
     "**同族**：P493/P496/P500/P506 之后又一次「门验的对象错了」——这次是**门本身的输入被造坏了**。",
     "P511;P506", "KW:top1=1.000000|set32k_v2|0.145"],

    ["B8工程", "P515",
     "装机收尾的 env 校验读错取样面（宿主机用户读不到 root-only `/proc/<pid>/environ`），且 trap 只还原 config 不重启 ⇒ 留下 config/进程错配",
     "W1044", "count", "1", "1", "DONE",
     "**W1044 实测**。窗口 B 的 `go=true` 后已写 config 并起容器，脚本用 "
     "`tr '\\0' '\\n' < /proc/$PID/environ | grep -q '^STRATA_GFX906_ATTN_DP4A=1$'` 校验；"
     "宿主机 `albus` 用户对 `-r-------- root root` 的 `/proc/<pid>/environ` **无权限**，连原有的 `STRATA_GFX906_TUNED=1` 都读不到 ⇒ 误报 FAIL。"
     "trap 的 `restore()` 只 `cp` 回旧 config、**没有重启进程**，于是留下「config 指向 `kvg`、进程跑 `attn`」的错配（下次重启会静默换件，违反三方一致）。"
     "**正确取样面**：`docker exec strata166-407 cat /proc/<容器内pid>/environ`（容器内 root）→ 实测含 "
     "`STRATA_GFX906_TUNED=1`、`STRATA_DECODE_TIMING=1`、**`STRATA_GFX906_ATTN_DP4A=1`** ⇒ 装机其实已生效。"
     "**修法**：`finish_install.sh` 写回 `cfg_new.json` 消除错配，再冷启动一次证明持久化（51 s），"
     "任何失败自动 `cp` 回 `cfg_w1044b.bak` + `docker restart` 回滚。"
     "**两个脚本缺陷都要记住**：① 校验引擎 env 必须从容器内读；② 装机后失败的 restore **必须重启容器**，只改 config 不够。",
     "P493;P496", "KW:environ|config/进程错配|冷启动"],

    ["B6判定探针", "P516",
     "上网核外证后改机理：INT8 量化里注意力 logits 是最敏感层，长度轴必要性更高；G3 的 2× 是工程约定非社区标准",
     "W1044", "count", "1", "1", "DONE",
     "**W1044 上网核（不改判据、只改说明，发生在开窗之前）**。W1043 初稿写「R103 改 query 侧点积、KV 没动 ⇒ "
     "长度悬崖机理上不适用」——**说得太满，作废**。外证：量化综述 `aiknowledge.cn/article/69829`、"
     "TrueSight《INT8 量化下的 Transformer 精度崩塌》、SageBwd、technologyonthe 2026-09 生产实践一致指出 "
     "**注意力 logits 是量化里最敏感的一层**（softmax 对 0.01 量级 pre-softmax 误差敏感、指数非线性放大），"
     "误差随层数 / decode 步 / 序列长度累积，且「8K 上无法区分的配置可能在 64K 退化」。R103 动的正是 `QK^T` 点积。"
     "⇒ 误差机制与 KV 量化不同（不是记忆条目丢失），但**长度轴照样必须测、G3 必要性反而更高**。"
     "**诚实边界**：G3 的 2× 阈值是本项目工程约定、**无外部权威依据**，已在 `LONGCTX_GATE.md` 标死，不冒充社区标准。"
     "配套取样面收缩也在开窗前写明：`qq_r103.py` 的 `PROMPT_LENS` 写死到 20K，64K logits 不做，"
     "64K 风险交给 needle 网格；G5 墙钟用 W1042 同形态数据、跨窗口仅作护栏。",
     "P511", "KW:注意力 logits|工程约定|开窗之前"],
]


def main():
    lines = io.open(P, encoding="utf-8").read().splitlines()
    have = {l.split("\t")[1] for l in lines if l.count("\t") >= 9 and not l.startswith("#")}
    for r in ROWS:
        assert len(r) == 11 and all("\t" not in x for x in r), r[1]
        whole = " ".join(r)
        for kw in r[10].replace("KW:", "").split("|"):
            assert kw in whole, "%s KW %r missing" % (r[1], kw)
    todo = [r for r in ROWS if r[1] not in have]
    # R103 close-out + AUDIT29 round count
    n_r103 = n_r107 = 0
    for i, l in enumerate(lines):
        f = l.split("\t")
        if len(f) >= 11 and f[1] == "R103":
            f[6], f[7] = "1", "DONE"
            f[2] = "R103 已装机（W1044：G1–G5 全过，`attn` + `ATTN_DP4A=1` 落生产）"
            lines[i] = "\t".join(f)
            n_r103 += 1
        if len(f) >= 11 and f[1] == "R107":
            f[2] = f[2].replace("12 轮连续未审", "13 轮连续未审")
            f[8] = f[8].replace("`12 unaudited rounds in a row (> 8)`（W1032–W1043",
                                "`13 unaudited rounds in a row (> 8)`（W1032–W1044")
            f[8] = f[8].replace("W1040 W1041 W1042 W1043", "W1040 W1041 W1042 W1043 W1044")
            f[10] = "KW:AUDIT29|13 轮连续未审|audit_scope"
            lines[i] = "\t".join(f)
            n_r107 += 1
    assert n_r103 == 1 and n_r107 == 1, (n_r103, n_r107)
    lines += ["\t".join(r) for r in todo]
    io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    tot = done = 0
    for l in io.open(P, encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
            try:
                tot += int(f[5]); done += int(f[6])
            except ValueError:
                pass
    pct = 100.0 * done / tot
    print("TOTALS %d / %d / %.1f%%  (+%d rows)" % (tot, done, pct, len(todo)))

    # ---- unique plan §0.1
    s = io.open(PLAN, encoding="utf-8").read()
    s = re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1043；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1044；" % (tot, done, pct), s, count=1)
    old_engine = next(l for l in s.splitlines() if l.startswith("| 引擎 md5 / 大小 |"))
    new_engine = ("| 引擎 md5 / 大小 | **`3b758f88ddad25cdad236be267810a9e` / 43,452,008 B（`strata-0.1.57-attn`，"
                  "W1044 装机：W1042 的 OPT 移植 + `STRATA_GFX906_ATTN_DP4A=1`；`--kv-grow` 仍开）**；"
                  "回滚 `strata-0.1.57-kvg` = `a85743d7f554159e8ac1e2d432d2e5ea` / 43,214,976 B，"
                  "更早 `b12180` = `d24f8293b575fbcee6c097239d9599cb` | disk = build = running 三方；冷启动复验 W1044 |")
    s = s.replace(old_engine, new_engine, 1)
    old_cfg = next(l for l in s.splitlines() if l.startswith("| config md5 / args / env |"))
    new_cfg = ("| config md5 / args / env | **`3dde880125925d785a49da69fa1ebdfb`**"
               "（`exe=/data/bin/strata-0.1.57-attn`，args 38 逐字未动，env 9→**10**：只多 `STRATA_GFX906_ATTN_DP4A=1`，"
               "来自 register `P512`）/ **38** / **10** | D5 增量门 `tools/deploy_gate.py --cfg-base/--cfg-new --reg-ids P512`；"
               "旧值 `ee69ebc2…`（`kvg`，9 env）是回滚面 |")
    s = s.replace(old_cfg, new_cfg, 1)
    qline = next(l for l in s.splitlines() if l.startswith("| **唯一队列** |"))
    qnew, n = re.subn(r"\*\*R103 .*?）\*\* →",
                      "~~**R103 已装机（W1044：G1–G5 全过、冷启动复验）**~~ →", qline, count=1)
    assert n == 1, "queue R103 anchor"
    s = s.replace(qline, qnew, 1)

    title = "### 回写 · W1044（2026-11-07 17:14–17:57）R103 装机完成：两次窗口 + 一次冷启动"
    if title not in s:
        block = """__TITLE__

- **生产换件**：`strata-0.1.57-attn`（`3b758f88…` / 43,452,008 B）+ config `3dde8801…`（args 38 未动、env 9→10，只加 `STRATA_GFX906_ATTN_DP4A=1`，register `P512`）。**重启 3 次 / 停机 2165 s / 装机 1 / 回滚 0**（窗口 A 1565 s + 窗口 B 549 s + 冷启动 51 s）。冷启动后 exe=attn、config 不变、容器内 env 开关 ON、health ok、冒烟通过、disk=build=running 三方一致。
- **门**：预注册 `albus/w1043/LONGCTX_GATE.md`（W1044 开窗前修订）的 **G1–G5 全过** —— build floor 四点逐字节；四长度 KL(C)≤KL(D 锚)；ratio@32K 0.145 ≤ 0.977；needle 网格 off 9/9、on 9/9（含 64K 三深度、cached=0）；8K/16K 墙钟不劣化 ⇒ `verdict.json go=true`。`deploy_gate.py` D1–D6 全 PASS（D5 增量只 `exe`+一项 env）。
- **窗口 A 判 NO-GO 是对的（`P514`）**：32K ids 周期重复 ⇒ 参考分布 `top1=1.000000 / 熵 0`，KL 掉到 1e-8，比值 3.36 是噪声相除。判 **INVALID（取样面失效）**，不是「DP4A 有长度悬崖」；按预注册还原。1K/8K/20K 与 W1041 逐位复现，证明取样面本身可靠。修法：`set32k_v2` 前 20K 同源、后 12,768 换成非重复源码 ids。
- **窗口 B 栽在收尾校验（`P515`）**：宿主机 `albus` 读不到 root-only `/proc/<pid>/environ` ⇒ 误判开关未生效；trap 只还原 config 不重启 ⇒ 留下 config/进程错配。容器内 root 复核确认 env 实际有 `ATTN_DP4A=1`，`finish_install.sh` 写回 cfg_new + 冷启动消除错配并验证持久化。**两条脚本铁律**：引擎 env 从容器内读；装机后失败的 restore 必须重启容器。
- **机理改判（`P516`，上网核后）**：注意力 logits 是 INT8 量化最敏感层，softmax 非线性放大误差、随长度累积 ⇒ W1043「KV 没动所以长度悬崖不适用」作废，长度轴必要性反而更高；G3 的 2× 是工程约定非社区标准。
- **外证**：aiknowledge 量化综述、TrueSight INT8 注意力漂移、SageBwd、technologyonthe 2026-09 生产实践；NeurIPS 2026《Length, Not Bit Width》190 runs、vLLM 128K FP8 needle 91%→13%、RULER/NoLiMa（W1043 已引）。
- **边界**：64K 只做 needle 任务级、未做 64K fp32 logits；decode 长生成门未做；R108 dot8 仍无生产调用点。`audit_scope §A` = **13 轮连续未审**（W1032–W1044，阈值 8），仍 FAIL；本轮三个缺陷都是跑门撞出来的，不是审计查出来的。
""".replace("__TITLE__", title)
        s = s.rstrip("\n") + "\n\n" + block
        t0 = s.index("| 小节 |")
        last = s.rfind("| `回写 ·", t0, s.index("> **【AUDIT27", t0) if "> **【AUDIT27" in s[t0:] else t0 + 80000)
        assert last > 0
        eol = s.index("\n", last) + 1
        row = ("| `回写 · W1044（2026-11-07 17:14–17:57）R103 装机完成：两次窗口 + 一次冷启动` | "
               "G1–G5 全过；32K 取样面失效与修复；env 校验与 trap 缺陷；机理改判 | W1044 |\n")
        s = s[:eol] + row + s[eol:]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("plan written")

    # ---- snapshot
    h = io.open(HAND, encoding="utf-8").read()
    h2, n = re.subn(r"(> SNAPSHOT: round=)W\d{4}", r"\g<1>W1044", h, count=1)
    assert n == 1
    h2 = h2.replace("prod_exe=strata-0.1.57-kvg prod_md5=a85743d7f554159e8ac1e2d432d2e5ea config_md5=ee69ebc272ce41a116f50ecb3bf0edc2",
                    "prod_exe=strata-0.1.57-attn prod_md5=3b758f88ddad25cdad236be267810a9e config_md5=3dde880125925d785a49da69fa1ebdfb")
    io.open(HAND, "w", encoding="utf-8", newline="\n").write(h2)
    print("snapshot -> W1044 / attn")

    # ---- recipe
    rlines = io.open(RECIPE, encoding="utf-8").read().splitlines()
    hit = 0
    for i, l in enumerate(rlines):
        f = l.split("\t")
        if f and f[0] == "strata-0.1.57-attn":
            f[-1] = (f[-1] + " **W1044 已装机**：config `3dde8801…`（env 10，"
                     "`STRATA_GFX906_ATTN_DP4A=1` 来自 `P512`）；G1–G5 全过，见 `P513`/`P514`/`P515`。")
            rlines[i] = "\t".join(f)
            hit += 1
    assert hit == 1, hit
    io.open(RECIPE, "w", encoding="utf-8", newline="\n").write("\n".join(rlines) + "\n")
    print("recipe attn -> installed")

    # ---- daily memory
    m = io.open(MEM, encoding="utf-8").read()
    if "### W1044（" not in m:
        add = """
### W1044（17:14–17:57）R103 装机完成：`attn` + `ATTN_DP4A=1` 进生产

- **生产**：`strata-0.1.57-attn`（`3b758f88…` / 43,452,008 B）+ config `3dde8801…`（args 38 未动、env 9→10，只加 `STRATA_GFX906_ATTN_DP4A=1`；register `P512`）。冷启动后开关 ON、health ok、冒烟通过、disk=build=running 三方一致。**重启 3 次 / 停机 2165 s / 装机 1 / 回滚 0**（窗口 A 1565 s + 窗口 B 549 s + 冷启动 51 s）。回滚件 `kvg`（`a85743d7…`）+ `tmp/w1044/cfg_w1044b.bak`。
- **G1–G5 全过**：build floor 四点逐字节；四长度 KL(C)≤KL(D 锚)；ratio@32K 0.145 ≤ 0.977；needle off 9/9、on 9/9（含 64K 三深度、cached=0）；8K/16K 墙钟不劣化。`deploy_gate.py` D1–D6 全 PASS。
- **窗口 A 判 NO-GO（P514）**：`set32k` 周期重复 ⇒ 32K 参考分布 `top1=1.000000 / 熵 0`，KL 1e-8、比值 3.36 是噪声相除 ⇒ **取样面失效**，不是长度悬崖。1K/8K/20K 与 W1041 逐位复现。修法 `set32k_v2`：前 20K 同源、后 12,768 换成非重复源码 ids ⇒ 32K `KL(C)=0.001457 / KL(D)=0.010032`、ratio 0.145。
- **窗口 B 收尾缺陷（P515）**：宿主机 `albus` 读不到 root-only `/proc/<pid>/environ` ⇒ 误判开关未生效；trap 只还原 config 不重启 ⇒ **config/进程错配**。容器内 root 复核确认 env 有 `ATTN_DP4A=1`，`finish_install.sh` 写回 cfg_new + 冷启动消除。**铁律**：引擎 env 从容器内读；装机后失败 restore 必须重启容器。
- **机理改判（P516，上网核）**：注意力 logits 是 INT8 量化最敏感层、softmax 非线性放大、误差随长度累积 ⇒ W1043「KV 没动所以长度悬崖不适用」作废；G3 的 2× 是工程约定非社区标准。
- **在产复核**：10,828 token 请求 `qsa attn 1974 ms`、cached=0、health ok（形状不同，不作定量结论）。
- 进度 **__TOT__ 条 / 已结 __DONE__ / __PCT__%**；`audit_scope §A` = **13 轮连续未审**（W1032–W1044），R107 已同步。
""".replace("__TOT__", str(tot)).replace("__DONE__", str(done)).replace("__PCT__", "%.1f" % pct)
        io.open(MEM, "w", encoding="utf-8", newline="\n").write(m.rstrip("\n") + "\n" + add)
        print("memory appended")


if __name__ == "__main__":
    main()
