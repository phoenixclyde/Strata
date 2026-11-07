# MEMORY.md 第二次尝试：用"协调式一处改三行"（新增 §0 现役 + 从待办移除已完成项 + 修正容器数），保证 <=2900
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

old = io.open(MEM, encoding="utf-8").read()
bak = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w713d_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)

A_OLD = ("- 生产：`strata-gfx906:0.1.40.4` / 容器 `strata166-404` / 8090 / `--restart unless-stopped`（不用 systemd）；\n"
         "  **0.1.41 镜像已建**（`c45268e786e1`，补丁面归零），**容器 -405 与切换未做**。")
A_NEW = ("- 生产：**`strata-gfx906:0.1.41` / `strata166-405`** / 8090 / `--restart unless-stopped`（不用 systemd）；补丁面**归零**。\n"
         "  回滚 `bash /home/albus/strata166/w712/switch_strata.sh <旧容器>`（-404/-402 均 Exited 保留）；"
         "闸门 `deploy/scripts/upgrade_gate.sh` 已首跑：**中性成立**（三档 reused 逐格相同、差 <=1.4%）。")
B_OLD = "- **未做**：切换 0.1.41 + 闸门脚本化 · B1b 收口三件 ·"
B_NEW = "- **未做**：B1b 收口三件 ·"
C_OLD = "C3 清理（5 镜像 / 4 容器）"
C_NEW = "C3 清理（5 镜像 / 5 容器）"

new = old
for o, n in [(A_OLD, A_NEW), (B_OLD, B_NEW), (C_OLD, C_NEW)]:
    c = new.count(o)
    print("锚点命中 %d: %s" % (c, o[:40]))
    assert c == 1, "锚点非唯一"
    new = new.replace(o, n)

fails = []
if "\r" in new: fails.append("CR")
if len(new) > 2900: fails.append("chars=%d" % len(new))
if 3000 - len(new) < 100: fails.append("余量 %d" % (3000 - len(new)))
if sum(1 for c in new if ord(c) in BAN): fails.append("BAN")
if not new.endswith("\n"): fails.append("结尾换行")
for k in ["0.1.41", "strata166-405", "upgrade_gate.sh", "PATCH_SURFACE_ZERO", "Z0=off"]:
    if k not in new: fails.append("缺关键串 " + k)
print("断言:", fails if fails else "[]")
if fails:
    raise SystemExit(9)

io.open(MEM, "w", encoding="utf-8", newline="\n").write(new)
b = open(MEM, "rb").read()
assert b == new.encode("utf-8"), "读回不符"
print("MEMORY.md 报数：chars=%d headroom=%d bytes=%d md5=%s cr=%d BAN=%d"
      % (len(new), 3000 - len(new), len(b), hashlib.md5(b).hexdigest(), b.count(b"\r"),
         sum(1 for c in new if ord(c) in BAN)))
print("备份:", os.path.basename(bak), "（旧 %d chars / md5 %s）"
      % (len(old), hashlib.md5(old.encode('utf-8')).hexdigest()[:12]))
