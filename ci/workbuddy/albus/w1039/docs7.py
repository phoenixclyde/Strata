#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: the probe's numbers -- the score path is exact to 1.8e-7, so read/arithmetic are out."""
import io

ROW = ("B6判定探针", "P465",
       "独立探针（合成池、1 秒 GPU、不启引擎）：手写读法算出的**分数只差 1.8e-7**（fp32 舍入级）⇒ 读法与末尾乘 scale 无罪",
       "W1039", "count", "1", "1", "DONE",
       "**W1039 独立探针（`t_probe.cu` / `t_probe`，`bash build_probe.sh run`；不启引擎、不动 config、不停生产，"
       "与引擎共用 GPU 约 1 秒，只申请几十 KB）**。合成 64 行 k8v4 池（随机 int8 codes + 真 half scale）+ 随机 q，"
       "同一个内核里对每一 lane 并排算两遍：`load8_q8` 的 `c[j]*sc` 路径 vs `p.k_q`/`p.k_scale` 手写索引 + 末尾 `pp*ks`。"
       "输出（row 0 / lane 0 与 lane 8）：codes 与 `load8` 反量化值**逐项相同**；per-lane 部分和 rel **0** 与 **2.66e-07**；"
       "32 lane 归约后的分数 rel **2.69e-07**。全量统计：2048 个 (row,lane) 对里 1300 对有差，"
       "**max|Δ| = 2.98e-08（部分和）/ 1.79e-07（分数）**，max rel 1.0e-03 只出现在接近 0 的值上。"
       "⇒ **读法与末尾乘 scale 是无罪的**，差异纯属 fp32 结合次序。"
       "**这一条把「读法」从嫌疑名单里永久划掉**（`P461` 里那一步到此彻底作废），"
       "也说明四臂那个 ≈0.04 不可能来自分数：1e-7 的分数扰动做不出 5% 的 argmax 翻边。"
       "⇒ 剩下的候选只有两处：**q tile 的内容**（`sq` swizzle/qflip、`sqh`、`sq8`）与 **softmax / V / merge 段**。"
       "下一步把探针扩到「整 12 头分数 + softmax + V」并排两遍——printf 在独立程序里是通的，这条信道已验证可用。"
       "本轮累计重启 15 次 / 停机 3993 s。",
       "P461;P464", "KW:1.8e-7|探针")

with io.open("deploy/PROGRESS.tsv", "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\t".join(ROW) + "\n")
print("ledger: +P465")

P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
add = """
**十一、探针把「读法」判无罪：分数只差 1.8e-7（`P465`）。**

独立探针（合成池 + 随机 q，同一个内核里两种读法并排算）：
codes 与 `load8` 反量化值**逐项相同**；per-lane 部分和 rel **0 / 2.66e-07**；32 lane 归约后分数 rel **2.69e-07**；
2048 对里 1300 对有差，**max|Δ| = 2.98e-08（部分和）/ 1.79e-07（分数）**。

⇒ 读法与末尾乘 scale **无罪**，差异只是 fp32 结合次序。四臂的 ≈0.04 不可能来自分数——
1e-7 的分数扰动做不出 5–6% 的 argmax 翻边。**剩下的候选只有两处**：q tile 的内容（`sq` 的 swizzle/qflip、`sqh`、`sq8`）
与 softmax / V / merge 段。

**工具结论（可复用）**：数值门里设备 `printf` 会被工具吞掉，但**独立 HIP 程序里的 `printf` 是通的**，
而且几十 KB 的探针可以与生产共用 GPU（不必停引擎）。以后凡是「引擎里看不见」的数值问题，先写探针。
"""
if "探针把「读法」判无罪" not in s:
    io.open(P, "a", encoding="utf-8", newline="\n").write("\n" + add)
    print("plan: appended 十一")

M = ".workbuddy/memory/2026-11-07.md"
mem = """
### W1039 探针（不用停引擎）：分数只差 1.8e-7，读法判无罪

- **独立 HIP 探针可以和生产共用 GPU**：只申请几十 KB、跑 1 秒，`docker run --device=/dev/kfd` 即可，**不必停引擎**。
  这比开窗口便宜两个数量级，而且 `printf` 在独立程序里是通的（引擎里会被数值门工具吞掉）。
- **结果**：同一个内核里并排跑 `load8_q8`（`c[j]*sc`）与 `p.k_q`/`p.k_scale` 手写索引 + 末尾 `pp*ks`，
  codes 与反量化值逐项相同；per-lane 部分和 rel 0 / 2.66e-07；32 lane 分数 rel 2.69e-07；
  2048 对里 1300 对有差，**max|Δ| 2.98e-08（部分和）/ 1.79e-07（分数）**。
- **⇒ 读法与末尾乘 scale 无罪**。四臂那个 ≈0.04 不可能来自分数（1e-7 做不出 5% argmax 翻边）。
  剩余候选：**q tile 内容**（`sq` 的 swizzle/qflip、`sqh`、`sq8`）与 **softmax / V / merge 段**。
- 探针编译两个坑：`clang++ ... | head` 会 SIGPIPE（BUILD_RC=141）导致二进制没生成——不要接 `head`，
  重定向到日志再 `grep`；`$VAR` 经 python→ssh→docker 内联会被吃掉，**一律写成容器内脚本文件**。
"""
s2 = io.open(M, encoding="utf-8").read()
if "读法判无罪" not in s2:
    io.open(M, "a", encoding="utf-8", newline="\n").write(mem)
    print("memory: appended")

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
old4 = "**四、进度** — **407 条 / 已结 320 / 78.6%**（本轮 +20：`P445`–`P464`）。"
new4 = "**四、进度** — **408 条 / 已结 321 / 78.6%**（本轮 +21：`P445`–`P465`）。"
assert old4 in r
r = r.replace(old4, new4, 1)

anchor = "**产物**：`albus/w1039/reply.md`（本件）"
add_r = """**19. 探针：分数只差 1.8e-7 —— 读法判无罪，嫌疑范围缩到两处（`P465`）**

不用窗口。**独立 HIP 探针可以和生产共用 GPU**（只申请几十 KB、跑 1 秒、不启引擎、不动 config），
而 `printf` 在独立程序里是通的——这条信道正好补上第 15 条被工具吞掉的那个洞。

同一个内核里对每一 lane 并排算两遍（`load8_q8` 的 `c[j]*sc` 路径 vs `p.k_q`/`p.k_scale` 手写索引 + 末尾 `pp*ks`）：

| 量 | 结果 |
|---|---|
| codes vs `load8` 反量化值 | **逐项相同**（row 0 / lane 0 / lane 8 全打印出来看过） |
| per-lane 部分和 rel | **0** 与 **2.66e-07** |
| 32 lane 归约后的分数 rel | **2.69e-07** |
| 全量 2048 对 | 1300 对有差，**max\\|Δ\\| = 2.98e-08（部分和）/ 1.79e-07（分数）** |

**⇒ 读法与末尾乘 scale 是无罪的**，差异纯属 fp32 结合次序。这一条把 `P461` 里「读法有问题」那一步**彻底作废**，
而且它给出一个更硬的推论：**1e-7 的分数扰动做不出 5–6% 的 argmax 翻边**，所以四臂那个 ≈0.04 不可能来自分数。

**嫌疑只剩两处**：① **q tile 的内容**——`sq` 的 swizzle/qflip 配对、`sqh` 的 fp16 填充、`sq8` 的 int8 量化；
② **softmax / V / merge 段**。下一步把探针扩到「整 12 头分数 + softmax + V」并排两遍——工具现成、信道已验证。

"""
assert anchor in r
r = r.replace(anchor, add_r + anchor, 1)
r = r.replace("`dump_fatbin.sh` / `unbundle.sh` / `gate7.sh`。", "`dump_fatbin.sh` / `unbundle.sh` / `gate7.sh` / `t_probe.cu` / `build_probe.sh`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: %d chars" % len(r))
