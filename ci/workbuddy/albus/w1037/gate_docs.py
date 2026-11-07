import io, shutil

# ---- ledger ----
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_w1037f")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B8工程", "P436",
    "四项报告第二次以「数字过期」的形式丢失：报告写 0 重启/0 停机而账本写 3 次/136 s ⇒ 新增 report_consistency 进硬门",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主 07:36：「每轮的四项报告你又丢了」）**：窗口跑完后 `reply.md` 开头那份四件套**仍写着「重启 0 次 / 0 分钟停机」**，"
    "而账本 `P434` 写的是三次重启、停机 136 秒。`report_lint` 只查字段在不在、`report_depth` 只查篇幅，"
    "**没有一道门比对「报告里的数」与「账本里的数」** ⇒ W1012「字段在、内容没了」的第三次复发，这次是数字过期。"
    "新增 `tools/report_consistency.py` 并接进 `round_close.py` 的 HARD：从 SNAPSHOT 取轮次 → 取该轮账本行的最大重启次数与最大停机秒数 → "
    "要求报告「三、本次落生产」段出现同样的数（负数自测：改回旧文案当场 FAIL 2 条）。四件套同时按窗口后现场重写"
    "（StartedAt 23:26:40Z、VRAM free 759,767,040 B、装机 1 次已还原）。",
    "P434", "KW:数字过期|report_consistency"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P436)")

# ---- W832 ----
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_w1037f")
s2 = io.open(P2, encoding="utf-8").read()
a = "**377 条 / 已结 294 / 78.0%**（W1037 校正"
b = "**378 条 / 已结 295 / 78.0%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)
ADD = """
**十三、四项报告第二次「丢」，这次是数字过期（`P436`）。**
窗口跑完后报告开头的四件套仍写着「重启 0 次 / 0 分钟停机」，而账本写的是三次重启、停机 136 秒。
`report_lint` 查字段在不在、`report_depth` 查篇幅，**没有一道门比对「报告里的数」与「账本里的数」**。
新增 `tools/report_consistency.py` 并接进 `round_close.py` 的 HARD：取该轮账本行的最大重启次数与最大停机秒数，
要求报告「三、本次落生产」段出现同样的数；把旧文案放回去当场 FAIL 2 条（负数自测通过）。
⇒ 硬门从 13 道变 **14 道**。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十三")

# ---- reply ----
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**377 条 / 已结 294 / 78.0%**（W1037 校正；本轮 +11：`P425`–`P435`）。"
b3 = "**378 条 / 已结 295 / 78.0%**（W1037 校正；本轮 +12：`P425`–`P436`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**14. 四项报告第二次丢，这次是「数字过期」，已变成门（`P436`）。**
窗口跑完后，本报告开头的四件套仍写着「重启 0 次 / 0 分钟停机」，账本 `P434` 写的是三次重启、停机 136 s——
`report_lint` 只查字段在不在、`report_depth` 只查篇幅，**没有一道门比对报告里的数与账本里的数**。
新增 `tools/report_consistency.py` 接进 `round_close.py` HARD：按 SNAPSHOT 轮次取账本的最大重启次数/停机秒数，
要求「三、本次落生产」段出现同样的数。把旧文案放回去 → 当场 **FAIL 2 条**（负数自测）。硬门 13 → **14 道**。
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +14")
