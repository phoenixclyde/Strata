import io

P = "deploy/PROGRESS.tsv"
row = ("B5本机缺口", "R105",
       "把 93 处 `STRATA_HIP_GFX906` 逐条分成三类（硬件事实 / 撰写时的假设 / 历史 workaround），把「gfx906 少掉的能力」变成一张可核清单——VMM 那条就是靠这个办法挖出来的",
       "W1039", "count", "1", "1", "OPEN",
       "**触发**：`vmm.cpp:167` 的排除是「假设」，不是硬件事实（`P472`），探针 1 秒就推翻了它。同一形状的条件在本树里有 **93 处**，其中「��� HIP、但显式排除 gfx906」这一子集才是能力缺口，已点名："
       "`core/mtp.cpp:486`（生产在用 `--mtp /data/mtp/rt`）、`core/verify.cpp:1213`、`program/generate.cpp:3078` 与 `:3371`、`prefill/prefill.cpp:2871`、`core/vmm.cpp:158/167`（已处理）。"
       "**判据**：每一处先回答三问——① 它排除的是**硬件能力**还是**某个 API 不存在**？② 有没有**运行时**判据可以替代（有就说明编译期排除是多余的，如 VMM 的属性检查）？③ 若真不能替代，缺的功能对生产参数面是否可达？"
       "**方法论已定**：凡能力判定，一律「源码条件 → 独立探针实测 → 只改条件不改语义 → 二进制变了才算改到」（`P472`/`P473`）。**零停机**：读码 + 探针，1 秒 GPU/次。"
       "**产出**：`albus/w1039/GFX906_GATES.md`（清单表：位置 / 排除什么 / 三类判定 / 探针方案 / 预期收益）。",
       "P472;P475", "KW:93 处|硬件事实|GFX906_GATES")

lines = io.open(P, encoding="utf-8").read().splitlines()
assert len(row) == 11
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended R105")

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
a = "**唯一队列** | **R104（进行中"
assert a in p
p = p.replace("→ ~~`R103`（attn 一支结案：本季不可测）~~",
              "→ **R105（新，`P479`：93 处 gfx906 能力门的分类清单，零停机）** → ~~`R103`~~", 1)
p = p.replace("**421 条 / 已结 334 / 79.3%**", "**422 条 / 已结 335 / 79.3%**", 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: §0.1 queue += R105, denom -> 422/335")

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
r = r.replace("**421 条 / 已结 334 / 79.3%**（本轮 +34：`P445`–`P478`）",
              "**422 条 / 已结 335 / 79.3%**（本轮 +35：`P445`–`P479`）", 1)
r = r.replace("队列：`R104`（`--kv-grow`）→ ~~`R103`~~",
              "队列：`R104`（`--kv-grow`）→ `R105`（93 处 gfx906 能力门分类）→ ~~`R103`~~", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: §四 += R105")
