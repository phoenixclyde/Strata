#!/usr/bin/env python3
# W840-05 登记表：改状态 + 追加更正说明 + 新增 AUDIT13 两条 + 清掉空行
import io

P = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
raw = io.open(P, encoding="utf-8").read()
lines = raw.split("\n")
blank = [i + 1 for i, l in enumerate(lines) if l.strip() == "" and i < len(lines) - 1]
print("blank lines (non-tail):", blank)
lines = [l for l in lines if l.strip() != ""]
rows = [l.split("\t") for l in lines]
hdr, body = rows[0], rows[1:]
assert all(len(r) == 11 for r in body), [r[0] for r in body if len(r) != 11]

def row(i):
    for r in body:
        if r[0] == i:
            return r
    raise KeyError(i)

CHANGES = {
 "P210": ("UNRESOLVED", "AUDIT13：evidence 里「33 条 33 个 sha」应作 36/36，且 3 条仅 446/318/420 token 的样本被当作 512 计入表。"),
 "P211": ("UNRESOLVED", "AUDIT13：read 为 n=2 均值且含冷启动样本（同臂差 303 ms=7.4%，是臂间差 46 ms 的 6.6 倍）、decode 单轮 A→B 非 ABBA ⇒ 只能记「不可分辨」，不能记 CONFIRMED。"),
 "P213": ("PARTIAL", "AUDIT13：GDN_PP 从未单独测（`a08` 只给 GDN_HEAD）；且「0.029→0.045」是无效相加（两样本总体不同，0.0171 中 88% 来自单点）。GDN_HEAD 的位等价已由 md5 复核成立（EG.tsv=E0.tsv=fadf1889）。"),
 "P218": ("CORRECTED", "AUDIT13：可达面应为 24.19 ms（53.8%），不是 33 ms（73%）；按 30–50% 局部改善应为 −16%~−27%，不是 −5%~−10%。"),
 "P219": ("CONFIRMED", "AUDIT13：3.9× 应为 4.40×（116.5/26.5）。"),
 "P221": ("SUPERSEDED", "被 P222（五臂实测全负）取代；状态未及时更新。"),
 "P223": ("SUPERSEDED", "已被 P226 取代：现 head 9ac564f、ahead 10、11 文件 +243/−9（GitHub compare 权威）。"),
 "P224": ("CORRECTED", "AUDIT13：当时「入口生效、行为不变」归因错误——表根本没被调用（P226）。banner 来自测试件，引擎二进制里 grep=0。"),
}
for pid, (st, note) in CHANGES.items():
    r = row(pid)
    old = r[5]
    r[5] = st
    r[10] = r[10].rstrip() + " " + note
    print("%-5s %-16s -> %-12s %s" % (pid, old, st, note[:40]))

NEW = [
 ["P228", "AUDIT", "AUDIT13：审计 W832–W839（8 轮，此前审计链止于 W831）",
  "P0 3 条、P1 8 条、P2 6 条；撤回 3 条；文档 20 处就地修复", "audit", "FIXED", "—", "—", "P227",
  ("机械定范围：全文扫 deploy 下审计件，W833–W839 出现 0 次、W832 仅 1 次 ⇒ 待审 = W832–W839。"
   "两个对抗只读子 agent（A：W832–W834；B：W835–W839）+ 主会话回原始字节复核。"
   "P0-1 W832 把 36 条/36 sha 写成 33/33，且 3 条非 512 token 样本计入表（原始 jsonl 复核）。"
   "P0-2 W832 的停机条件写在 ms/win 上，而四臂 ms/win 配对差 +11.75/−7.24/−4.11/+2.53%、复本基线自身 +4.88% ⇒ 永不可能触发；"
   "关账结论仍成立（按主判据 tok/ms 与 6% 噪声底盘判 UNRESOLVED），但依据必须改写。"
   "P0-3 三处把「不可分辨」写成「无差异/CONFIRMED」：P211（read n=2 含冷样本）、P214（pool read1300 实为 3/3 同向）、P213（GDN_PP 未测）。"
   "P1 另有：W835 可达面 33ms/73% 应为 24.19/53.8%、收益 −5~−10% 应为 −16~−27%、3.9× 应为 4.40×；"
   "W836 find_dependency≠rocBLAS 进二进制、banner 来自测试件、+216/−9 为快照（现 +243/−9）；W839 第 10 个 commit 应为第 9、门禁 17 项不是 18。"
   "撤回 3 条（审计方自己也判错）：①「EG 臂开关没下发」——配置是 w833_klegdn.json，确实设了 GDN_HEAD=0，位等价成立；"
   "②「门禁假绿 BW_REFRESH_S / cudaStreamCreateWithPriority」——上游 main 两个词计数均为 0（GitHub raw 核）；"
   "③「97.4% 算错」——未四舍五入是 33.46/34.34=97.4%。"),
  "报告 deploy/AUDIT13_W832_W839.md；20 处文档修复；8 条 P 行改状态。"],
 ["P229", "OPEN", "GDN_PP 的数值代价从未单独测（P213 判 PARTIAL 的直接后果）",
  "要判需一次 KL 臂（STRATA_GDN_PP=0 对基线，n≥6 同位置）；在此之前不得写「GDN 组零债」",
  "measurement", "PENDING", "—", "—", "P213/P228",
  ("背景：`gfx906_tuned_env` 与 gfx1151 表都含 STRATA_GDN_PP=2，但它从未被单独关掉测过；"
   "W832 §4.4 把 GDN_HEAD 的位等价（EG.tsv=E0.tsv=fadf1889，md5 完全相同）扩写成「GDN_HEAD/GDN_PP 零债」。"
   "成本约 6 min/臂（本机 4.5 min 载入 + 1.5 min 采集），可与下一次 KL 门合并做。"),
  "未做。对外只能说「GDN_HEAD 位等价」。"],
]
for r in NEW:
    assert len(r) == 11
    if any(x[0] == r[0] for x in body):
        print(r[0], "exists")
    else:
        body.append(r)
        print(r[0], "added")

out = "\t".join(hdr) + "\n" + "\n".join("\t".join(r) for r in body) + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("rows:", len(body))
print("status dist:", {k: sum(1 for r in body if r[5] == k) for k in sorted({r[5] for r in body})})
