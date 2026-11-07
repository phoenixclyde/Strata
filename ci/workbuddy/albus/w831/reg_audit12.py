# -*- coding: utf-8 -*-
"""登记 AUDIT12 的 P205–P208。"""
import io

P = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
s = io.open(P, encoding="utf-8").read()

rows = [
 ("P205", "INCIDENT", "§6.1 的 0.1.53 vs 0.1.54n A/B 两臂不同源：n 缺 W793/rocBLAS",
  "结论收窄：decode 0 回归 0 收益；read 三档不可比", "measurement", "CORRECTED",
  "—", "—", "P201/P195",
  "原始字节：`rocblas` 字符串 strата-0.1.53=3 / 0.1.54n=0 / 0.1.54n2=3；build-028.log 有 2 条 `rocblas_state_ ... not used`，"
  "build-028r.log 为 0。rocBLAS 打在 prefill 的 f16 GEMM 上（W830 §6 同镜像 ABBA：常数项 1190→915 ms）⇒ "
  "§6.1 里 read 的 −6.2/+3.7/+9.8% 混了'缺 W793'，不能判引擎版本；decode 走 GEMV 不受影响，结论成立。",
  "已改 W828 §6.1。今后 A/B 必须在文档写明两臂代码来源。"),

 ("P206", "DATA", "模型层数 = 48（原文多处写 60）",
  "每窗口专家读取 3.2 GB / ~300 GB/s（非 3.9 GB / 375–400）", "data", "CORRECTED",
  "—", "—", "P197/P203",
  "`data/packs/ud-q4_k_xl/native_experts.txt`：48 个 layer（0..47），每层 512 专家，48×512=24576 与 W829 §0 的 24576 实例一致；"
  "专家总字节 77,017,907,200。受影响：§6.14 的 3.9 GB→3.2 GB、375–400→~300 GB/s、§6.15 并集 94→75 GB、"
  "§6.16 搬运 72 GB/15 GB/s→52 GB/11 GB/s（更正后与 W829 的 12 GB/s 实测相符，原 15 GB/s 超过 PCIe 3.0 x16 上限）。",
  "已改。Q3 的 +6% 不受影响（走 23.4%×25%）。"),

 ("P207", "DATA", "gfx1151 exact 表是 19 项（原文 15），且我们已手动开 2 项",
  "19 项；生产 env 已含 GDN_HEAD=1 / GDN_PP=2", "data", "CORRECTED",
  "—", "—", "P191/P203",
  "`src/core/arch_defaults.cpp:58-90` 逐条数得 19 项（GDN_HEAD…SH_STREAM），段首注释逐字 `Exact (bitwise) on Aurora`。"
  "生产 14 个 env 里 `STRATA_GDN_HEAD=1`、`STRATA_GDN_PP=2` 本就在 ⇒ '一项都没开' 不成立，"
  "准确说法是'arch 默认表在 gfx906 上不生效，19 项里我们手动开了 2 项'。",
  "已改 §6.8 标题与正文。'AMD 优化轴已穷尽' 的覆盖证据仍不足（六类只覆盖 20/29）。"),

 ("P208", "MEASUREMENT", "判据列必须与实际排序列一致；A/B 必须标两臂代码来源",
  "两条硬规矩（AUDIT12 新增）", "measurement", "CONFIRMED",
  "—", "—", "P200/P205",
  "§6.11 声明判据是 tokens/window ÷ ms/window，表里给的却是 wall tok/s，两列差 1.2–3.7% 与效应同量级；"
  "按声明判据 th=47.73 vs 基线 45.38=+5.2%，与'平地'相反。另 §6.16 拿拟合斜率 1.32 比实测区间斜率 1.69（同口径应为 1.64）。"
  "规矩：①判据写哪一列就只许用哪一列排序；②A/B 必须写明两臂 exe/构建树/是否含全部本地补丁；"
  "③算出的带宽不得超过链路理论上限；④层数/字节等分母必须引可复现清单。",
  "采纳。已写入 AUDIT12 §8/§9。"),
]

for r in rows:
    if ("\n" + r[0] + "\t") in ("\n" + s):
        print(r[0], "exists")
        continue
    s += "\t".join(r) + "\n"
    print(r[0], "added")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("rows", len([l for l in s.split("\n") if l.strip()]))
