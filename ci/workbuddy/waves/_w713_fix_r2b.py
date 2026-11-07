# 补两处锚点 + MEMORY.md（技能规程）+ 日志 + 终检
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]


def rep(p, old, new, tag="", must=1):
    full = os.path.join(WS, p)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        print("  MISS %-34s %d!=%d  %s" % (p, n, must, tag)); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    print("  OK   %-34s %s" % (p, tag)); return True


# 1) §2 的 C1 行
rep("deploy/W713_PLAN.md",
    "| **C1** | 独立对抗性审计重跑 | 上一轮子 agent 通道 3 次被 killed |",
    "| ~~C1~~ | ~~独立对抗性审计重跑~~ **已完成（两轮）**：22:2x（`W713_AUDIT.md`）+ 23:0x（`W713_AUDIT2.md`） | 见报告两件 |",
    "§2 C1 行")
# 2) §2 顺序行去掉 C1（已完成）
rep("deploy/W713_PLAN.md",
    "-> C4/C5 -> C1 -> C3。",
    "-> C4/C5 -> C3。",
    "§2 顺序行")
# 3) §6.1 #4 补 lend-coverage 关项
rep("deploy/W713_PLAN.md",
    "；服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%） |",
    "；服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%）；**含 0.1.41 新增的 lend-coverage 告警计数 = 0，该观察项当场关项** |",
    "§6.1 #4")

# 4) MEMORY.md（技能规程：先备份 + 五断言 + 报数）
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
old = io.open(MEM, encoding="utf-8").read()
bak = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w713e_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)
new = old
CH = [
    # (a) register 指纹不再写字面值（每改必变）—— 换成指针
    ("register 35 行（md5 随每次改 register 变化，现值 `3dc808ceaf030f370db961001b5d6da1`）",
     "register 35 行（**md5 每改一次就变，别抄进记忆**；核指纹请现算 `md5sum deploy/params/PARAM_REGISTER.tsv` 并与 166 对比）"),
    # (b) 待办里的 B1b 已收口
    ("- **未做**：B1b 收口三件 ·", "- **未做**："),
    # (c) §3 的 B1b 段补"已收口"结论
    ("=> 未采纳。", "=> **已在 0.1.41 上收口并复核**（收益 -70.6% 温 TTFT / 代价 冷预填 -11~-23% / **答案会变**），**判定不改基线 P10**。"),
]
for o, n in CH:
    c = new.count(o)
    print("  MEMORY 锚点命中 %d: %s" % (c, o[:44]))
    assert c == 1, "MEMORY 锚点非唯一"
    new = new.replace(o, n)
# 追加第二轮审计与 B1b 收口一行（放在 §5 末）
new = new.rstrip("\n") + ("\n- 2026-10-08 两轮对抗性审计（`W713_AUDIT.md` + `W713_AUDIT2.md`）：抓出并修掉"
                          "核验器硬编码容器名、**register 本机/166 真值分叉（P0）**、一次整节误删并重建、以及若干时效与口径问题。\n")
fails = []
if "\r" in new: fails.append("CR")
if len(new) > 2900: fails.append("chars=%d" % len(new))
if 3000 - len(new) < 100: fails.append("余量 %d" % (3000 - len(new)))
if sum(1 for c in new if ord(c) in BAN): fails.append("BAN")
if not new.endswith("\n"): fails.append("结尾换行")
for k in ["0.1.41", "strata166-405", "不改基线 P10", "PATCH_SURFACE_ZERO", "Z0=off", "prompt-cache-every"]:
    if k not in new: fails.append("缺关键串 " + k)
print("  MEMORY 断言:", fails if fails else "[]")
if fails:
    raise SystemExit(9)
io.open(MEM, "w", encoding="utf-8", newline="\n").write(new)
b = open(MEM, "rb").read()
assert b == new.encode("utf-8")
print("  MEMORY 报数：chars=%d headroom=%d bytes=%d md5=%s cr=%d BAN=%d"
      % (len(new), 3000 - len(new), len(b), hashlib.md5(b).hexdigest(), b.count(b"\r"),
         sum(1 for c in new if ord(c) in BAN)))

# 5) 日志
io.open(os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md"), "a", encoding="utf-8", newline="\n").write("""
## W713g 第二轮对抗性审计 + 修复（2026-10-08 23:0x-23:3x）
- 三路（数字溯源 / 账本与回归 / 误删重建零损）已完成；**未达标件 12 -> 0**（23:2x 复验）。
- **P0（本轮最重）**：`W713_PLAN.md` 声称 register "本机==166"，实际 **本机 `f82ccdd743ff...` vs 166 `3dc808ceaf03...`**
  ---- 我 23:02 改完 P10 evidence 后**没推 166**。已推（166 侧同时留备份），两侧 md5 现一致。
- **P1（5 条，均已修）**：① `W713_UPGRADE.md` §3.2 对照表**列内混源**（100/220 取 `b1.log`、530 取 `b1b.log`）
  => 已统一为 `b1.log` A 臂并重算差值（-0.3/-0.1、-1.1/-1.4、-0.9/-0.9），并加"两侧差 4 token"的口径披露；
  ② `W713_PLAN` §0 残留旧文（"容器 -405 与切换未做"）与计数 11/14/6 => 整段重写为 13/11/4 且指针不再指具体行号；
  ③ `SESSION_KICKOFF.md` 又过期（0.1.40.4/-404）=> **改成指针式**（"现役一律以 `PROJECT.md` §二 为准"），根治；
  ④ `configs/workbuddy-strata166.md` 正文 8 处 -404 => -405；⑤ `PROJECT.md` 通道/回滚行 => 通用脚本 + 指针。
- **P1（漏修）**：上一轮 `W713_AUDIT.md` 自称"P1 6/6 全修"**是假的** —— P1-5 点名三处只改了两处，
  `W709_HANDOVER.md` §2 仍写"必须与 chunk 对齐"无降级标注。**已补修**并在审计件里更正为"5/6 -> 现 6/6"。
- **P2**：`W713_PLAN` §2 的 C1 标完成、§6.1#4 补回 lend-coverage 关项、§2 顺序行去掉 C1；100 档冷预填补齐四条（427.4-443.6）；
  MEMORY.md 去掉 register 字面值（改为"别抄进记忆、现算"）、B1b 标收口、加两轮审计行；删 `waves/_pr119.out.txt` `_resid.txt`（0 字节）。
- 证据：`deploy/W713_AUDIT2.md`（本轮报告）；修复脚本 `waves/_w713_fix_r2.py`（含一次自伤：字符串里用 ASCII 双引号导致语法错，已修）。
""")
print("  日志已追加")
