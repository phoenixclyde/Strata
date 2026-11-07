import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

# §0.1: ROCm 也是"唯一来源"该管的事实 —— 之前只写了 llama.cpp 的 pin
ROW = ("| **ROCm（容器内）** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；"
       "clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858`；rocprofv3 1.3.5 | "
       "`docker exec strata166-407 …`；三套编号互不相等（自建 gfx906 树），写「ROCm 7.x」等于没写 |\n")
if "**ROCm（容器内）**" not in s:
    anchor = "| **依赖 pin（llama.cpp）** |"
    assert anchor in s
    s = s.replace(anchor, ROW + anchor, 1)

BLOCK = '''
### 回写 · W1025（四项报告：把 ROCm 与 llama.cpp 变成字段，并把这套规矩做成独立技能）

机主三问：①W1024 的结论落权威方案了吗？②四项报告里要**明确指出**生产容器的 ROCm 与 llama.cpp 版本；
③把这四项报告落成一个完整的单独技能。

**一、落在哪（grep 得到，不是"我记得写了"）**

| 内容 | 落点 |
|---|---|
| W1024 全部结论 | `W832` §6.5「回写 · W1024」（`:1961` 起） |
| 三个编号 | `P357`（容器内版本）/ `P358`（rebase 复核）/ `P359`（b12169 分派层，OPEN） |
| 依赖 pin | §0.1「依赖 pin（llama.cpp）」行（`:26`） |
| **本轮新增** | §0.1「**ROCm（容器内）**」行 + §6.5 本块 + `P360`/`P361` |

**二、报告门从 12 项变 14 项，两条是行级**

`tools/report_lint.py` 原来全是**全文级**匹配 —— 正文里提到 `llama.cpp` 就算过，这正好让"表里没有、正文里有"
蒙混过关。新增：

| 字段 | 判据 | 为什么是行级 |
|---|---|---|
| `F9 ROCm 版本（容器内）` | 「一、生产容器」段内**某一行**同时含 `ROCm` + 版本号 + `HIP`/`hipconfig`/`.info/version` | 这台机器三套 ROCm 编号（10.1.0 / 7.14.0-gfx906 / 7.16.26323）互不相等，全文匹配会把任何一个当成答案 |
| `F10 llama.cpp 版本（容器内）` | 同一段内某一行同时含 `llama.cpp` + `bNNNNN` + **40 位 sha** | 7 位前缀不可校验；树 hash 才能证明"哪棵树" |

实测有效性：补行前 `REPORT_LINT: FAIL (2)`（"表内 0 行"），补行后 `PASS (14 fields)`；
`ci/round_gate.py` 的正样本也加了这两行，`ROUND_GATE: PASS`（7/7 + 4/4 + 两道自测）。

**三、技能：`strata-report`**

`~/.workbuddy/skills/strata-report/SKILL.md` —— 独立于 `strata-release`（那个负责"做一版"，这个负责"写清楚"）。
内容：四项结构、**十字段逐条取值命令**（含容器内 `cat /opt/rocm/.info/version`、`hipconfig --version`、
`find … md5sum | md5sum`）、3a/3b 要求、正文 ≥1500 字符与 ≥4 `file:line`、唯一副本 + `--post` 校验头、
四道门、六条真实失败模式、与 release 技能的分工。

**四、判据再收紧一条**

字段必须能在**容器内**取到：`ROCm` 认 `.info/version` + `hipconfig`，`llama.cpp` 认 `BUILD-IMAGE.json` + 树 hash。
宿主版本、镜像台账、上一轮报告的数字都不算 —— 那三处都曾经对不上。
'''
if "回写 · W1025" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK

s = s.replace("| 进度分母 | **289 条 / 已结 209 / 72.3%** |", "| 进度分母 | **291 条 / 已结 211 / 72.5%** |", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P360",
  "report_lint 12→14 项：F9 ROCm / F10 llama.cpp 改为行级且限定在「一、生产容器」段",
  "W1025", "DONE",
  "**W1025 立**：老门全是全文级，正文提到就算过。新增两条行级判据——`F9` 要一行同时含 `ROCm`+版本+`HIP`/`hipconfig`/`.info/version`，"
  "`F10` 要一行同时含 `llama.cpp`+`bNNNNN`+40 位 sha，且搜索范围限定在「一、生产容器」段（`re.split(r'\\*\\*二、|## 二、')` 之前）。"
  "实测：补行前 FAIL(2)（表内 0 行），补行后 PASS(14 fields)；`ci/round_gate.py` 正样本同步加两行，ROUND_GATE PASS。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1025"),
 ("B8工程", "P361",
  "四项报告成独立技能 `strata-report`（四项结构 + 十字段取值命令 + 门 + 失败模式）",
  "W1025", "DONE",
  "**W1025 立**：`~/.workbuddy/skills/strata-report/SKILL.md`，与 `strata-release`（做一版）分工：本技能只管把这一版写清楚。"
  "含十字段逐条命令（容器内 `cat /opt/rocm/.info/version`、`hipconfig --version`、`find|md5sum|md5sum`）、3a≥19 flag / 3b≥8 env、"
  "正文 ≥1500 字符与 ≥4 `file:line`、唯一副本 + `round_close --post` 校验头、四道门、六条真实失败模式。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1025"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
ID = lines[hi].split("\t").index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
