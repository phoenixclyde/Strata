#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039 (2nd half): write the confound into the plan, register pa7 in the rebuild recipe."""
import io

# ---- 1. plan writeback ------------------------------------------------------------------------
P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
assert "### 回写 · W1039" in s
add = """
**七、两臂误差是「共模」，而共模的来源是归约也被换掉了（`P457` / `P458`）。**

先看误差长什么样（`error_structure.py`，零窗口，读已有四份 tsv）：int8 臂 `|Δlogp|` 中位 **0.01769**、
>0.01 占 **54.41%**；fp16 臂中位 **0.01930**、>0.01 占 **55.22%**；逐点相关 **0.6965**，共同 >0.001 的位置 **3247/4995**。
两臂幅度分布几乎重合，而地板臂（同二进制、两次独立容器）**逐位相同** ⇒ **不是环境噪声，也不是各自位宽的舍入**
（fp16 的 q 误差是 int8 的 1/40，若由位宽主导两条曲线应差一个数量级）。据此撤回 `P454` 给的成因。

共模的位置在派发里，不在算术里：生产 `env` 9 项没有 `STRATA_GFX906_ATTN_REDUCE12`（容器内 `grep -c` = 0），
对照臂走 `attn_chunk_kernel<M,false,true>`（**REDUCE12 = false**，12 次 `warp_sum`）；而 OPT 臂的宏
`STRATA_ATTN_OPT_SWZ` 固定是 `<M,false,true,true,O>`（**REDUCE12 = true**，12-in-16 打包归约），
触发条件 `opt_sw != 0` 与那个 env 无关。**⇒ 每一个「开关 vs 对照」的数值门都同时换了点积指令和归约方式。**

**判据（`P459`，一停一起约 9 min，不换二进制）**：把 `ATTN_REDUCE12=1` 加到生产件 `b12180` 上，
对照臂就是它自己（另跑一遍 `b12180` 验跨容器地板）。
KL ≈ 0.038 ⇒ 归约是共因，`P447`/`P451`/`P453`/`P456` 的数值判决全部作废，必须对 REDUCE12 版的对照重测；
KL = 0 ⇒ 归约无辜，转 pa7 的两个诊断位：`ATTN_CTLREAD=1`（基线算术，走 OPT 的手写 K 读法与末尾乘 scale）
与 `ATTN_F16Q=1`（查询只做 fp16 往返，点积仍是 fp32 fma）。

**这一条的方法学价值高于任何单个开关**：`P446`（派发包在别的宏里）、`P441`（接错函数）、`P448`（`default: break`
掉内核）、到现在这条（对照与实验不同实例化），四次都是同一类错——**「我改了 A」和「我比的是 A」是两件事**。
所以给窗口脚本加一条硬要求：每臂开工前，先把「本臂与对照的实例化 / 环境差」逐项列出来打印进日志。
"""
if "两臂误差是「共模」" not in s:
    s = s.rstrip("\n") + "\n" + add
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("plan: appended 七")
else:
    print("plan: already present")

# ---- 2. rebuild recipe -----------------------------------------------------------------------
R = "deploy/REBUILD_RECIPE.tsv"
r = io.open(R, encoding="utf-8").read()
row = ("strata-0.1.57-pa7\tf04b91a6ebcbc649449632c39e8fdf01\t43576168\t"
       "gfx906/port-all @ (W1039 未提交)\tllama-master = b12180 bcb01528 + mmq@4c1004c\t"
       "build-pa3\tdiagnostic bits 16/32 (CTLREAD / F16Q), 8 switches present, NOT installed (P459)\n")
if "strata-0.1.57-pa7" not in r:
    if not r.endswith("\n"):
        r += "\n"
    io.open(R, "w", encoding="utf-8", newline="\n").write(r + row)
    print("recipe: +pa7")
else:
    print("recipe: pa7 already there")

# ---- 3. daily memory -------------------------------------------------------------------------
M = ".workbuddy/memory/2026-11-07.md"
mem = """
### W1039 补（11:1x–11:3x）数值判决被一个归约混淆污染 + 四项报告形态归位

- **归约混淆（本轮最贵的一条）**：所有 OPT 臂都由 `STRATA_ATTN_OPT_SWZ` 发成 `attn_chunk_kernel<M,false,true,true,O>`
  （**REDUCE12 = true**），而生产 env 9 项没有 `STRATA_GFX906_ATTN_REDUCE12` ⇒ 对照臂是 `<M,false,true>`（**false**）。
  ⇒ `P453`(DP4A) / `P456`(F16D) 的 KL 都是「点积 + 归约」两处一起变的结果，**不能归因到开关本身**。
  这是 `P446`/`P441`/`P448` 之后第四次同类：**「我改了 A」≠「我比的是 A」**。
- **误差共模的证据（零窗口）**：int8 与 fp16 两臂 `|Δlogp|` 分布几乎重合（中位 0.01769 vs 0.01930，>0.01 占 54.4% vs 55.2%），
  逐点相关 **0.6965**；地板臂两次独立容器**逐位相同** ⇒ 共模非噪声、非位宽。`P454` 的成因撤回。
- **判别只需一个 env**：`ATTN_REDUCE12=1` 加在 `b12180` 上 vs `b12180` 本身（`gate3.sh`，一停一起 ~9 min，不换二进制）。
  若 KL≈0.038 ⇒ 归约是共因，DP4A/F16D 判决全部重来；若 0 ⇒ 用 pa7 的 `CTLREAD` / `F16Q` 两位继续剥（`gate4.sh`）。
- **pa7**：`f04b91a6ebcbc649449632c39e8fdf01` / 43,576,168 B / 0 FAILED，八开关 `strings` 全在册；
  顺带把「bits 16/32 无 swizzle 时静默跑基线」改成打印一次警告。
- **四项报告形态归位**：w1039 一度把 §三 写成 6 行表、正文用 `## T1..T10`（第三套编号）。
  已按 w1031–w1037 的固定形态改回：H1 一句话 → `**一、**` 表 → `**二、**` → `**三、**` 单句（重启/停机/回滚/装机在内）→ `**四、**` → `## 正文` + `**n. …**`。
  `report_lint` 的「两套编号」检查就是为这种漂移加的。
"""
s2 = io.open(M, encoding="utf-8").read()
if "归约混淆（本轮最贵的一条）" not in s2:
    io.open(M, "a", encoding="utf-8", newline="\n").write(mem)
    print("memory: appended")
else:
    print("memory: already there")
