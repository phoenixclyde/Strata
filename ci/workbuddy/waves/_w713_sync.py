# 切换后同步"现役事实"的 4 处副本 + 方案账更新 + MEMORY.md（按技能规程） + 新件码位清洗
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
SUB = [("\u2014\u2014", " - "), ("\u2014", "-"), ("\u2192", "->"), ("\u21d2", "=>"),
       ("\u2026", "..."), ("\u2264", "<="), ("\u2265", ">="), ("\u2260", "!="),
       ("\u2212", "-"), ("\u00d7", "x")]
log = []


def clean(path):
    full = os.path.join(WS, path if path.startswith(".") or "/" in path else path)
    t = io.open(full, encoding="utf-8").read()
    nb = sum(1 for c in t if ord(c) in BAN)
    if nb:
        for a, b in SUB:
            t = t.replace(a, b)
        io.open(full, "w", encoding="utf-8", newline="\n").write(t)
        log.append(("CLEAN", path, "BAN %d -> 0" % nb, ""))
    return nb


def rep(path, old, new, must=1):
    full = path if os.path.isabs(path) else os.path.join(WS, path)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        log.append(("MISS", os.path.basename(path), "%d!=%d" % (n, must), old[:60])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    log.append(("OK", os.path.basename(path), "", old[:60])); return True


# 0) 清新件码位
clean("deploy/W713_UPGRADE.md")

# 1) PROJECT.md 现役三行 + 回滚行
rep("PROJECT.md",
    "| 引擎 | Strata `v0.1.40.4`（上游 `Niko1221/Strata`；2026-10-08 由 0.1.40.2 升级，见 `deploy/W712_UPGRADE.md`） |",
    "| 引擎 | Strata `v0.1.41`（上游 `Niko1221/Strata`；2026-10-08 连升两次：0.1.40.2`->`0.1.40.4 见 `deploy/W712_UPGRADE.md`，0.1.40.4`->`0.1.41 见 `deploy/W713_UPGRADE.md`） |")
rep("PROJECT.md", "| 镜像 | `strata-gfx906:0.1.40.4`（`8f8f6e87e664` / 6.57 GB） |",
                "| 镜像 | `strata-gfx906:0.1.41`（`c45268e786e1` / 6.57 GB；补丁面归零） |")
rep("PROJECT.md", "| 容器 | `strata166-404`（端口 **8090**", "| 容器 | `strata166-405`（端口 **8090**")

# 2) 配置件头部
rep("deploy/configs/workbuddy-strata166.md",
    "> **升级于 2026-10-08 20:12 CST**：Strata `v0.1.40.2` -> **`v0.1.40.4`**",
    "> **升级于 2026-10-08 22:35 CST**：Strata `v0.1.40.4` -> **`v0.1.41`**（当日第二次）")
rep("deploy/configs/workbuddy-strata166.md",
    "> 服务：镜像 **`strata-gfx906:0.1.40.4`** / 容器 **`strata166-404`** / 端口 **8090**",
    "> 服务：镜像 **`strata-gfx906:0.1.41`** / 容器 **`strata166-405`** / 端口 **8090**")

# 3) 方案 §0 状态行
rep("deploy/W713_PLAN.md",
    "**当前状态（23:0x，含对抗性审计后修订）**：**三路独立对抗性审计已完成**（6 条 P1 全部处置，见 `deploy/W713_AUDIT.md`）；",
    "**当前状态（22:4x，含对抗性审计后修订）**：**三路独立对抗性审计已完成**（6 条 P1 全部处置，见 `deploy/W713_AUDIT.md`）；"
    "**0.1.41 已切换并跑完升级闸门（中性成立）**，见 `deploy/W713_UPGRADE.md`；"
    "**W1 / W2 因此已完成**（§6.1 #12 / #13）。")

# 4) §6.2 的 #1 / #2 标完成
rep("deploy/W713_PLAN.md",
    "| 1 | **W1 切换 0.1.41**（建容器 -405 -> 切换 -> 复验） | 镜像已好；切换需走带自动回滚的脚本（会打断本会话推理 35 s，实测可控） |",
    "| ~~1~~ | ~~**W1 切换 0.1.41**~~ **已完成 22:35**（-405 就绪 35 s，复验 PASS=16/FAIL=0） | 见 `deploy/W713_UPGRADE.md` |")
rep("deploy/W713_PLAN.md",
    "| 2 | **W2 升级闸门脚本化** `deploy/scripts/_upgrade_gate.sh` | 有它以后每次升级 10 分钟买一份可比证据 |",
    "| ~~2~~ | ~~**W2 升级闸门脚本化**~~ **已完成并首跑**：`deploy/scripts/upgrade_gate.sh`（服务面 7 项 + 中性矩阵，实测中性成立） | 见 `W713_UPGRADE.md` §3 |")

# 5) §6.1 追加两条已做
rep("deploy/W713_PLAN.md",
    "| 11 | \"升级闸门\"方案 | 本件 §3（判据已定，脚本待写 -> 见 6.2 #2） |",
    "| 11 | \"升级闸门\"方案 | 本件 §3（**已落脚本并首跑**，见 #13） |\n"
    "| 12 | **引擎 0.1.40.4 -> 0.1.41 升级 + 切换** | 补丁面**归零**（`PATCH_SURFACE_ZERO`）；镜像 `c45268e786e1`；容器 `-405` 35 s 就绪；`deploy/W713_UPGRADE.md` |\n"
    "| 13 | **升级闸门脚本 + 首跑** | `deploy/scripts/upgrade_gate.sh`；服务面 7 项全过 + 中性矩阵（三档 reused 逐格相同、差 <=1.4%） |")

for st, p, extra, what in log:
    print("  %-6s %-34s %-12s %s" % (st, p, extra, what))

# 6) MEMORY.md（按 routek-memory-slim 规程：先备份 + 五断言 + 报数）
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
old = io.open(MEM, encoding="utf-8").read()
bak = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w713c_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)
new = old.replace(
    "- 生产：`strata-gfx906:0.1.40.4` / 容器 `strata166-404` / 8090 / `--restart unless-stopped`（不用 systemd）；\n"
    "  **0.1.41 镜像已建**（`c45268e786e1`，补丁面归零），**容器 -405 与切换未做**。",
    "- 生产：**`strata-gfx906:0.1.41` / 容器 `strata166-405`** / 8090 / `--restart unless-stopped`（不用 systemd）；补丁面**归零**。\n"
    "  回滚：`bash /home/albus/strata166/w712/switch_strata.sh <旧容器>`（-404=0.1.40.4 / -402=0.1.40.2 均 Exited 保留）。\n"
    "  升级闸门 `deploy/scripts/upgrade_gate.sh` 已首跑：**中性成立**（三档 reused 逐格相同、差 <=1.4%）。")
fails = []
if new == old: fails.append("替换未生效")
if "\r" in new: fails.append("CR")
if len(new) > 2900: fails.append("chars")
if sum(1 for c in new if ord(c) in BAN): fails.append("BAN")
if not new.endswith("\n"): fails.append("结尾换行")
print("MEMORY.md 断言:", fails if fails else "[]")
if fails:
    raise SystemExit(9)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(new)
b = open(MEM, "rb").read()
assert b == new.encode("utf-8")
print("MEMORY.md 报数：chars=%d headroom=%d bytes=%d md5=%s cr=%d BAN=%d（备份 %s）"
      % (len(new), 3000 - len(new), len(b), hashlib.md5(b).hexdigest(), b.count(b"\r"),
         sum(1 for c in new if ord(c) in BAN), os.path.basename(bak)))

# 7) 终检
print("\n=== 终检 ===")
for p in ["PROJECT.md", "DEPLOY".lower() + "/W713_PLAN.md", "deploy/W713_UPGRADE.md",
          "deploy/configs/workbuddy-strata166.md", ".workbuddy/memory/MEMORY.md"]:
    d = open(os.path.join(WS, p), "rb").read()
    print("  %-42s CR=%d BAN=%d bytes=%d" % (p, d.count(b"\r"),
          sum(1 for c in d.decode("utf-8") if ord(c) in BAN), len(d)))
