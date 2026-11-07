# 收尾：闸门关项（lend coverage=0）+ 当日日志追加 + 终检
import hashlib, io, os

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

# 1) §6.2 #10 关项
p = os.path.join(WS, "deploy", "W713_PLAN.md")
t = io.open(p, encoding="utf-8").read()
old = "| 判据：`grep -c 'lend coverage' 166:data/strata-ud-iq4_xs.log`，>0 记证据并入账，=0 即关项 |"
new = "| **已关项**：0.1.41 闸门实测 `lend coverage` 计数 = **0**（我们不走短借覆盖不足那条路） |"
assert t.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
print("§6.2#10 已关项")

# 2) 当日日志
log = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
note = """
## W713d W1 切换 0.1.41 + W2 升级闸门（2026-10-08 22:34-22:45，机主令「你继续」）
- **脚本升级（方案优化）**：切换脚本从"一次升级一个专用脚本"改成**通用参数化** `deploy/scripts/switch_strata.sh`
  （旧容器自动探测 + 300 s 轮询 + 失败自动回滚；md5 `c49d8164976ac2fdce102490a0d640db`）；
  新增 `deploy/scripts/upgrade_gate.sh`（md5 `ec2a0050ed4cd13e28ba273c20af15ea`）。两个都过 CR=0/BAN=0/bash -n。
- 建容器 `strata166-405`（0.1.41，参数逐项抄 -404）；**切换实测**：22:34:22 自动探测 OLD=`-404` -> 停 -> 22:34:28 起 -405
  -> **22:35:03 ready（35 s）** -> rc=0；-404 `Exited (0)` 保留；引擎三项参数在；LIVE md5 未变。
- **升级闸门首跑**（服务面 7 项 + 中性矩阵）：
  1) `/v1/models` 200 / `n_ctx 262144`；2) `strata --version` = **`strata 0.1.41`**；3) `/proc` cmdline 三项参数在；
  4) LIVE md5 未变；5) 容器 -405 Up、其余 4 个 Exited；6) 本机 `verify_config.py` **PASS=16 / FAIL=0**（容器自动识别 -405）；
  7) **0.1.41 新增的 "lend coverage" 告警计数 = 0 => 该观察项当场关项**。
- **中性矩阵（1 臂 x 3 档 x 2 轮，Z0=off）vs 0.1.40.4 同口径**：
  | 档 | 0.1.41 冷 -> 温 / reused | 0.1.40.4 冷 -> 温 / reused |
  | 100 | 10.80 -> 10.463 / 0 | 10.83 -> 10.472 / 0 |
  | 220 | 22.84 -> 5.786 / 8192 | 23.10 -> 5.866 / 8192 |
  | 530 | 49.67 -> 16.836 / 16384 | 50.02 -> 17.011 / 16384 |
  冷预填引擎行：100 档 441.8-443.6、220 档 438.3-440.0、530 档 **482.6-482.8**（上版 479.7-481.0）。
  => **三档 reused 逐格相同、所有差 <=1.4% => 中性成立**（样本量 n=2，故只判"差小于分辨力"）。
  => **#1353（RAM-resident prompt reader）对我们没有带来增益**（+0.6%，分辨力内），与官方在 R9700 上的观察一致。
- 交付件：新写 `deploy/W713_UPGRADE.md`；同步现役事实四处副本（`PROJECT.md` §二 / `configs/workbuddy-strata166.md` 头部 /
  `W713_PLAN.md` §0+§6.1#12/#13+§6.2#1#2 标完成 / `MEMORY.md`）；
  `MEMORY.md` 按技能规程改（备份 `_bak/MEMORY.md.bak_w713d_*`；**chars 2878 / 余量 122 / 4432 B / md5 `9ad339b540ecbeaff3b1c07ac46cecd8` / cr 0 / BAN 0**；
  第一次尝试因 2900 上限被 fail-closed 拦下、文件未动，改为"一处改三行"的协调式编辑才过）。
- 账本变化：**已做 11 -> 13 项**（+W1 切换、+W2 闸门脚本）；**没做 14 -> 12 项**（-2）。
- 下一步（账上）：**B1b 收口三件**（答案是否变 / 在 0.1.41 上复核 / 冷预填代价入结论）-> B7(P35 `STRATA_STAGER_SSD`) -> B3 -> B2 -> B6 -> B4 -> B5 -> C4/C5 -> C1 -> C3。
"""
io.open(log, "a", encoding="utf-8", newline="\n").write(note)
print("当日日志已追加 %d 字符" % len(note))

# 3) 终检
print("\n=== 终检 ===")
files = ["PROJECT.md", "HANDOVER.md", "MAP_OLD_TO_NEW.md", "SESSION_KICKOFF.md",
         "deploy/W713_AUDIT.md", "deploy/W713_UPGRADE.md", "deploy/W713_PLAN.md",
         "deploy/W712_UPGRADE.md", "deploy/W712_PLAN.md", "deploy/configs/workbuddy-strata166.md",
         "deploy/params/PARAM_REGISTER.tsv", "deploy/params/verify_config.py", "deploy/params/gen_config.py",
         "deploy/scripts/switch_strata.sh", "deploy/scripts/upgrade_gate.sh",
         "deploy/docker/Dockerfile-0.1.41", ".workbuddy/memory/MEMORY.md"]
bad = 0
for f in files:
    d = open(os.path.join(WS, f), "rb").read()
    n = sum(1 for c in d.decode("utf-8") if ord(c) in BAN)
    if n or d.count(b"\r"):
        bad += 1; print("  %-42s CR=%d BAN=%d <== 未达标" % (f, d.count(b"\r"), n))
print("未达标件 =", bad, "（共检 %d 件）" % len(files))
