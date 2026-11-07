# -*- coding: utf-8 -*-
"""W986 整改：参数册 4 处 + 台账 2 行。"""
import io, time

TS = time.strftime("%Y-%m-%d %H:%M")

Q = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
rl = io.open(Q, encoding="utf-8").read().splitlines()
head, body = rl[0], rl[1:]
out = []
for l in body:
    c = l.split("\t")
    pid = c[0]
    if pid == "P65":
        c[5] = "CLOSED"
        c[10] = (c[10] if len(c) > 10 else "") + (
            " 【W986 已清 %s】从生产删除（env 9→8）；A/B（n=10）：decode 37.01（CV 5.84%%）/ TTFT 4.0533（CV 0.59%%）"
            "对删除前 37.37/4.0743 ⇒ 无变化，与「惰性」判断一致。" % TS)
        l = "\t".join(c)
    elif pid == "P10":
        c[3] = "auto:16384"
        c[10] = (c[10] if len(c) > 10 else "") + (" 【W986 更正 %s】册值原写 auto，生产实为 auto:16384（P131/P259 已实测该值）。" % TS)
        l = "\t".join(c)
    elif pid == "P107":
        c[3] = "/data/gfx906-rocblas-5.7.0.txt"
        c[10] = (c[10] if len(c) > 10 else "") + (" 【W986 更正 %s】册值原写 5.5，生产实际指向 5.7.0（P230 记为 5.7）。" % TS)
        l = "\t".join(c)
    elif pid == "P227":
        c[5] = "REJECTED"
        c[10] = (c[10] if len(c) > 10 else "") + (
            " 【W986 判否 %s】唯一可测的 auto 候选（`pcie_frac_auto`，去 `--pcie-frac` + `STRATA_PCIE_FRAC_DEFAULT=auto`）"
            "实测 decode +1.53%%（band 11.68%%）、TTFT −0.23%%（band 1.18%%）⇒ 不显著，已回退。其余候选仍是源码级未打开。" % TS)
        l = "\t".join(c)
    out.append(l)

extra = [
    "\t".join(["P256", "ENV", "STRATA_RESIDENT_HEADROOM_GIB", "(已删除)", "ram", "CLOSED", "-", "-", "-",
                "P65 的落地：W986 从生产移除，env 9→8",
                "**W986 清理（%s）**：A/B n=10 无差异；该 env 自 W785 去 `--resident-experts` 后即惰性。" % TS]),
    "\t".join(["P257", "CLI", "`pcie_frac_auto`（去 --pcie-frac + STRATA_PCIE_FRAC_DEFAULT=auto）", "已回退", "pcie", "REJECTED",
                "-", "-", "P227", "decode +1.53%%（band 11.68%%）/ TTFT −0.23%%（band 1.18%%）/ n=10",
                "**W986 判否（%s）**：见 P227 补注；回退后 pcie-frac 维持 0.20。" % TS]),
]
io.open(Q, "w", encoding="utf-8", newline="").write("\n".join([head] + out + extra) + "\n")
print("REGISTER: P65→CLOSED, P10/P107 值更正, P227→REJECTED, +P256/P257")

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows_add = [
    "\t".join(["B7配置旋钮", "P258", "删死参 `STRATA_RESIDENT_HEADROOM_GIB`（P65 惰性 env）", "W986", "count", "1", "1",
               "DONE", "**W986（%s）** 已从生产移除，env 9→8；n=10 decode 37.01 / TTFT 4.0533 对 37.37 / 4.0743 ⇒ 无变化。" % TS]),
    "\t".join(["B1参数轴", "P259x", "`pcie_frac_auto`（去 --pcie-frac + STRATA_PCIE_FRAC_DEFAULT=auto）", "W986", "count", "1", "1",
               "DONE_NEG", "**W986 判否（%s）** n=10：decode +1.53%%，TTFT −0.23%%，均在 2×CV 内 ⇒ 回退。P227 的 auto 候选至此关闭。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(lines + rows_add) + "\n")
print("PROGRESS: +2 行")
