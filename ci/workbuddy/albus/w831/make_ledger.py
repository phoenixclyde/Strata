# -*- coding: utf-8 -*-
"""从 AUDIT12 报告表格机械生成台账 AUDIT_LEDGER.tsv，并生成审计链索引 AUDIT_INDEX.md。"""
import io, os, re

DEP = "D:/workbuddy_space/strata_ws/deploy/"
RPT = DEP + "AUDIT12_W826_W831.md"
s = io.open(RPT, encoding="utf-8").read()

# ---------- 解析 P0（### P0-x · 标题） ----------
P0_LOC = {"P0-1": "W828:137-149", "P0-2": "W828 §6.15/§6.16", "P0-3": "W830:13"}
p0 = []
for m in re.finditer(r"^### (P0-\d) · (.+)$", s, re.M):
    pid, title = m.group(1), m.group(2).strip()
    p0.append((pid, title))

# ---------- 解析 P1 / P2 表 ----------
def rows_of(section_header, ncols):
    i = s.index(section_header)
    j = s.find("\n## ", i + 3)
    body = s[i: j if j > 0 else len(s)]
    out = []
    for line in body.split("\n"):
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != ncols:
            continue
        if not cells[0].isdigit():
            continue
        out.append(cells)
    return out

p1 = rows_of("## 3 P1", 4)   # # 位置 问题 复核结果
p2 = rows_of("## 4 P2", 3)   # # 位置 问题

# ---------- 处置状态 ----------
DISPO = {
 "P0-1": ("正文已收窄结论 + 顶部横幅", "FIXED"),
 "P0-2": ("落地口径按 n2 重算（1.6/4.9/12.2 s）+ 横幅", "FIXED"),
 "P0-3": ("代码由 W831 补回；W830 判定已更正；门禁换标记", "FIXED"),
 "P1-3": ("文档改为「5 项」；另 3 项仍未测", "FIXED_TEXT / OPEN_MEASURE"),
 "P1-7": ("补记同 harness 对照臂（1206 ms + 1.317）", "FIXED"),
 "P2-7": ("标注不可复现（third_party 2832；2768/2773）", "FIXED"),
}
DEFAULT = ("已就地更正（正文）", "FIXED")

def esc(x):
    return x.replace("\t", " ").replace("\n", " ")

lines = ["id\taudit\tsev\tdoc\tloc\tfinding\tdisposition\tstatus"]

for pid, title in p0:
    d, st = DISPO.get(pid, DEFAULT)
    lines.append("\t".join([f"A12-{pid}", "AUDIT12", "P0", "W826-W831",
                            P0_LOC.get(pid, ""), esc(title), esc(d), st]))

for n, loc, issue, check in p1:
    pid = f"P1-{n}"
    d, st = DISPO.get(pid, DEFAULT)
    lines.append("\t".join([f"A12-{pid}", "AUDIT12", "P1", "W826-W831", esc(loc),
                            esc(issue), esc(d + "｜复核：" + check[:120]), st]))

for n, loc, issue in p2:
    pid = f"P2-{n}"
    d, st = DISPO.get(pid, DEFAULT)
    lines.append("\t".join([f"A12-{pid}", "AUDIT12", "P2", "W826-W831", esc(loc),
                            esc(issue), esc(d), st]))

io.open(DEP + "AUDIT_LEDGER.tsv", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("ledger rows:", len(lines) - 1, "  P0=", len(p0), "P1=", len(p1), "P2=", len(p2))

# ---------- 审计链索引 ----------
CHAIN = [
 ("AUDIT6",  "W776–W785", "0", "5", "5", "-",  "AUDIT6_W776_W785.md"),
 ("AUDIT7",  "W786–W788 + R5", "0", "4", "7", "-", "AUDIT7_W786_W788.md"),
 ("AUDIT8",  "W789–W795", "0", "4", "7", "-",  "AUDIT8_W789_W795.md"),
 ("AUDIT9",  "W796–W800", "0", "5", "7", "-",  "AUDIT9_W796_W800.md"),
 ("AUDIT10", "W801–W809", "0", "2", "6", "3",  "AUDIT10_W801_W809.md"),
 ("AUDIT11", "W810–W825", "3", "12", "8", "-", "AUDIT11_W810_W825.md"),
 ("AUDIT12", "W826–W831", "3", "11", "12", "-", "AUDIT12_W826_W831.md"),
]
tot = [sum(int(r[i]) for r in CHAIN) for i in (2, 3, 4)]

idx = []
idx.append("# 审计索引（AUDIT6 → AUDIT12）\n")
idx.append("> 本表由 `albus/w831/make_ledger.py` 从各审计件的「总判」行机械提取，不靠记忆。")
idx.append("> 下一轮**待审区间**的判定方法：跑 `albus/w831/audit12_scope.py`（全文比对），不要靠这张表往前推。\n")
idx.append("| 审计件 | 覆盖轮次 | P0 | P1 | P2 | P3 | 文件 |")
idx.append("|---|---|---:|---:|---:|---:|---|")
for a, rng, p0n, p1n, p2n, p3n, fn in CHAIN:
    idx.append(f"| {a} | {rng} | {p0n} | {p1n} | {p2n} | {p3n} | `{fn}` |")
idx.append(f"| **合计** | W776–W831 | **{tot[0]}** | **{tot[1]}** | **{tot[2]}** | **{sum(int(r[5]) for r in CHAIN if r[5]!='-')}** | — |")
idx.append("")
idx.append("## 台账\n")
idx.append("- `AUDIT_LEDGER.tsv` —— AUDIT12 的 26 条结论逐条登记（id / 严重度 / 位置 / 问题 / 处置 / 状态），")
idx.append("  由报告表格**解析生成**，改报告后重跑脚本即可同步，不手抄。")
idx.append("")
idx.append("## 仍未结清的（跨轮，需实测）\n")
idx.append("| 项 | 出处 | 状态 |")
idx.append("|---|---|---|")
idx.append("| `--spec-min-p` / `--pool-workers` 的效应（0.4%/0.7%）低于自述 12–16% 漂移 | W829 §5.2、AUDIT12 §8-1 | **未判**，不应写作\"最优\" |")
idx.append("| 数值债还差 3 项（`MMQ_KQ`、`GDN_HEAD`、`GDN_PP` 未翻） | W828 §6.10、AUDIT12 P1-3 | 文档已改，**测量未做** |")
idx.append("| §6.8 的 AMD 开关覆盖面：六类只覆盖 20/29 个未设变量 | W828 §6.8、AUDIT12 P1-2 | **覆盖不足**，\"已穷尽\"不成立 |")
idx.append("| 宽窗口 bit-exact 从未验（只编译 + batch16 起不来） | W829 L79 | **未做** |")
idx.append("")

io.open(DEP + "AUDIT_INDEX.md", "w", encoding="utf-8", newline="\n").write("\n".join(idx) + "\n")
print("index written; totals P0/P1/P2 =", tot)
