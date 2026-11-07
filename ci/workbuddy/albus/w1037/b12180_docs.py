import io, shutil

NEW_MD5 = "d24f8293b575fbcee6c097239d9599cb"
CFG_MD5 = "5e9b81e2f66ca48999766d2ae0201fb6"
OLD_MD5 = "e0a6987f732a401f780f5dad5812812f"

# ---- recipe ----
P0 = "deploy/REBUILD_RECIPE.tsv"
shutil.copyfile(P0, P0 + ".bak_b12180")
s0 = io.open(P0, encoding="utf-8").read()
s0 = s0.replace("strata-0.1.57-mstr\t", "strata-0.1.57-b12180\t")
s0 = s0.replace("master 候选，**未装机**；TQ overlay ON；见 P439", "**在产**（2026-11-07 08:07 装机）；b12180 == master `bcb01528`；TQ overlay ON；见 P439/P440")
s0 = s0.replace("**在产**（2026-11-07 07:50 装机）；TQ overlay ON；见 P437/P438", "回滚件（2026-11-07 08:07 起退居回滚）；TQ overlay ON；见 P437/P438")
io.open(P0, "w", encoding="utf-8", newline="\n").write(s0)
print("recipe updated")

# ---- ledger ----
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_b12180")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B10环境与版本", "P440",
    "升到 b12180（== master bcb01528）并装机：停机 42 s，8K −0.28%（2×CV 0.47%）⇒ 不是负优化，留",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 实测（机主 08:05「装，升 b12180」）**：`b12180` 的 sha 就是 `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（= master HEAD，"
    "2026-11-06T22:42:46Z），所以 07:57 编的 master 件**就是 b12180 件**，已改名 `strata-0.1.57-b12180`（`%s` / 43,207,464 B）。"
    "装机一次重启 **42 s**，config `e23bbce5…` → `%s`（只改 `exe`），`k10p` 退居回滚。"
    "两轮冒烟（2.5K n=6 / 8K n=4）：**8K 1257.1 vs k10p 1260.6 us/tok = −0.28%%**（池化 2×CV 0.47%%）；"
    "2.5K +0.04%%（2×CV 3.96%%）；decode 62.1/66.3 vs 59.7/62.4 tok/s ⇒ 不比 k10p 差。按「不是负优化就跟」**保留**。"
    "**未做**：数值门（KL/top-1 LOGPOS 探针）仍需独占窗口。本轮累计**重启 5 次**、停机 **220 s**。" % (NEW_MD5, CFG_MD5),
    "P439", "KW:b12180|不是负优化"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P440)")

# ---- W832 ----
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_b12180")
s2 = io.open(P2, encoding="utf-8").read()
a = ("| 引擎 md5 / 大小 | **`e0a6987f732a401f780f5dad5812812f` / 43,207,464 B（`strata-0.1.57-k10p`，"
     "llama.cpp b12110 + mmq@4c1004c）**；回滚 `strata-0.1.57-001` = `5e63174dbd7cc04e5fa1b5fc455b2a73` / 42,947,088 B |")
b = ("| 引擎 md5 / 大小 | **`%s` / 43,207,464 B（`strata-0.1.57-b12180`，llama.cpp b12180 == master `bcb01528` + mmq@4c1004c）**；"
     "回滚 `strata-0.1.57-k10p` = `%s`，更早 `strata-0.1.57-001` = `5e63174dbd7cc04e5fa1b5fc455b2a73` |" % (NEW_MD5, OLD_MD5))
assert a in s2, "engine row"
s2 = s2.replace(a, b, 1)
a2 = "| config md5 / args / env | **`e23bbce525487636eeac7020960c46c6`**（`exe=/data/bin/strata-0.1.57-k10p`）/ 37 / 9 | 同上 |"
b2 = "| config md5 / args / env | **`%s`**（`exe=/data/bin/strata-0.1.57-b12180`）/ 37 / 9 | 同上 |" % CFG_MD5
assert a2 in s2, "config row"
s2 = s2.replace(a2, b2, 1)
a3 = "**381 条 / 已结 298 / 78.2%**（W1037 校正"
b3 = "**382 条 / 已结 299 / 78.3%**（W1037 校正"
assert a3 in s2
s2 = s2.replace(a3, b3, 1)
ADD = """
**十七、升到 b12180 并装机（`P440`）。** 机主 08:05「装，升 b12180」。查证：**b12180 的 sha 就是 `bcb01528`（= master HEAD）**，
所以 07:57 编的 master 件就是 b12180 件，改名 `strata-0.1.57-b12180`（`%s` / 43,207,464 B）后装机。
一次重启 **42 s**，config `e23bbce5…` → `%s`（只改 `exe`），`k10p` 退居回滚。
两轮冒烟（2.5K n=6 / 8K n=4）：**8K 1257.1 vs k10p 1260.6 us/tok = −0.28%%**（池化 2×CV 0.47%%）、
2.5K +0.04%%（2×CV 3.96%%）、decode 62.1/66.3 vs 59.7/62.4 tok/s ⇒ 不比 k10p 差，按「不是负优化就跟」**保留**。
**未做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口。本轮累计重启 5 次、停机 220 s。
""" % (NEW_MD5, CFG_MD5)
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 §0.1 + 十七")

# ---- handoff ----
P4 = "albus/w1034/HANDOFF.md"
shutil.copyfile(P4, P4 + ".bak_b12180")
s4 = io.open(P4, encoding="utf-8").read()
s4 = s4.replace("prod_exe=strata-0.1.57-k10p prod_md5=e0a6987f732a401f780f5dad5812812f config_md5=e23bbce525487636eeac7020960c46c6",
                "prod_exe=strata-0.1.57-b12180 prod_md5=d24f8293b575fbcee6c097239d9599cb config_md5=5e9b81e2f66ca48999766d2ae0201fb6")
s4 = s4.replace("| 在产引擎 | `strata-0.1.57-k10p` · md5 `e0a6987f732a401f780f5dad5812812f` · 43,207,464 B（llama.cpp b12110 + mmq@4c1004c）；回滚 `-001` |",
                "| 在产引擎 | `strata-0.1.57-b12180` · md5 `d24f8293b575fbcee6c097239d9599cb` · 43,207,464 B（llama.cpp b12180 == master bcb01528 + mmq@4c1004c）；回滚 `k10p` / `-001` |")
io.open(P4, "w", encoding="utf-8", newline="\n").write(s4)
print("handoff updated")

# ---- reply ----
P3 = "albus/w1037/reply.md"
shutil.copyfile(P3, P3 + ".bak_b12180")
s3 = io.open(P3, encoding="utf-8").read()
pairs = [
 ("| 2 | 运行中引擎 | **`strata-0.1.57-k10p`** · md5 `e0a6987f732a401f780f5dad5812812f` · 43,207,464 B（llama.cpp b12110 + `mmq@4c1004c`）；回滚 `-001` = `5e63174d…` |",
  "| 2 | 运行中引擎 | **`strata-0.1.57-b12180`** · md5 `%s` · 43,207,464 B（llama.cpp b12180 == master `bcb01528` + `mmq@4c1004c`）；回滚 `k10p` = `%s` |" % (NEW_MD5, OLD_MD5)),
 ("| 3 | config | md5 **`e23bbce525487636eeac7020960c46c6`** · `exe=/data/bin/strata-0.1.57-k10p` · args 37 / env 9 |",
  "| 3 | config | md5 **`%s`** · `exe=/data/bin/strata-0.1.57-b12180` · args 37 / env 9 |" % CFG_MD5),
 ("restarts=0（RestartCount 只计策略重启）· StartedAt `2026-11-06T23:49:46Z`（= 本机 07:49:46，**K10 装机后的启动**）",
  "restarts=0（RestartCount 只计策略重启）· StartedAt `2026-11-07T00:06:33Z`（= 本机 08:06:33，**b12180 装机后的启动**）"),
 ("VRAM used 33,584,640,000 B / total 34,342,961,152 B ⇒ **VRAM free 758,321,152 B（0.71 GiB）**（K10 装机后取）",
  "VRAM used 33,602,011,136 B / total 34,342,961,152 B ⇒ **VRAM free 740,950,016 B（0.69 GiB）**（b12180 装机后取）"),
]
for x, y in pairs:
    if x not in s3:
        print("WARN anchor:", x[:36]); continue
    s3 = s3.replace(x, y, 1)

i = s3.find("**三、本次落生产**"); j = s3.find("**四、进度**")
assert i > 0 and j > i
s3 = s3[:i] + ("**三、本次落生产** — **本轮累计：重启 5 次 / 停机 220 s / 装机 3 次 / 回滚 0 次**。"
  "07:23–07:27 A/B 窗口 3 次重启（136 s）；07:49 K10 装机 1 次（42 s）；08:06 升 b12180 装机 1 次（42 s，`running = /data/bin/strata-0.1.57-b12180`）。\n"
  "b12180 冒烟（2.5K n=6 / 8K n=4）：**8K −0.28%（2×CV 0.47%）**、2.5K +0.04%、decode 不比 k10p 差 ⇒ 保留，`k10p` 退居回滚。\n"
  "**没做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口。\n\n") + s3[j:]

a3 = "**381 条 / 已结 298 / 78.2%**（W1037 校正；本轮 +15：`P425`–`P439`）。"
b3 = "**382 条 / 已结 299 / 78.3%**（W1037 校正；本轮 +16：`P425`–`P440`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
s3 = s3.rstrip("\n") + "\n" + """
**18. 升到 b12180 并装机（`P440`）。** b12180 的 sha 就是 `bcb01528`（= master HEAD），所以 07:57 编的 master 件就是它；
改名 `strata-0.1.57-b12180` 后装机，一次重启 42 s，config `e23bbce5…` → `%s`（只改 `exe`）。两轮冒烟：
**8K 1257.1 vs k10p 1260.6 us/tok = −0.28%%（池化 2×CV 0.47%%）**、2.5K +0.04%%、decode 62.1/66.3 vs 59.7/62.4 tok/s ⇒ 保留。
**没做**：数值门的 LOGPOS 探针仍需独占窗口。本轮累计重启 5 次、停机 220 s。
""" % CFG_MD5
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply updated")
