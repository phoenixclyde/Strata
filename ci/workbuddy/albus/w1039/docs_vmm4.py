import io

P = "deploy/PROGRESS.tsv"
row = ("B1参数轴", "P478",
       "`kvg.on` 与「弹性 K/V 已开」是**两组**条件：前者为假时 `kvg_ensure` 不增长却返回成功，长请求会踩未映射地址 ⇒ 窗口必须先验一行日志再发长请求",
       "W1039", "count", "1", "1", "DONE",
       "**源码**：`generate.cpp:6714` 用十一项与关系打开弹性 K/V；`kvg_start`（`:9961`）**另加** `xcache.vmm_range() != nullptr && d_res != nullptr && !host_res.empty() && srcp != nullptr && top > kvg.floor`。"
       "两者可以不同时为真，而 `kvg_ensure`（`:9978`）的开头是 `if (!kvg.on || cells <= kvg.cells) return true;` ——**`kvg.on` 为假时它「成功」但不增长**，调用方于是照常使用超出已映射范围的 cell。"
       "**判据（机械）**：`kvg_start` 成功时会打印 `strata generate: elastic K/V: N of M cells in VRAM ...`；为假时 `generate.cpp:6711` 会打印 `--kv-grow is off (...)`。"
       "⇒ 窗口脚本加硬门：健康检查后 `grep -aq \"elastic K/V:\"` 不成立就 **在发任何长请求之前中止并还原**。"
       "这条与 `P465`（探针先证可见性）同一族：**别把「我以为它开了」当成「它开了」**。",
       "P474;P477", "KW:kvg.on|静默失效|硬门")

lines = io.open(P, encoding="utf-8").read().splitlines()
assert len(row) == 11
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended P478")

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
r = r.replace("**420 条 / 已结 333 / 79.3%**（本轮 +33：`P445`–`P477`）",
              "**421 条 / 已结 334 / 79.3%**（本轮 +34：`P445`–`P478`）", 1)
para = """
**窗口脚本里加了一道硬门（`P478`）**：`kvg.on`（`generate.cpp:9961`）比「弹性 K/V 已开」那十一项**多**五个条件（`xcache.vmm_range()`、`d_res`、`host_res`、`srcp`、`top > floor`）。两者不同时为真时，`kvg_ensure` 的开头 `if (!kvg.on || cells <= kvg.cells) return true;` 会**「成功」但不增长**，调用方照常使用未映射的 cell。所以脚本在健康检查之后先 `grep -aq "elastic K/V:"`，不成立就**在发任何长请求之前中止并还原**——这和 `P465`（探针先证可见性再开窗）是同一条纪律。
"""
j = r.find("**外部核对反而给出一条更值钱的教训")
assert j > 0
r = r[:j] + para.lstrip("\n") + "\n" + r[j:]
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: P478 paragraph + denom")

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**420 条 / 已结 333 / 79.3%**", "**421 条 / 已结 334 / 79.3%**", 1)
a = "- **失败模式**：trim 不成 ⇒ `ERR the K/V could not give its VRAM back to the expert cache` 并退进程（窗口必看）。"
b = a + "\n- **静默失效门（`P478`）**：`kvg.on` 为假时 `kvg_ensure` 不增长却返回成功 ⇒ 脚本先 `grep -aq \"elastic K/V:\"`，不成立就在发长请求前中止还原。"
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: P478 line + denom")
