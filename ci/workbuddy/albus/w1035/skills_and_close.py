"""W1035 第 13 段：把可复用件落成独立技能 + 落账 + 方案回写 + 记忆。

一次落盘，单次执行（避免长内联被本机杀毒掐）。
所有写入前先备份；禁同一表达式里 read + open。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"
TAG = "W1035"


def backup(p):
    b = p + ".bak_w1035e"
    if not os.path.exists(b):
        shutil.copyfile(p, b)
    return b


SEC = """
**13. 把可复用的部分落成 4 个独立技能（本轮唯一新增的"资产"，不是分析）。**
判据不是"我做过"，而是三条同时成立：① 有**独立触发条件**（机主的一句话就能命中）；② 含**不可外推的判据**（换个模型/机器就会错的经验）；③ **会再被用到**。按这三条筛，本轮的 11 个交付件里只有 4 个过关：

| 新技能 | 触发（机主会怎么说） | 核心判据 | 参考实现（md5 已钉） |
|---|---|---|---|
| `workbuddy-round-gate-hooks` | 「规矩总是漏」「别再靠你记得」「装个钩子让我信」 | 钩子要看**这一回合改了什么文件**并跑真门，不是看消息里有没有四段标题；必须 fail-open | `stop_guard.py` `2f4701eb…` · `round_mark.py` `45940db8…` · `round_ledger.py` `7a547988…` |
| `strata-deploy-evidence-gate` | 「凭什么能落生产」「谁决定装不装」 | 六条 D1–D6，缺一条即 REFUSE；**分支保护只挡合并不挡直推**，门要设在装机前 | `deploy_gate.py` `4d9ea7e4…` |
| `engine-io-attribution` | 「以前没这种读盘」「现在一直有 X MB/s」 | 五步法（空闲基线→rchar vs read_bytes→smaps 钉文件→驻留率→冷热对照→时间对账）；单次观测+巧合 ≠ 因果 | `io_who.py` `f1cca754…` · `measure_req.py` `a0ad8208…` · `attr_req.py` `09e42d67…` |
| `strata-quant-quality-gate` | 「这版数值一样吗」「D4 缺证据」 | 三臂含**自一致地板**；`max|Δlogit|=0` 优先于 KL；混合树不能归因单补丁 | `w1035_c_run.sh` `f13f3217…` · `cmp_extra.py` `2831b89f…` |

**判定不建的三个（写清理由，防下轮重开）**：`ci_probe.py`（六条触发条件已验完，属一次性结论，留证据件即可）、`mmq_pad_check.py`（形状相关，换引擎/换卡即失效，写成了技能会误导）、`inventory.py`（编号/规矩清单，账本与门已覆盖）。另外 **`strata-release` 与 `strata-report` 已存在，不新建同类**——只在 `strata-deploy-evidence-gate` 里写明分工：`release` 管「怎么装」，本技能管「凭什么允许装」。

**验证（都做了，不是声明）**：`quick_validate.py` **4/4 `Skill is valid!`**；技能里钉的 **7 个脚本 md5 与磁盘逐一比对，0 drift**；实操加载 `engine-io-attribution` **即时返回全文**——说明技能与 `settings.json` 不同，**热加载即可用、不需要重启**。踩到的一个校验规则：`description` **不许含尖括号**，`/proc/<pid>/io` 这类写法会直接被拒，改成 `/proc/PID/io` 并压成单行才过。

**边界（必须同时说）**：技能是**知识 + 流程**，它让下一次不必重新推导；它**不是门**，不会阻断任何操作。门的形态仍是 `round_close` / `deploy_gate` / `Stop` 钩子。把技能当门用，等于把"记得加载"换成"记得加载技能"，还是靠自觉。
"""

ROW = ("B8工程\tP415\t把可复用件落成 4 个独立技能（钩子/装机门/IO归因/数值门），含判定不建的 3 项\tW1035\t"
       "count\t1\t1\tDONE\t"
       "**W1035 立**：判据三条（独立触发 / 不可外推的判据 / 会再用），过关 4 个——"
       "`workbuddy-round-gate-hooks`（钩子强制，含四个坑：settings 启动时读、中文 JSON 乱码、"
       "标记大小写致严格分支永不进入、缺字段时 fail-closed 卡死；须 fail-open）、"
       "`strata-deploy-evidence-gate`（D1–D6 + deploy.sh 3.5/8；附三条边界：Actions 只静态、"
       "分支保护只挡合并不挡直推、pre-push 才是唯一硬拦）、"
       "`engine-io-attribution`（五步法：空闲基线→rchar vs read_bytes→smaps 钉文件→驻留率→冷热对照→"
       "requests×MB/uptime 对账；五个坑含 docker exec 的 /proc 不是引擎的）、"
       "`strata-quant-quality-gate`（三臂含自一致地板；max|Δlogit|=0 优先；混合树不归因单补丁）。"
       "**不建 3 个并写明理由**：ci_probe（一次性）、mmq_pad_check（形状相关会误导）、inventory（已有覆盖）；"
       "`strata-release`/`strata-report` 已存在，不新建同类，只写清分工。"
       "**验证**：quick_validate 4/4 valid；技能内钉的 7 个脚本 md5 与磁盘比对 0 drift；"
       "实测技能**热加载即用**（不需重启，与 settings.json 不同）。"
       "**边界**：技能是知识+流程，不是门，不阻断任何操作。")


def append_section():
    t = io.open(REP, encoding="utf-8").read()
    if "13. 把可复用的部分落成 4 个独立技能" in t:
        return "§13 已存在，跳过"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§13 已写（%d 字符）" % len(SEC)


def add_ledger():
    t = io.open(PROG, encoding="utf-8").read()
    if "\tP415\t" in t:
        return "P415 已存在，跳过"
    backup(PROG)
    io.open(PROG, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + ROW + "\n")
    return "P415 已加"


PLAN_SEC = """
#### 八、可复用件落成 4 个独立技能（W1035，判据=独立触发 / 不可外推 / 会再用）

| 技能 | 触发 | 核心判据 | 落点 |
|---|---|---|---|
| `workbuddy-round-gate-hooks` | 「规矩总是漏」「别再靠你记得」 | 钩子看**改了什么文件**并跑真门，不看消息文本；必须 fail-open（缺字段不能判负） | `~/.workbuddy/skills/` |
| `strata-deploy-evidence-gate` | 「凭什么能落生产」 | D1–D6 缺一即 REFUSE；分支保护只挡合并不挡直推 ⇒ 门设在装机前 | 同上 |
| `engine-io-attribution` | 「以前没这种读盘」 | 五步法钉到文件；单次观测 + 巧合 ≠ 因果 | 同上 |
| `strata-quant-quality-gate` | 「这版数值一样吗」 | 三臂含自一致地板；`max|Δlogit|=0` 优先；混合树不归因单补丁 | 同上 |

**不建**：`ci_probe`（一次性）、`mmq_pad_check`（形状相关，换引擎即失效）、`inventory`（账本已覆盖）。
**不新建同类**：`strata-release`/`strata-report` 已存在，只补分工说明。
**验证**：validator 4/4 · 7 个脚本 md5 0 drift · 技能热加载即用（与 `settings.json` 需重启不同）。
**边界**：技能不阻断操作，门的形态仍是 `round_close` / `deploy_gate` / `Stop` 钩子。
"""


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "#### 八、可复用件落成 4 个独立技能" in t:
        return "§八 已存在，跳过"
    i = t.index("### 回写 · W1035")
    j = t.find("\n### 回写 ·", i + 10)
    j = t.find("\n## ", i + 10) if j == -1 else j
    if j == -1:
        j = len(t)
    backup(PLAN)
    t = t[:j] + "\n" + PLAN_SEC + t[j:]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t)
    return "§6.5 回写 · W1035 追加 §八"


MEMSEC = """
- 04:0x **W1035 · 4 个独立技能落地**（`~/.workbuddy/skills/`）：`workbuddy-round-gate-hooks`（钩子强制，四个坑：settings 启动时读 / 中文 JSON 乱码 / 标记大小写致严格分支永不进入 / 缺字段 fail-closed；须 fail-open）· `strata-deploy-evidence-gate`（D1–D6 + deploy.sh 3.5/8；**分支保护只挡合并不挡直推**）· `engine-io-attribution`（五步法：空闲基线→rchar vs read_bytes→smaps 钉文件→驻留率→冷热对照→对账）· `strata-quant-quality-gate`（三臂含自一致地板；`max|Δlogit|=0` 优先；混合树不归因单补丁）。判据=独立触发 + 不可外推 + 会再用；**不建** ci_probe / mmq_pad_check / inventory（各有理由，已写进方案 §6.5 §八）。验证：validator 4/4、7 个脚本 md5 0 drift、**技能热加载即用（不需重启）**。校验规则坑：`description` 不许含尖括号。技能≠门，不阻断操作。
"""


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在（本轮不动）"
    t = io.open(MEM, encoding="utf-8").read()
    if "4 个独立技能落地" in t:
        return "记忆已含本条，跳过"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_section, add_ledger, add_plan, add_mem):
        print(fn.__name__, "->", fn())
