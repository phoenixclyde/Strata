# 审计收尾批：配置件 Z0/时效 + W713_PLAN（kv-grow/审计节/md5）+ W712_UPGRADE 样本量声明 + MEMORY.md md5
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
log = []


def rep(path, old, new, must=1, fs=None):
    full = fs or os.path.join(WS, path)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        log.append(("MISS", path, "%d!=%d" % (n, must), old[:60])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    log.append(("OK", path, "", old[:60])); return True


# ---- 1) 配置件：B1b 时效 + §十 Z0 声明 ----
rep("deploy/configs/workbuddy-strata166.md",
    "但**尚未实测**，已列为下一步 B1b（见 `deploy/W712_PLAN.md`）。",
    "B1b 已实测（`--prefill 4096` + `every 4096`：4.6k 会话温 TTFT 10.58 -> 3.59 s，冷预填 -11%），"
    "**但尚未采纳**（未在 0.1.41 复核、答案是否变未测）=> 现行方案与全量账见 `deploy/W713_PLAN.md`。")

rep("deploy/configs/workbuddy-strata166.md",
    "## 十、前缀复用的边界（B1 实测，2026-10-08）",
    "## 十、前缀复用的边界（B1 实测，2026-10-08）\n\n> 环境声明：本节全部读数均在 **Z0=off（省电档）** 下取得；分辨力 = 预填 1.2-1.7%。")

# ---- 2) W713_PLAN：补 --kv-grow + 审计节 + §6.1 的 register md5 ----
rep("deploy/W713_PLAN.md",
    "| 9 | **B5 P28 `STRATA_GR_SPLIT`** | 预期 ~3% < 分辨力 => 只用机制判据 |",
    "| 9 | **B5 P28 `STRATA_GR_SPLIT`**（同族低优先项 `--kv-grow`(P32) 也仍未测） | 预期 ~3% < 分辨力 => 只用机制判据 |")

rep("deploy/W713_PLAN.md",
    "| 9 | **固化审计 + P34 结论入 register** | register `3bf819e3ccd3f54ed454154b14c3eb3f`",
    "| 9 | **固化审计 + P34 结论入 register** | register `3dc808ceaf030f370db961001b5d6da1`（当天两改：`a91b677e` -> `3bf819e3` -> 本次）")

rep("deploy/W713_PLAN.md",
    "**当前状态（22:2x）**：",
    "**当前状态（23:0x，含对抗性审计后修订）**：**三路独立对抗性审计已完成**（6 条 P1 全部处置，见 `deploy/W713_AUDIT.md`）；")

# ---- 3) W712_UPGRADE：给"中性"结论加样本量边界（审计 F8）----
rep("deploy/W712_UPGRADE.md",
    "**判据**：本机分辨力 **预填 1.2-1.7%**。",
    "**判据**：本机分辨力 **预填 1.2-1.7%**。**样本量声明（2026-10-08 审计 F8）**："
    "本次每臂仅 **2 组**，低于本项目自己「亚分辨力效应须 >=5 轮/臂」的口径 —— "
    "故本条只判「**差值小于分辨力**」（这是 n=2 足以支持的部分），**不判**「两版完全等价」。")

# ---- 4) MEMORY.md：改 register md5（按技能规程：先备份 + 五断言 + 报数）----
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
BAK = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w713b_" + time.strftime("%Y%m%d_%H%M%S"))
old_b = open(MEM, "rb").read()
old_s = old_b.decode("utf-8")
shutil.copy2(MEM, BAK)
assert hashlib.md5(open(BAK, "rb").read()).hexdigest() == hashlib.md5(old_b).hexdigest()
new_s = old_s.replace("register md5 `3bf819e3ccd3f54ed454154b14c3eb3f` / 35 行",
                      "register 35 行（md5 随每次改 register 变化，现值 `3dc808ceaf030f370db961001b5d6da1`）")
fails = []
if new_s == old_s: fails.append("替换未生效")
if "\r" in new_s: fails.append("CR")
if len(new_s) > 2900: fails.append("chars")
if sum(1 for c in new_s if ord(c) in BAN): fails.append("BAN")
if not new_s.endswith("\n"): fails.append("结尾换行")
print("MEMORY.md 断言:", fails if fails else "[]")
if fails:
    raise SystemExit(9)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(new_s)
bb = open(MEM, "rb").read()
assert bb == new_s.encode("utf-8")
log.append(("OK", "MEMORY.md", "", "register md5 更新（备份 %s）" % os.path.basename(BAK)))
print("MEMORY.md 报数：chars=%d headroom=%d bytes=%d md5=%s cr=%d BAN=%d"
      % (len(new_s), 3000 - len(new_s), len(bb), hashlib.md5(bb).hexdigest(), bb.count(b"\r"),
         sum(1 for c in new_s if ord(c) in BAN)))

print("\n=== 台账 ===")
for st, path, extra, what in log:
    print("  %-5s %-30s %-8s %s" % (st, path, extra, what))
print("\n=== CR/BAN 复验 ===")
for p in ["deploy/configs/workbuddy-strata166.md", "deploy/W713_PLAN.md", "deploy/W712_UPGRADE.md",
          ".workbuddy/memory/MEMORY.md"]:
    d = open(os.path.join(WS, p), "rb").read()
    print("  %-42s CR=%d BAN=%d bytes=%d" % (p, d.count(b"\r"),
          sum(1 for c in d.decode("utf-8") if ord(c) in BAN), len(d)))
