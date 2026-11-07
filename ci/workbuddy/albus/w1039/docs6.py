#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: the DPP discriminator lands exact -- so the drift tracks "changed the per-lane partial", not the
reduction and not the instantiation.  Ledger + plan + memory + report."""
import io

ROW = ("B6判定探针", "P464",
       "判别臂 `ATTN_DPP=1` 逐位相同（100.00% / KL 0.00000）⇒ 漂移只跟「改没改 per-lane 部分和」走，与归约、与实例化无关",
       "W1039", "count", "1", "1", "DONE",
       "**W1039 窗口（`gate7.sh`，12:28:48–12:33:06，停机 258 s，一次臂）**。`ATTN_DPP=1`（bit1）只把 `warp_sum` 的"
       "实现换成 DPP、**不碰任何算术**，设计上必须逐位相同；实测对 pa7 的 ctl **100.00% / KL 0.00000 / PPL 4.048 vs 4.048**。"
       "把六个臂排成判别表（同一个 ctl、同一 4995 点、同一 `--kv k8v4`）："
       "**bit0 REDUCE12 = 0.00000**（12-in-16 归约）、**bit1 DPP = 0.00000**（归约实现）；"
       "**bit2 int8 dot4 = 0.04130**、**bit3 fp16 dot2 = 0.03798**、**bit4 CTLREAD = 0.04111**、**bit5 F16Q = 0.04479**。"
       "⇒ 前两个只动**归约**、后四个都动 **per-lane 的 8 项部分和**。"
       "**结论**：④ 组的漂移与「归约实现」「哪个模板实例」都无关，只与「per-lane 部分和不是基线那条代码算的」相关；"
       "而 `P463` 已证明 CTLREAD 那条分支被编译器展平 8 倍，所以「源码等价」不足以证明这四个臂里哪个是错的——"
       "**但足以判定：OPT 数值门现在不能用来给 DP4A / F16D 定性**。下一步改成独立探针内核（合成数据、~30 s GPU、不进引擎），"
       "直接把两种读法算出的分数打出来。",
       "P463;P460", "KW:DPP|判别表")

with io.open("deploy/PROGRESS.tsv", "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\t".join(ROW) + "\n")
print("ledger: +P464")

P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
add = """
**十、判别臂落地：漂移只跟「改没改 per-lane 部分和」走（`P464`）。**

六臂判别表（同一个 ctl、同一 4995 点、同一 `--kv k8v4`）：

| 臂 | 改了什么 | top-1 | KL |
|---|---|---|---|
| bit0 `REDUCE12=1` | 只换**归约**（12 次 warp_sum → 12-in-16 打包） | **100.00%** | **0.00000** |
| bit1 `ATTN_DPP=1` | 只换**归约实现**（shuffle → DPP），不碰算术 | **100.00%** | **0.00000** |
| bit2 `ATTN_DP4A=1` | per-lane 部分和改成 `v_dot4_i32_i8` | 93.55% | 0.04130 |
| bit3 `ATTN_F16D=1` | per-lane 部分和改成 4×`v_dot2_f32_f16` | 94.29% | 0.03798 |
| bit4 `ATTN_CTLREAD=1` | per-lane 部分和改写成**基线算术**（手写 K 读） | 93.97% | 0.04111 |
| bit5 `ATTN_F16Q=1` | q 走 fp16 往返、点积仍 fp32 fma | 93.61% | 0.04479 |

**两条干净的边界**：归约（bit0/bit1）**逐位不变**；凡是动 per-lane 部分和的（bit2–bit5）**一律 ≈0.04**，
且四个数彼此只差 0.007、两两相关仅 0.50–0.65——**这不是「某个分支写错」的样子**。

**所以 `R103` 的 attn 数值面暂停**：先用独立探针内核（合成 q/k、~30 s GPU、不进引擎、不占窗口）
把「基线读法」与「手写读法」算出的分数并列打出来，回答「同一 (row, lane) 读到的字节与 scale 是否相同」。
这个问题一有答案，四臂的 0.04 是不是同一个原因就确定了。
"""
if "判别臂落地：漂移只跟" not in s:
    io.open(P, "a", encoding="utf-8", newline="\n").write("\n" + add)
    print("plan: appended 十")

M = ".workbuddy/memory/2026-11-07.md"
mem = """
### W1039 判别臂（12:28–12:33，停机 258 s）六臂判别表定了边界

- **`ATTN_DPP=1` = 100.00% / KL 0.00000**（只换归约实现、不碰算术）⇒ 与 bit0 `REDUCE12` 一样**逐位不变**。
- **判别表**：改**归约**的两臂（REDUCE12 / DPP）全 0.00000；改 **per-lane 部分和**的四臂（DP4A 0.04130 / F16D 0.03798 /
  CTLREAD 0.04111 / F16Q 0.04479）一律 ≈0.04，两两相关仅 0.50–0.65。
- **⇒ 漂移与「归约」「哪个实例化」无关，与「per-lane 部分和换了算法」强相关**；但四个数彼此几乎相同却又只是中等相关，
  不像单一错误，像「任何 1e-3 级扰动都会让 5% 的 argmax 翻边」的敏感度 + 各自的独立分量。
- **下一步**：独立探针内核（合成 q/k、~30 s GPU、不进引擎、不占窗口），把两种读法的分数并列打出来。
  这条比再开窗口便宜，而且它是唯一能直接回答「同一 (row,lane) 读到的字节与 scale 是否相同」的办法。
"""
s2 = io.open(M, encoding="utf-8").read()
if "六臂判别表定了边界" not in s2:
    io.open(M, "a", encoding="utf-8", newline="\n").write(mem)
    print("memory: appended")

# ---- report -----------------------------------------------------------------------------------
R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
old4 = "**四、进度** — **406 条 / 已结 319 / 78.6%**（本轮 +19：`P445`–`P463`）。"
new4 = "**四、进度** — **407 条 / 已结 320 / 78.6%**（本轮 +20：`P445`–`P464`）。"
assert old4 in r
r = r.replace(old4, new4, 1)

# section 三: one more window
old3 = "⑨ 复现判别 11:57:09–12:10:11（1 次 / **782 s**，含一次 260 s 臂超时）；"
new3 = ("⑨ 复现判别 11:57:09–12:10:11（1 次 / **782 s**，含一次 260 s 臂超时）"
        "⑩ DPP 判别 12:28:48–12:33:06（1 次 / **258 s**）；")
assert old3 in r
r = r.replace(old3, new3, 1)
r = r.replace("**重启 14 次、停机 3735 s、回滚 0 次、装机 0 次**", "**重启 15 次、停机 3993 s、回滚 0 次、装机 0 次**", 1)
r = r.replace("九个窗口依次是", "十个窗口依次是", 1)

anchor = "**产物**：`albus/w1039/reply.md`（本件）"
add_r = """**17. 判别臂落地：边界画出来了，问题定位到「per-lane 部分和」（`P464`）**

`ATTN_DPP=1` 只把 `warp_sum` 换成 DPP、不碰任何算术，实测对 pa7 的 ctl **100.00% / KL 0.00000**。
六臂排成判别表（同一 ctl、4995 点、`--kv k8v4`）：

| 臂 | 改了什么 | top-1 | KL |
|---|---|---|---|
| bit0 `REDUCE12=1` | 只换**归约** | **100.00%** | **0.00000** |
| bit1 `ATTN_DPP=1` | 只换**归约实现** | **100.00%** | **0.00000** |
| bit2 `ATTN_DP4A=1` | per-lane 部分和 → `v_dot4_i32_i8` | 93.55% | 0.04130 |
| bit3 `ATTN_F16D=1` | per-lane 部分和 → 4×`v_dot2_f32_f16` | 94.29% | 0.03798 |
| bit4 `ATTN_CTLREAD=1` | per-lane 部分和 → **基线算术**（手写 K 读） | 93.97% | 0.04111 |
| bit5 `ATTN_F16Q=1` | q 走 fp16 往返、点积仍 fp32 fma | 93.61% | 0.04479 |

**两条边界干净得不能再干净**：只动归约的两臂 **逐位不变**；凡是动 per-lane 部分和的四臂**一律 ≈0.04**。
所以「归约」「哪个模板实例」都被排除了，剩下的是**这 8 项部分和的算法**。

**但四个数几乎相同、两两相关却只有 0.50–0.65**——这不是「某个分支写错」的样子，更像
**「任何千分之一量级的分数扰动都会让 5% 的 argmax 翻边」的敏感度 + 各自的独立分量**。
要分开这两者，必须看到**分数本身**，而这需要一条能把数值打出来的信道——见下。

**18. 下一步：独立探针内核（约 30 s GPU，不进引擎、不占窗口）**

现有两条仪器路线都不能用：设备 `printf` 被数值门工具吞掉（第 15 条），`--cuda-device-only` 重编被 TU 的
host-only 符号挡住（第 16 条）。所以写一个**独立的小 HIP 程序**：合成 q/k、按 k8v4 的池布局摆一份数据，
分别用 `load8_q8` 与手写索引算同一 (row, lane) 的部分和，把 codes / scale / 两个结果并列打到 stdout。
它只占 30 s GPU、不启引擎、不动 config，能直接回答「同一 (row, lane) 读到的字节与 scale 是否相同」。

"""
assert anchor in r
r = r.replace(anchor, add_r + anchor, 1)
r = r.replace("`isa3.py` / `dump_fatbin.sh` / `unbundle.sh`。", "`isa3.py` / `dump_fatbin.sh` / `unbundle.sh` / `gate7.sh`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: %d chars" % len(r))
