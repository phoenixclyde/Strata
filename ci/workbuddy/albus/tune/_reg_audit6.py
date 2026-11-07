# -*- coding: utf-8 -*-
"""AUDIT6 整改：P84/P78/P65 note 修正 + 新增 P90（审计结论与三条硬规则）。"""
import io, time, shutil

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_audit6_" + time.strftime("%Y%m%d_%H%M%S"))

P90 = ("【AUDIT6 2026-10-25 审计结论】范围：AUDIT5 之后的 W776-W785 十轮 + 三次生产变更（0.2.3/0.2.4/去 resident）+ "
       "一次本机校准 + 12 组 env 扫描。**P0=0，P1=5，P2=5**。P1：①三轮（W777:196/W780:101/W784:159）把 --kv-grow 当可开，"
       "引用门时漏了 `vmm_available()`，而 gfx906 构建该函数恒 false（vmm.cpp:299-303）=> 实测三臂 slots 恒 9901；"
       "②P84 note 曾写'仅 F1-F5 保留'，而 F1（gr_up75/gr_down_v3 溢出）是死代码、F2 不可达；③MEMORY §4 仍写 'P66/P65 采纳'，与现行相反；"
       "④P78 的 'decode +2~5%' 口径被 P88 否掉（5 runs 摆动 ±10%），prompt 部分 +0.6% 仍成立；"
       "⑤W783 的 A1 仍按 decode>=+2% 立项，而 E0 证明注意力整族只占 6.7%。"
       "P2：W785 单位错（MiB 当 GB，差 7%）、22.84 应为 22.3 GiB、816 vs 832 B/cell、MEMORY 槽位 9761 归属错、verify 29->28 系 P66 行消失（FAIL 仍 0）。"
       "**三条硬规则（今后强制）**：A 引用门必须引整条谓词并在运行期用引擎自己的 off 日志复核；"
       "B 内核优化前先证'符号在二进制 + 在 dispatch 路径 + 再谈资源数'（否则优化的是死代码）；"
       "C decode 结论必须带接受率与 runs 数（>=10 或交错 A/B），<5% 级只认阶段 ms。"
       "详见 `deploy/AUDIT6_W776_W785.md`。")

rows = io.open(REG, encoding="utf-8-sig").read().splitlines()
out = []
for ln in rows:
    f = ln.split("\t")
    if len(f) > 10 and f[0] == "P84":
        f[10] = "收口：FA/MoE/topk/GEMV/llama.cpp 全线关闭；F1 撤销(死代码)、F2 不可达(无 VMM)，保留项见 W785/P90"
        ln = "\t".join(f)
    elif len(f) > 10 and f[0] == "P78":
        f[10] = "采纳：三档 prompt 一致 +0.6~0.67%；**decode +2~5% 部分未定**（P88：5 runs 摆动 ±10%，待 >=10 runs 或阶段 ms 重测）；槽 9732->9901"
        ln = "\t".join(f)
    elif len(f) > 10 and f[0] == "P65":
        f[10] = "采纳(历史上)：只被 resident 逻辑读取；W785 起 --resident-experts 已去掉 => 本 env 惰性（配着但不生效），下次动 config 时一并清理"
        ln = "\t".join(f)
    out.append(ln)

out = [ln for ln in out if not ln.startswith("P90\t")]
out.append("\t".join(["P90", "REF", "AUDIT6（W776-W785 审计）", "P0=0/P1=5/P2=5", "audit", "REFERENCE",
                      "-", "-", "-", P90, "三条硬规则：门引全谓词/先证内核在跑/decode 带接受率"]))
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows:", len(out))
