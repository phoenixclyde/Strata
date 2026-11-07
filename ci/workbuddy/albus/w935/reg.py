# -*- coding: utf-8 -*-
"""W935: 采纳 5a13c34f（PLE 提限）+ P260 + 队列"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

# ---------- PARAM_REGISTER: P260 ----------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
rows = io.open(q, encoding="utf-8").read().split("\n")
p260 = "\t".join([
    "P260", "REF", "`5a13c34f` PLE 提限补丁（mlock 前把 RLIMIT_MEMLOCK 的 soft 提到 hard）",
    "已采纳（2026-11-04，引擎 8e92c662）", "kv", "ADOPTED", "P256", "-", "-", "W935",
    ("**W935 实测（2026-11-04 09:0x-09:3x）**：①**三场景验证**（prlimit 喂 limit + 复刻补丁逻辑）："
     "**soft=8M/hard=unlimited ⇒ 提限 8→1536 MiB、mlock(512 MiB) OK**（这是补丁存在意义的那一档）；"
     "soft=8M/hard=8M（dockerd 默认）⇒ 提不动（`max>cur` 不成立）；unlimited ⇒ 正确跳过、零动作。"
     "②生产侧：`PLE table locked in RAM 1.7-1.9 s`、`VmLck 26.82 GiB`、**无 `raised to` 行**（不改变现有行为）。"
     "③性能无回归：prefill 8.790→8.853(+0.7%, CV 0.9%)、decode 80.58→79.4(−1.5%, CV 12.8%)。"
     "**价值**：`--ulimit memlock=-1` 是**部署依赖**（重建容器漏带就退回 8 MiB），补丁让引擎自己提限 ⇒ "
     "若宿主 dockerd 设 `LimitMEMLOCK=infinity`，容器可不再需要该参数。**注**：dockerd 当前仍是 8388608，"
     "未改（`restart docker` 会重启所有容器，属系统级变更，待定）"),
])
at = None
for i, rr in enumerate(rows):
    f = rr.split("\t")
    if f and f[0] == "P259":
        at = i + 1
        break
if at is not None:
    rows.insert(at, p260)
    print("P260 inserted")
else:
    rows.append(p260)
io.open(q, "w", encoding="utf-8").write("\n".join(rows))

# ---------- PROGRESS: 追加 R78（采纳记录，作为已结条目） ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
while lines and lines[-1] == "":
    lines.pop()
lines.append("\t".join([
    "B10环境与版本", "R78",
    "采纳 `5a13c34f`（PLE 提限）：mlock 前把 RLIMIT_MEMLOCK 的 soft 提到 hard，失败时给出需要/允许/怎么改",
    "W935 §0", "count", "1", "1", "DONE",
    ("**W935 实测 2026-11-04 09:0x-09:3x｜1 次重启｜已装生产**：干净版二进制 `8e92c662`（主线 d963c791 + 仅此一条；"
     "R66/R68 的四个符号实测均为 0）。**三场景**：soft=8M/hard=unlimited ⇒ 提限 8→1536 MiB、mlock OK（补丁的意义所在）；"
     "soft=hard=8M（dockerd 默认）⇒ 提不动；unlimited ⇒ 静默跳过。**生产验证**：PLE locked 1.7-1.9 s、VmLck 26.82 GiB、"
     "无 raised 行。**性能无回归**：prefill +0.7%(CV 0.9%)、decode −1.5%(CV 12.8%)。"
     "**未做**：宿主 dockerd 的 `LimitMEMLOCK=infinity`（改它可去掉容器 `--ulimit` 依赖，但 restart docker 会重启所有容器）"),
    "W935;W919",
]))
lines.append("")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
print("R78 appended")

# ---------- W832 队列 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 09:3x 修，`W935`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70~~ → ~~R75~~ → ~~R76~~ "
            "→ ~~R65~~ → ~~R78（采纳 PLE 提限，引擎 8e92c662）~~ → **R77**（cherry-pick fatal error 自退） → "
            "**R74**（W4A4 精度门） → R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))
print("done")
