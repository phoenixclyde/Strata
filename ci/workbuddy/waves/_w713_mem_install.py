# MEMORY.md 增量并改安装器（按 routek-memory-slim 技能的规程：先归档 -> 五断言 -> 落盘 -> 读回 -> 报数六件）
#   本件不是"压缩"（chars 未超 2900），走技能 §6「增量并改」路径。
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
BAKDIR = os.path.join(WS, ".workbuddy", "memory", "_bak")
NEWF = os.path.join(WS, "waves", "_w713_mem_new.md")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212,
       0x00D7, 0x2605] + list(range(0x2460, 0x246A))   # 项目禁用码位 + 技能 BAN 表补充

old_b = open(MEM, "rb").read()
old_s = old_b.decode("utf-8")
old_md5 = hashlib.md5(old_b).hexdigest()
print("=== 基线 ===")
print("chars=%d  bytes=%d  cr=%d  md5=%s" % (len(old_s), len(old_b), old_b.count(b"\r"), old_md5))

# ---- 步骤 1：先归档备份（技能的"保险"）----
os.makedirs(BAKDIR, exist_ok=True)
bak = os.path.join(BAKDIR, "MEMORY.md.bak_w713_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)
assert hashlib.md5(open(bak, "rb").read()).hexdigest() == old_md5, "备份 md5 与基线不符"
print("归档备份 ->", bak, "（md5 与基线一致）")

# ---- 步骤 2：读入新稿并做五断言 ----
new_s = open(NEWF, encoding="utf-8").read()
new_b = new_s.encode("utf-8")
fails = []
if "\r" in new_s: fails.append("CR 非 0")
if len(new_s) > 2900: fails.append("chars %d > 2900" % len(new_s))
if 3000 - len(new_s) < 100: fails.append("余量 %d < 100" % (3000 - len(new_s)))
nb = [hex(ord(c)) for c in new_s if ord(c) in BAN]
if nb: fails.append("BAN 命中 %r" % nb)
if not new_s.endswith("\n"): fails.append("结尾无换行")
for key in ["PARAM_REGISTER.tsv", "verify_config.py", "W713_PLAN.md", "strata166-404",
            "3bf819e3ccd3f54ed454154b14c3eb3f", "PATCH_SURFACE_ZERO", "prompt-cache-every",
            "STRATA_STAGER_SSD", "Z0=off"]:
    if key not in new_s: fails.append("关键串缺失: %s" % key)
# 符号保真（cz122 教训）：旧版出现过的符号类字符（非 CJK/全角）不得凭空消失到 0
def symset(t):
    return {c for c in t if ord(c) < 0x3000 or 0xFF00 <= ord(c) <= 0xFFEF}
lost = {c for c in symset(old_s) if c not in new_s and ord(c) > 0x7F}
if lost: fails.append("符号丢失: %r" % sorted(lost))
print("=== 五断言 + 关键串 + 符号保真 ===")
print("FAILS =", fails if fails else "[]")
if fails:
    raise SystemExit(9)   # fail-closed：不写盘

# ---- 步骤 3：落盘 + 读回 ----
io.open(MEM, "w", encoding="utf-8", newline="\n").write(new_s)
back_b = open(MEM, "rb").read()
assert back_b == new_b, "读回与写入不相等"
assert back_b.count(b"\r") == 0

print("=== 报数六件（终态） ===")
print("chars=%d  headroom=%d  bytes=%d  md5=%s  cr=%d  BAN=%d"
      % (len(new_s), 3000 - len(new_s), len(new_b), hashlib.md5(back_b).hexdigest(),
         back_b.count(b"\r"), sum(1 for c in new_s if ord(c) in BAN)))
print("旧 -> 新 chars: %d -> %d (delta %+d)" % (len(old_s), len(new_s), len(new_s) - len(old_s)))
