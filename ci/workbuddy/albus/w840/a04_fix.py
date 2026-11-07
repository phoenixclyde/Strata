#!/usr/bin/env python3
# W840-04 AUDIT13 就地修复（锚点唯一才写；--apply 才落盘）
import io, sys, os

APPLY = "--apply" in sys.argv
D = "D:/workbuddy_space/strata_ws/deploy/"

EDITS = [
 # ---------------- W832 ----------------
 ("W832_OPT_PLAN_V2.md",
  "**33 条 512-token 生成给出 33 个不同的 sha**",
  "**36 条 512-token 生成给出 36 个不同的 sha**（AUDIT13 更正：原写 33/33。原始 `w832_tune_results.jsonl` 是 36 条、36 个不同 sha，且其中 3 条只生成 446/318/420 token，被当成 512-token 计入上表）"),

 ("W832_OPT_PLAN_V2.md",
  "任一臂的 `ms/win` 与 base 差 < 2%",
  "任一臂的**声明判据**（`tok/ms`）与 base 差 < 2%（AUDIT13 更正：原文写 `ms/win`。四臂的 `ms/win` 配对差是 +11.75 / −7.24 / −4.11 / +2.53%，同配置复本之间就差 +4.88% ⇒ 原停机条件在这台机器上永不可能触发）"),

 ("W832_OPT_PLAN_V2.md",
  "**−0.6%**（噪声内） |",
  "**−0.6%**（噪声内；AUDIT13：此臂是单轮 A→B、read 为 n=2 均值且含冷启动样本，按本项目自己的规矩应记 **UNRESOLVED**，不是 CONFIRMED） |"),

 ("W832_OPT_PLAN_V2.md",
  "关掉后 KL 0.0000、argmax 100%、top-10 1.00、|Δlp| 0.00000。",
  "关掉后 KL 0.0000、argmax 100%、top-10 1.00、|Δlp| 0.00000。（AUDIT13 更正：只有 `GDN_HEAD` 有臂——`w833_klegdn.json` 设 `STRATA_GDN_HEAD=0`，且 EG.tsv 与 E0.tsv 的 md5 同为 `fadf1889…`，位等价成立；`GDN_PP` **从未单独测**，不能一并判零债。）"),

 ("W832_OPT_PLAN_V2.md",
  "位等价 ⇒ 零数值代价；顺序不变，无理由关",
  "位等价 ⇒ 零数值代价；顺序不变，无理由关（AUDIT13：仅 `GDN_HEAD` 有实测，`GDN_PP` 未测）"),

 ("W832_OPT_PLAN_V2.md",
  "量级从 0.029 变成 **≈0.045 上下**",
  "量级从 0.029 变成 **≈0.045 上下**（AUDIT13 更正：这个加法本身无效——0.0171 取自 6 个 prompt 尾部位置、0.0293 取自 45 个位置，两个样本总体不同；且 0.0171 里 88% 来自单点 0.1006。只能记「0.0171 这个量级上另有一笔」，不能报和。）"),

 ("W832_OPT_PLAN_V2.md",
  "−3.2% 只出现在最短档且只有 3 次重复，另两档反向 ⇒ 是抖动，不是效应。",
  "−3.2% 只出现在最短档，另两档反向。（AUDIT13 复核 `w834_pool.out`：read1300 三对逐一比较 pw13 **三次都更快**（4414>4380、4051>3960、4092>3949），是同向而非抖动。⇒ 该项应记 **UNRESOLVED**（n=3、无 ABBA、无噪声底盘），不记「无差异」。）"),

 # ---------------- W835 ----------------
 ("W835_GFX906_PORT_FEASIBILITY.md",
  "**可触及量 ≈ 33 ms（73%）**。若各项拿到 30–50% 局部改善，**合计 −5% ~ −10%**；",
  "**可触及量 ≈ 24.19 ms（53.8%）**（AUDIT13 更正：原写 33 ms / 73%，把标 ✗ 的 6.50 ms 等待也算了进去；表中 ✓ 项只有 7.46+7.01+5.88+3.84）。若各项拿到 30–50% 局部改善，**合计 −16% ~ −27%**（原文写 −5~−10%，与自表差 3–5 倍）；"),

 ("W835_GFX906_PORT_FEASIBILITY.md",
  "26.5 ms，bf16 下 116.5 ms = 3.9×",
  "26.5 ms，bf16 下 116.5 ms = **4.40×**"),

 ("W835_GFX906_PORT_FEASIBILITY.md",
  "**这 3.9× 我们已经吃到了**",
  "**这 4.40× 我们已经吃到了**"),

 # ---------------- W836 ----------------
 ("W836_BRANCH.md",
  "| head | **`642de24f`**（2026-10-31，**8 个 commit**） |",
  "| head | **`642de24f`**（2026-10-31，**8 个 commit**）—— 快照时点；现 head `9ac564f`、**10 个 commit** |"),

 ("W836_BRANCH.md",
  "| 改动面 | **10 个文件，+216 / −9** |",
  "| 改动面 | **10 个文件，+216 / −9**（快照时点；AUDIT13 用 GitHub compare 核到现为 **11 文件 / +243 −9**） |"),

 ("W836_BRANCH.md",
  "| 改动面 | ✅ 6 文件 +94/−7（无多余） |",
  "| 改动面 | ✅ 6 文件 +94/−7（第 7 个 commit 时点；无多余） |"),

 ("W836_BRANCH.md",
  "即 `find_package(rocblas)` 已被执行并找到包 |",
  "即 `find_package(rocblas)` 已被执行并找到包。（AUDIT13 更正：`find_package` 执行 **≠** `STRATA_ROCBLAS_AVAILABLE` 进了编译单元，更 ≠ 链接进二进制；同一张表下一行还写着「完整编译未做」。真判据是构建日志里 `rocblas_state_ not used` 归零 + 二进制里 `rocblas` 字符串数。） |"),

 ("W836_BRANCH.md",
  "| 运行时 banner | ✅ `strata: gfx906 (MI50-class)",
  "| 运行时 banner（**来自单独编译的测试件，不是引擎**） | ✅ `strata: gfx906 (MI50-class)"),

 ("W836_BRANCH.md",
  "**补丁门禁 11 项全 OK**",
  "**补丁门禁 11 项全 OK**（当时项数；AUDIT13 时已扩到 17 项）"),

 # ---------------- W839 ----------------
 ("W839_ARCH_ENTRY.md",
  "## 3 改法（分支上的第 10 个 commit）",
  "## 3 改法（分支上的第 9 个 commit；trace 是第 10 个）"),

 ("W839_ARCH_ENTRY.md",
  "预热 **12820 MB/s**",
  "预热 **12820 MB/s**（与 W835 记的 12739 差 0.6%，属逐次波动，不是「逐项一致」）"),

 ("W839_ARCH_ENTRY.md",
  "门禁 **18 项全 PASS**",
  "门禁 **17 项全 PASS**"),

 ("W839_ARCH_ENTRY.md",
  "本轮新增 4 项，共 **18 项**",
  "本轮新增 4 项，共 **17 项**"),
]

ok = fail = 0
buffers = {}
for fn, old, new in EDITS:
    p = D + fn
    if p not in buffers:
        buffers[p] = io.open(p, encoding="utf-8").read()
    s = buffers[p]
    n = s.count(old)
    if n != 1:
        print("SKIP(%d) %-28s %s" % (n, fn, old[:46]))
        fail += 1
        continue
    buffers[p] = s.replace(old, new, 1)
    ok += 1
    print("ok      %-28s %s" % (fn, old[:46]))

print("\nmatched %d, skipped %d" % (ok, fail))
if APPLY:
    for p, s in buffers.items():
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("written:", len(buffers))
else:
    print("(dry-run; add --apply)")
