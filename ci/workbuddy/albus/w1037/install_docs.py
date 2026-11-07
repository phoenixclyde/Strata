import io, shutil

NEW_MD5 = "e0a6987f732a401f780f5dad5812812f"
NEW_SIZE = "43,207,464"
CFG_MD5 = "e23bbce525487636eeac7020960c46c6"
OLD_MD5 = "5e63174dbd7cc04e5fa1b5fc455b2a73"

# ---------- rebuild recipe ----------
P0 = "deploy/REBUILD_RECIPE.tsv"
shutil.copyfile(P0, P0 + ".bak_inst")
s0 = io.open(P0, encoding="utf-8").read()
s0 = s0.replace("K10 重建件，**未装机**；TQ overlay ON；见 P437", "**在产**（2026-11-07 07:50 装机）；TQ overlay ON；见 P437/P438")
s0 = s0.replace("build-r28（镜像 strata-gfx906:0.2.11-101 内，/src=该 tag）\t在产",
                "build-r28（镜像 strata-gfx906:0.2.11-101 内，/src=该 tag）\t回滚件（2026-11-07 07:50 起退居回滚）")
io.open(P0, "w", encoding="utf-8", newline="\n").write(s0)
print("recipe updated")

# ---------- ledger ----------
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_inst")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B10环境与版本", "P438",
    "K10 装机：strata-0.1.57-k10p 进生产，停机 42 s，8K +0.32%（2×CV 1.0%）⇒ 不是负优化，留",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 实测（机主 07:49「装」）**：`install_k10.sh` 一次重启 42 s，`running = /data/bin/strata-0.1.57-k10p`，"
    "config md5 `53ac61e0…` → `%s`（只改 `exe` 一个字段）。冒烟两轮（n=6 于 2.5K / n=4 于 8K）："
    "**8K 1260.6 vs 对照 1256.6 us/tok = +0.32%%（池化 2×CV 1.0%%）**；2.5K 1578.9 vs 1571.5 = +0.47%%（2×CV 2.5%%）；"
    "decode 62.4 vs 57.6 tok/s（CV 14%%/15%%，噪声）。相位 `qsa attn` 572–583 / 2222–2255，与对照同带。"
    "按机主口径「只要不是负优化就跟」⇒ **保留**，`-001`（`%s`）退居回滚件。"
    "**未做**：数值门（KL/top-1 的 LOGPOS 探针）仍需独占窗口（`P392` 同理），本条只覆盖性能面。" % (CFG_MD5, OLD_MD5),
    "P437", "KW:装机|k10p"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P438)")

# ---------- W832 §0.1 + 回写 ----------
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_inst")
s2 = io.open(P2, encoding="utf-8").read()
a = "| 引擎 md5 / 大小 | `5e63174dbd7cc04e5fa1b5fc455b2a73` / 42,947,088 B（`strata-0.1.57-001`） |"
b = ("| 引擎 md5 / 大小 | **`%s` / %s B（`strata-0.1.57-k10p`，llama.cpp b12110 + mmq@4c1004c）**；"
     "回滚 `strata-0.1.57-001` = `%s` / 42,947,088 B |" % (NEW_MD5, NEW_SIZE, OLD_MD5))
assert a in s2, "engine row"
s2 = s2.replace(a, b, 1)
a2 = "| config md5 / args / env | `53ac61e0c663a6a46b7a5aa2e610bf43` / 37 / 9 | 同上 |"
b2 = "| config md5 / args / env | **`%s`**（`exe=/data/bin/strata-0.1.57-k10p`）/ 37 / 9 | 同上 |" % CFG_MD5
assert a2 in s2, "config row"
s2 = s2.replace(a2, b2, 1)
a3 = "**379 条 / 已结 296 / 78.1%**（W1037 校正"
b3 = "**380 条 / 已结 297 / 78.2%**（W1037 校正"
assert a3 in s2
s2 = s2.replace(a3, b3, 1)
ADD = """
**十五、K10 装机完成（`P438`）。** 机主 07:49「装」。一次重启 **42 s**，`running = /data/bin/strata-0.1.57-k10p`
（`%s` / %s B），config md5 `53ac61e0…` → `%s`（只改 `exe` 一个字段），`-001` 退居回滚件。
冒烟两轮（2.5K n=6 / 8K n=4）：**8K 1260.6 vs 对照 1256.6 us/tok = +0.32%%**（池化 2×CV 1.0%%）、
2.5K +0.47%%（2×CV 2.5%%）、decode 在 CV 14%% 的噪声里 ⇒ 按机主口径「只要不是负优化就跟」**保留**。
**没做的说清楚**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口，这条只覆盖性能面。
""" % (NEW_MD5, NEW_SIZE, CFG_MD5)
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 §0.1 + 十五")

# ---------- handoff SNAPSHOT ----------
P4 = "albus/w1034/HANDOFF.md"
shutil.copyfile(P4, P4 + ".bak_inst")
s4 = io.open(P4, encoding="utf-8").read()
s4 = s4.replace("prod_exe=strata-0.1.57-001 prod_md5=5e63174dbd7cc04e5fa1b5fc455b2a73 config_md5=53ac61e0c663a6a46b7a5aa2e610bf43",
                "prod_exe=strata-0.1.57-k10p prod_md5=e0a6987f732a401f780f5dad5812812f config_md5=e23bbce525487636eeac7020960c46c6")
s4 = s4.replace("| 在产引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B |",
                "| 在产引擎 | `strata-0.1.57-k10p` · md5 `e0a6987f732a401f780f5dad5812812f` · 43,207,464 B（llama.cpp b12110 + mmq@4c1004c）；回滚 `-001` |")
io.open(P4, "w", encoding="utf-8", newline="\n").write(s4)
print("HANDOFF SNAPSHOT updated")

# ---------- reply ----------
P3 = "albus/w1037/reply.md"
shutil.copyfile(P3, P3 + ".bak_inst")
s3 = io.open(P3, encoding="utf-8").read()
pairs = [
 ("| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B |",
  "| 2 | 运行中引擎 | **`strata-0.1.57-k10p`** · md5 `e0a6987f732a401f780f5dad5812812f` · 43,207,464 B（llama.cpp b12110 + `mmq@4c1004c`）；回滚 `-001` = `5e63174d…` |"),
 ("| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |",
  "| 3 | config | md5 **`e23bbce525487636eeac7020960c46c6`** · `exe=/data/bin/strata-0.1.57-k10p` · args 37 / env 9 |"),
 ("restarts=0（docker 的 RestartCount 只计策略重启）· StartedAt `2026-11-06T23:26:40Z`（= 本机 07:26:40，**本轮 A/B 窗口还原后的启动**）",
  "restarts=0（RestartCount 只计策略重启）· StartedAt `2026-11-06T23:49:46Z`（= 本机 07:49:46，**K10 装机后的启动**）"),
 ("VRAM used 33,583,194,112 B / total 34,342,961,152 B ⇒ **VRAM free 759,767,040 B（0.71 GiB）**（窗口还原后取）",
  "VRAM used 33,584,640,000 B / total 34,342,961,152 B ⇒ **VRAM free 758,321,152 B（0.71 GiB）**（K10 装机后取）"),
 ("**引擎无净变更**：disk = build = running 三方一致（`-001` / `5e63174d…`），config md5 回到 `53ac61e0…`；"
  "本轮**装机 1 次（候选 pa1，窗口内，已还原）/ 重启 3 次 / 停机 136 s / 回滚 0 次**。",
  "**本轮换了一次在产件**：`-001` → `k10p`（llama.cpp b12110 + mmq@4c1004c），disk = build = running 三方一致（`e0a6987f…`），"
  "config md5 `53ac61e0…` → `e23bbce5…`（只改 `exe`）；本轮**装机 2 次（pa1 已还原 / k10p 在产）/ 重启 4 次 / 停机 178 s / 回滚 0 次**。"),
]
for x, y in pairs:
    if x not in s3:
        print("WARN anchor:", x[:40])
        continue
    s3 = s3.replace(x, y, 1)

# 三、落生产
i = s3.find("**三、本次落生产**")
j = s3.find("**四、进度**")
assert i > 0 and j > i
s3 = s3[:i] + ("**三、本次落生产** — **重启 4 次 / 停机 178 s / 回滚 0 次 / 装机 2 次（pa1 已还原、k10p 在产）**。\n"
  "07:23–07:27 的 A/B 窗口三段重启（47/42/47 s，合计 136 s）；07:49:44–07:50:29 的 K10 装机一次重启 **42 s**，"
  "`running = /data/bin/strata-0.1.57-k10p`；config md5 `53ac61e0…` → `e23bbce5…`（只改 `exe` 一个字段）。\n"
  "K10 冒烟（2.5K n=6 / 8K n=4）：**8K +0.32%（池化 2×CV 1.0%）**、2.5K +0.47%（2×CV 2.5%）、decode 在噪声里 ⇒ 按「不是负优化就跟」保留。\n"
  "**没做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口。\n\n") + s3[j:]

a3 = "**379 条 / 已结 296 / 78.1%**（W1037 校正；本轮 +13：`P425`–`P437`）。"
b3 = "**380 条 / 已结 297 / 78.2%**（W1037 校正；本轮 +14：`P425`–`P438`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**16. K10 装机完成（`P438`）。** 一次重启 42 s，`running = /data/bin/strata-0.1.57-k10p`（`e0a6987f…` / 43,207,464 B），
config `53ac61e0…` → `e23bbce5…`（只改 `exe`），`-001` 退居回滚件。冒烟两轮：**8K 1260.6 vs 对照 1256.6 us/tok = +0.32%**
（池化 2×CV 1.0%）、2.5K +0.47%（2×CV 2.5%）、decode 62.4 vs 57.6 tok/s（CV 14%/15%）⇒ 按机主口径**保留**。
**没做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口——这条只覆盖性能面，别当成「已验证」。
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply updated")
