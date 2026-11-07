import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1015（报告只有一份；R94 的金标不存在；`host grouping` 的 91 ms 是复用等待）

**1. 报告规矩（机主第 N 次点这一条）。** W1013/W1014 两轮的文件版都过了门（`report_lint` 12 字段、
`report_depth` 阈值），但**聊天里发的是压缩版**：8 行表、没有 3a/3b 明细、M/P/Q 并成一行。这不是格式问题，
是**同一份报告存在两个副本、而门只看见其中一个**——和 W1003 的「W832 两份、没人比」是同一个病。

写死的规矩：

- 报告的**唯一副本**是 `albus/<轮次>/reply.md`；聊天里贴的就是它的**全文**，不改写、不删行、不并段。
- `round_close.py --post` 在 PASS 之后打印 `POST: md5=<…> chars=<…>` 再打印全文 ⇒ 贴的时候连这一行一起贴，
  两边对得上才算发过。

**2. R94 的「对金标 KL/top-1」在这台机器上做不了，原因是缺件，不是缺方法。**
`data/quant_quality/v1/` 里只有 5 段文本与 `set.ids.json`（已分词，948 KB 级），**没有 `REF.tsv`**；
而 `quant_quality.py` 的参照臂要求 Q8_0 pack，我们的 pack 是 `ud-q4_k_xl`（`native_experts.txt` 里只有
**专家**是 Q4_K/Q5_K/Q5_1/Q8_0，dense 部分不是 Q8_0）⇒ **绝对门没有参照物**。

改成**相对门**（这也是 W806/W807 一直在用的口径）：

> 每一条改比特的候选，与**现役配置**在同一 prompt 集上各跑一次 teacher-forced LOGPOS，比 KL 与 top-1；
> 判据 KL ≤ **0.0139**（W806 提示侧标尺）、top-1 ≥ **99%**；同配置两次跑作底噪（W807 已证解码侧底噪 0）。
> 门的目的从「证明比 Q8_0 好」变成「证明这次采纳不比现役更差」，这与我们实际的决策面一致。

需要独占 GPU（`quant_quality run` 自起引擎）：停机约 4–6 分钟，本轮**没做**（见下条边界）。

**3. R95 的 91 ms 归因有了，而且**不是**「把建组计划挪到 issuer 线程」。**
读 `prefill.cpp:4655` 起的 host 建组段：

- `:4663` — `m.up_ring.d2h_sync(m.ids_host.data(), m.ids, (size_t) T * K * 4, m.cs)`，**同步** D2H；
- `:4656-4657` 的注释逐字：*"(the sync below also orders this layer's writes of slot/src/bounds after the
  previous layer's kernels that read them)"* —— 这个 sync **同时承担缓冲复用排序**；
- 算术：`T*K*4` = 2084×8×4 = **66 KB/层**，×48 层 = **3.2 MB**，PCIe D2H 约 **0.5 ms**；而相位里是 **91 ms**。

⇒ **91 ms 不是拷贝，也不是建表（T*K 的直方图是百万级整数操作，微秒级），是「等上一层把 slot/src/bounds
读完」的停顿**。所以 W1013/W1014 里写的机制（"把建组挪到 issuer 线程"）是**错的**：搬线程不解决复用冲突。
真正的解法是**双缓冲**（`ids/slot/src/bounds` 各开两份、按层奇偶交替），让本层的 host 写不再等上一层读完；
上限 2.85%，`busy/phase` 事件实验（`P309`）仍是前置，因为它要验证"等"确实占满这 91 ms。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1015" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P329", "报告唯一副本：`albus/<轮>/reply.md`，聊天贴全文；`round_close --post` 打 md5+字符数", "W1015", "DONE",
  "**W1015 立**：W1013/W1014 文件版过门（12 字段 + depth 阈值）但聊天版是压缩版（8 行、无 3a/3b）⇒ 同一份报告两个副本、门只看见一个，"
  "与 W1003「W832 两份没人比」同源。规矩：唯一副本 + `--post` 打印 `POST: md5=… chars=…` 再打全文，连校验头一起贴。",
  "albus/w1002/round_close.py"),
 ("B6判定探针", "P330", "R94 金标不可得：无 `REF.tsv`、无 Q8_0 pack ⇒ 改「相对门」（两臂 LOGPOS，KL≤0.0139 / top-1≥99%）", "W1015", "DONE_NEG",
  "**W1015 立**：`data/quant_quality/v1/` 只有 5 段文本 + `set.ids.json`，**无 REF.tsv**；`quant_quality.py` 的参照臂要 Q8_0 pack，而我们是 `ud-q4_k_xl`"
  "（`native_experts.txt` 里 Q8_0 只出现在**专家**的 d_type，dense 不是）⇒ 绝对门缺参照物。改相对门：候选 vs 现役，teacher-forced LOGPOS，KL≤0.0139、top-1≥99%；同配置两次跑作底噪。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1015"),
 ("B6判定探针", "P331", "`host grouping` 91 ms 是缓冲复用等待，不是建表也不是拷贝 ⇒ 解法是双缓冲，不是搬线程", "W1015", "OPEN",
  "**W1015 立**：`prefill.cpp:4663` 是 `d2h_sync`（T*K*4 = 66 KB/层，48 层 3.2 MB ≈ 0.5 ms），`:4656-4657` 注释逐字说该 sync 同时排序「本层对 slot/src/bounds 的写 vs 上一层读」"
  "⇒ 91 ms 是等上一层读完的停顿。**更正** W1013/W1014 的「把建组挪 issuer 线程」：搬线程不解决复用冲突，正解是 `ids/slot/src/bounds` 各两份按层奇偶双缓冲；"
  "上限 2.85%，前置 `P309` 的 busy/phase 事件确认「等」占满整段。",
  "src/prefill/prefill.cpp"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID, ST, NOTE = head.index("id"), head.index("status"), head.index("note")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]

for i, l in enumerate(lines):
    if l.count("\t") < 9 or l.startswith("#"):
        continue
    c = l.split("\t")
    if c[ID] == "R95":
        c[NOTE] = ("**W1015 更正机制**：91 ms 不是建表/拷贝（3.2 MB ≈ 0.5 ms），是 `prefill.cpp:4663` 的 `d2h_sync` 同时承担的"
                   "「本层写 vs 上一层读」缓冲复用排序（`:4656-4657` 注释逐字）⇒ 解法=双缓冲，不是把建组挪到 issuer 线程；"
                   "前置 `P309` 事件实验（`P331`）。") + " " + c[NOTE]
        lines[i] = "\t".join(c)
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows + R95 note" % len(add))
