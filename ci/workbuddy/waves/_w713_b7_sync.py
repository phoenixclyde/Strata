# B7 后同步：方案账（B7 标完成 / 计数）+ MEMORY.md（技能规程）
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
led = []


def rep(p, old, new, tag=""):
    full = os.path.join(WS, p)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != 1:
        led.append(("MISS", p, "%d" % n, tag or old[:50])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    led.append(("OK", p, "", tag or old[:50])); return True


# 1) 方案：§6.2#1 标完成
rep("deploy/W713_PLAN.md",
    "| 1 | **B7 / 新候选 P35 `STRATA_STAGER_SSD`** | 0.1.41 #1353 的目标场景正是我们；用于判定我们走的是哪条 prompt reader 路径 |",
    "| ~~1~~ | ~~**B7 / 新候选 P35 `STRATA_STAGER_SSD`**~~ **已完成 23:25**：三臂实测**无差**（<=0.1%）=> "
    "**#1353 对本机价值 = 0**，该开关无用；register 新增 **P98 = REJECTED** | 见 `deploy/tmp/_w713_b7_remote.log` |",
    "§6.2#1")
# 2) 方案：§6.1 追加 #14
rep("deploy/W713_PLAN.md",
    "| 13 | 通用切换脚本 |",
    "| 14 | **B7 实测：`STRATA_STAGER_SSD` 三臂无差（<=0.1%）** | 引擎 `/proc` environ 实读确认 env 生效；机制行只在自动分支打印；register **P98 = REJECTED** |\n"
    "| 13 | 通用切换脚本 |",
    "§6.1 追加 #14")
# 3) 方案：§2 的 B7 行标完成 + 顺序行去掉 B7
rep("deploy/W713_PLAN.md",
    "| **B7** | **`STRATA_STAGER_SSD`（新候选 P35）**",
    "| ~~B7~~ | ~~**`STRATA_STAGER_SSD`（新候选 P35）**~~ **已完成：无差 => REJECTED**",
    "§2 B7 行")
rep("deploy/W713_PLAN.md",
    "-> B7 -> B3 -> B2",
    "-> B3 -> B2",
    "§2 顺序行")
# 4) 方案 §6.1 标题口径补一句"计数以现算为准"
rep("deploy/W713_PLAN.md",
    "### 6.1 已做（13 项，带证据）",
    "### 6.1 已做（14 项，带证据；**register 行数/分布以现算为准**：2026-10-08 23:3x = 36 行 / ADOPTED 16 / REJECTED 13 / CANDIDATE 7）",
    "§6.1 标题")

for st, p, ex, tag in led:
    print("  %-5s %-30s %-6s %s" % (st, p, ex, tag))

# 5) MEMORY.md（先备份 + 五断言 + 报数）
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
old = io.open(MEM, encoding="utf-8").read()
bak = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w713g_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)
new = old.replace(
    "register 35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7（**md5 每改必变，别抄**）。",
    "register **行数/分布与 md5 都以现算为准**（2026-10-08 23:3x：36 行 / ADOPTED 16 / REJECTED 13 / CANDIDATE 7；md5 每改必变别抄）。")
new = new.replace(
    "- **未做**：B7 新候选 P35 `STRATA_STAGER_SSD` · ",
    "- **未做**：")
new = new.replace(
    "| 35 行 |", "| 36 行 |")   # 若有
fails = []
if new == old: fails.append("无改动")
if "\r" in new: fails.append("CR")
if len(new) > 2900: fails.append("chars=%d" % len(new))
if 3000 - len(new) < 100: fails.append("余量 %d" % (3000 - len(new)))
if sum(1 for c in new if ord(c) in BAN): fails.append("BAN")
if not new.endswith("\n"): fails.append("结尾换行")
print("MEMORY 断言:", fails if fails else "[]")
if fails:
    raise SystemExit(9)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(new)
b = open(MEM, "rb").read()
assert b == new.encode("utf-8")
print("MEMORY 报数：chars=%d headroom=%d bytes=%d md5=%s cr=%d BAN=%d"
      % (len(new), 3000 - len(new), len(b), hashlib.md5(b).hexdigest(), b.count(b"\r"),
         sum(1 for c in new if ord(c) in BAN)))
