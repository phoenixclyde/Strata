# 审计收尾：当日日志追加 + 审计报告 CR/BAN 自检
import hashlib, io, os

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

# ---- 1) 审计报告自检 ----
p = os.path.join(WS, "deploy", "W713_AUDIT.md")
t = io.open(p, encoding="utf-8").read()
nb = [hex(ord(c)) for c in t if ord(c) in BAN]
if nb:
    for a, b in [("\u2014\u2014", " - "), ("\u2014", "-"), ("\u2192", "->"), ("\u21d2", "=>")]:
        t = t.replace(a, b)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
d = open(p, "rb").read()
print("W713_AUDIT.md: 清洗前 BAN=%s -> 现 CR=%d BAN=%d bytes=%d md5=%s"
      % (nb if nb else "[]", d.count(b"\r"),
         sum(1 for c in d.decode("utf-8") if ord(c) in BAN), len(d), hashlib.md5(d).hexdigest()[:12]))

# ---- 2) 当日日志追加 ----
log = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
note = """
## W713c 三路独立对抗性审计（2026-10-08 23:0x，机主令「审计」）
- 加载技能 `routeb-audit`；按四条铁律（独立上下文 / 只读 / 对抗立场 / 只认原始证据）派**三路并行只读子 agent**
  （`audit-ledger` / `audit-docs` / `audit-mechanism`，Explore 类型，工具集无 Write/Edit）。上一轮单通道 3 次被 killed，拆三路后全部回收。
- **产出：P1 x6 / P2 x14 / WEAK x5（去重后），P0 = 0**。三条核心结论（升级中性 / B1 边界 / B1b 赢家）的数字经审计侧独立抽样**逐格吻合原始输出**。
- **最重的一条 P1 是工具缺陷**：`verify_config.py:19` **写死容器名 `strata166-402`**，20:12 容器切到 -404 后它一直 inspect 那个已 Exited 的旧容器
  => 四数据面里的 Env 面读的是死容器（两代 env 恰好相同才"侥幸 PASS"）。**根因修**：改为自动探测运行中的 strata 容器；
  顺带把此前"只取不用"的 Cmd 面做成真判定（`--config` 容器内路径 + Binds 映射回宿主 LIVE）。修后实测 **PASS=16 / FAIL=0**（容器自动识别为 -404）。
- 其余 P1：`W712_UPGRADE.md` §4 的 register md5 假陈述（同件自相矛盾）；`SESSION_KICKOFF.md` 仍是 0.1.40.2/-402 的旧快照；
  `W713_PLAN.md` §4.4 把**现役 -404** 列进"回滚旧容器"（危险）；**register P34 + MEMORY.md 把"chunk 对齐"写成已确证机制**（实为经验规律，
  源码直读反而解释不通 every=4096/chunk=8192 得 0 => 已降级为"经验规律 + 待追"）；**MEMORY.md 时效全错**（容器/md5/已完成待办/H5H6/无 0.1.41 字样）。
- 处置：**P1 6/6 修完**、**P2 14/14 修完**、**WEAK 5/5 修完**；含清掉根目录 **6 个 0 字节残留**（W712 §5#1 那次"反引号经 shell"事故的产物，事故认了但垃圾没清）。
  register 改动走完整通道：`3bf819e3…` -> `3dc808ceaf030f370db961001b5d6da1`，**生成物逐字节未变**，推 166 后 FAIL=0，仍 35 行 / 16-12-7。
  MEMORY.md 按 `routek-memory-slim` 技能规程改（**改前归档 `_bak/MEMORY.md.bak_w713_*` + 五断言 + 关键串 + 符号保真**），
  报数六件：**chars 2788 / 余量 212 / 4327 B / md5 `e80b2ec57559556dbb7b1dd70c3f417f` / cr 0 / BAN 0**。
- **审计报告：`deploy/W713_AUDIT.md`**（含 6/14/5 逐条台账 + 无法验证清单 6 条 + 复验表 + 元结论三条）。
- 元结论三条（写进报告的 §6）：① 症状在文档、根因在工具（凡切换环境必须 grep 全部硬编码）；② "结论通过"≠"表述正确"（证据等级要**逐句**标）；
  ③ 同一事实活在多个件里 => **值只写一处、其余写指针**（本轮已把 MEMORY.md 里的 register md5 改成"现值 + 随每次改动而变"）。
- 审计后现行方案：`deploy/W713_PLAN.md`（§0 已标"含对抗性审计后修订"）；下一步仍是 **W1 切换 0.1.41 + W2 升级闸门**。
"""
io.open(log, "a", encoding="utf-8", newline="\n").write(note)
print("当日日志已追加 %d 字符" % len(note))
