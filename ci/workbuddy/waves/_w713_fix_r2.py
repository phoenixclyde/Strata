# 审计修复批（第二轮）：register 推 166 + 9 处文档 + 2 个 0 字节件
import base64, collections, hashlib, io, os, subprocess

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
led = []


def rd(p):
    return io.open(os.path.join(WS, p), encoding="utf-8").read()


def wr(p, t):
    io.open(os.path.join(WS, p), "w", encoding="utf-8", newline="\n").write(t)


def rep(p, old, new, tag="", must=1):
    t = rd(p); n = t.count(old)
    if n != must:
        led.append(("MISS", p, "%d!=%d" % (n, must), tag or old[:50])); return False
    wr(p, t.replace(old, new)); led.append(("OK", p, "", tag or old[:50])); return True


def rep_line(p, needle, new_line, tag=""):
    t = rd(p); ls = t.split("\n")
    idx = [i for i, l in enumerate(ls) if needle in l]
    if len(idx) != 1:
        led.append(("MISS", p, "line hits %d" % len(idx), tag or needle[:50])); return False
    ls[idx[0]] = new_line
    wr(p, "\n".join(ls)); led.append(("OK", p, "", tag or needle[:50])); return True


def rep_para(p, prefix, new_para, tag=""):
    t = rd(p); paras = t.split("\n\n")
    idx = [i for i, x in enumerate(paras) if x.lstrip().startswith(prefix)]
    if len(idx) != 1:
        led.append(("MISS", p, "para hits %d" % len(idx), tag or prefix[:50])); return False
    paras[idx[0]] = new_para
    wr(p, "\n\n".join(paras)); led.append(("OK", p, "", tag or prefix[:50])); return True


# ---------- 0) register 推 166（本机 = 真值，166 落后）----------
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
raw = open(REG, "rb").read()
b64 = base64.b64encode(raw).decode("ascii")
s = ("set -u\nD=/home/albus/strata166/params\n"
     "cp -f $D/PARAM_REGISTER.tsv $D/PARAM_REGISTER.tsv.bak_w713fix_$(date +%%Y%%m%%d_%%H%%M%%S)\n"
     "base64 -d > $D/PARAM_REGISTER.tsv <<'__R_EOF__'\n%s\n__R_EOF__\n"
     "echo remote_md5=$(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)\n") % b64
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=120)
print("本机 register md5 =", hashlib.md5(raw).hexdigest())
print(p.stdout.decode("utf-8", "replace").strip())

# ---------- 1) W713_PLAN §0 整段重写（去掉残留旧文 + 计数改 13/11/4 + 指针不指具体行号）----------
rep_para("deploy/W713_PLAN.md", "**当前状态",
         "**当前状态（23:2x，含第二轮对抗性审计后修订）**：生产 = **`strata-gfx906:0.1.41` / 容器 `strata166-405`**（22:35 切换，"
         "中性已验）；**三路独立对抗性审计已完成两轮**（报告 `deploy/W713_AUDIT.md` 与 `deploy/W713_AUDIT2.md`）；"
         "**全量账见 §6**（已做 / 没做 / 重做 三张表，计数以 §6 各表标题为准）。", "§0 状态段")

# ---------- 2) W713_PLAN §2 的 C1 行标完成 ----------
rep_line("deploy/W713_PLAN.md", "| C1 |",
         "| ~~C1~~ | ~~独立对抗性审计重跑~~ **已完成（两轮）**：第一轮 22:2x（`W713_AUDIT.md`，6 条 P1 处置）、"
         "第二轮 23:0x（`W713_AUDIT2.md`，含账本真值分叉等） | 报告见 `deploy/W713_AUDIT*.md` |", "§2 C1 行")

# ---------- 3) §6.1 #4 补上 lend-coverage 关项 ----------
rep("deploy/W713_PLAN.md",
    "| 服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%） |",
    "| 服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%）；**含 0.1.41 新增的 lend-coverage 告警计数 = 0 => 该观察项当场关项** |",
    "§6.1 #4")

# ---------- 4) W713_UPGRADE §3.2：统一单一来源（b1.log）并重算差值 + 补齐 100 档四条 + 加注 token 差 ----------
rep_line("deploy/W713_UPGRADE.md", "| 100（4,593 / 4,604）",
         "| 100（4,593 / 4,604 对 4,589 / 4,600） | 10.80 -> **10.463 s** / **0** | 10.83 -> 10.472 s / 0 | -0.3% / -0.1% |", "§3.2 100 行")
rep_line("deploy/W713_UPGRADE.md", "| 220（9,993 / 10,004）",
         "| 220（9,993 / 10,004 对 9,989 / 10,000） | 22.84 -> **5.786 s** / **8192** | 23.10 -> 5.866 s / 8192 | -1.1% / -1.4% |", "§3.2 220 行")
rep_line("deploy/W713_UPGRADE.md", "| 530（23,943 / 23,954）",
         "| 530（23,943 / 23,954 对 23,939 / 23,950） | 49.67 -> **16.836 s** / **16384** | 50.10 -> 16.990 s / 16384 | -0.9% / -0.9% |", "§3.2 530 行")
rep_line("deploy/W713_UPGRADE.md", "冷预填（引擎自报 tok/s）",
         "冷预填（引擎自报 tok/s，每档四条全给）：100 档 **427.4 / 441.8 / 442.6 / 443.6**（首读最慢）；"
         "220 档 438.3 / 440.0（两次冷读）；530 档 482.6 / 482.8。上版（b1.log）对应：100 档 426.8 / 442.7 / 443.5 / 442.3、"
         "220 档 434.4 / 435.6、530 档 479.7 / 481.0。", "§3.2 冷预填行")
rep("deploy/W713_UPGRADE.md",
    "**判定：中性成立。**",
    "**口径披露（第二轮审计 P1 更正）**：上表对照列**统一取自 `b1.log` 的 A 臂（0.1.40.4）**，"
    "两侧 prompt 长度差 4 token（同脚本不同批），故严格说是「同脚本同参数、非逐字同 prompt」。\n\n**判定：中性成立。**",
    "§3.2 口径披露")

# ---------- 5) W709_HANDOVER §2 加降级标注（上轮漏修的那一处）----------
rep("deploy/W709_HANDOVER.md",
    "1. **可复用的前缀必须与 prefill chunk 对齐**：chunk = 8192（`--prefill auto`）。",
    "1. **可复用的前缀必须与 prefill chunk 对齐**：chunk = 8192（`--prefill auto`）。\n"
    "   **[2026-10-08 审计 P1 更正]** 这是**实测规律、非源码确证**：引擎 help 与源码未见显式「对齐」断言"
    "（\"existing chunk boundary\" 只出现在 `--prompt-cache-tail` 的 help），且 `every=4096`+`chunk=8192` 得 `reused=0` "
    "无法用源码直读解释。引用时请按「实测规律」对待，见 `W713_AUDIT.md` §1 P1-5 与 `W713_AUDIT2.md`。",
    "W709 §2 降级标注")

# ---------- 6) W713_AUDIT.md 更正"6/6 全修"（上轮实际漏了一处）----------
rep("deploy/W713_AUDIT.md",
    "| 处置 | **P1 全部已修并复验**（6/6）；P2 全部已修（14/14）；WEAK 已修或已补判据（5/5） |",
    "| 处置 | **P1 6 条中 5 条当时已修**；**第 6 条（P1-5 的三处点名）只改了两处，漏了 `W709_HANDOVER.md` §2**，"
    "由 2026-10-08 23:0x 第二轮审计（`W713_AUDIT2.md`）抓出并已补修 => 现为 6/6。P2 14/14、WEAK 5/5 |",
    "AUDIT 更正")

# ---------- 7) SESSION_KICKOFF.md：改成"指针式"（下次切换不再过期）----------
rep_line("SESSION_KICKOFF.md", "- 引擎 Strata `v0.1.40.4`",
         "- **现役引擎/镜像/容器一律以 `PROJECT.md` §二 为准**（本件不再写死：2026-10-08 一天内切了两次，"
         "写死必过期）。切换时的现场见 `deploy/W713_UPGRADE.md`。", "KICKOFF 现役行")
rep_line("SESSION_KICKOFF.md", "docker restart -t 30 strata166-404",
         "docker restart -t 30 <PROJECT.md §二 里的现役容器名>", "KICKOFF 通道行")

# ---------- 8) configs 件正文的 -404 -> -405 ----------
CFG = "deploy/configs/workbuddy-strata166.md"
t = rd(CFG)
n404 = t.count("strata166-404")
print("configs 件里 strata166-404 出现 %d 次（正文命令/常驻清单）" % n404)
wr(CFG, t.replace("strata166-404", "strata166-405"))
led.append(("OK", CFG, "替换 %d 处" % n404, "-404 -> -405"))

# ---------- 9) PROJECT.md 通道行 + 回滚行改通用 ----------
rep_line("PROJECT.md", "-> docker restart -t 30 strata166-404",
         "  -> docker restart -t 30 <现役容器，见 §二>", "PROJECT 通道行")
rep("PROJECT.md",
    "`docker stop -t 30 strata166-404 && docker start strata166-402` 即回 0.1.40.2",
    "`bash /home/albus/strata166/w712/switch_strata.sh strata166-404`（通用切换脚本自带停旧/起新/轮询/回滚；"
    "`-404`=0.1.40.4、`-402`=0.1.40.2 均 Exited 保留）",
    "PROJECT 回滚行")

# ---------- 10) 删两个 0 字节件 ----------
for f in ["waves/_pr119.out.txt", "waves/_resid.txt"]:
    fp = os.path.join(WS, f)
    if os.path.exists(fp) and os.path.getsize(fp) == 0:
        os.remove(fp); led.append(("DEL", f, "", "0 字节"))
    else:
        led.append(("SKIP", f, "", "不存在或非 0 字节"))

print("\n=== 台账 ===")
for st, p_, ex, tag in led:
    print("  %-5s %-38s %-10s %s" % (st, p_, ex, tag))
