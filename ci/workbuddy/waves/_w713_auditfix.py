# W713 审计后修复批：文档一致性（逐处 count==1 断言 + 完成后 CR/BAN 复验）+ 清 6 个 0 字节残留
import hashlib, io, os, subprocess, base64, glob

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
REPORT = []

# ---- 0) 取 b1b.log 里三档的实测 token（用于把"约 1,125"换成真值）----
s = "grep -oE 'prompt [0-9]+ tokens' /home/albus/strata166/w712/b1b.log | sort -u | head -20"
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=90)
pts = sorted(int(x.split()[1]) for x in p.stdout.decode("utf-8", "replace").splitlines() if x.startswith("prompt "))
print("b1b.log 实测 prompt token 集合:", pts)

# ---- 1) 定点替换表 ----
def rep(path, old, new, must=1):
    full = os.path.join(WS, path)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        REPORT.append(("MISS", path, "%d!=%d" % (n, must), old[:60]))
        return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    REPORT.append(("OK", path, "", old[:60]))
    return True


rep("deploy/W712_UPGRADE.md",
    "`PARAM_REGISTER.tsv` 一字未动（md5 仍 `a91b677ea13905cb36ef56fa6224c36d`，35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7）。",
    "register 的**值/状态一字未动**；§3.2 收口时把 B1 的边界结论写进了 P34 的 evidence/verdict"
    "（md5 `a91b677e...` -> `3bf819e3ccd3f54ed454154b14c3eb3f`，仍 35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7；"
    "重新 `gen_config --write` 后生产 config **逐字节未变**）。")

rep("deploy/W712_UPGRADE.md",
    "| MTP draft 接受（COLD 臂） |",
    "| MTP draft 接受（COLD 15/17 与 WARM 19/24 各一） |")

rep("deploy/W713_PLAN.md",
    "**B1b 已于 22:12 收尾**",
    "**B1b 已于 22:12 收尾**")   # 占位：若上一步已改则 MISS，用于探测

rep("deploy/W713_PLAN.md",
    "2. **B1b 正在跑**（0.1.40.4 上）=> **必须等它收尾**再建镜像/切换：",
    "2. **B1b 已于 22:12 干收尾**（镜像是在它之后才建的）——本条纪律已满足；日后若并发跑波，仍须等它收尾再建镜像/切换：")

rep("deploy/W713_PLAN.md",
    "`-402`(0.1.40.2) / `-404`(0.1.40.4) 均 `Exited` 可一键起回",
    "`-401` / `-402` / `strata166` 均 `Exited` 保留（**现役 `-404` 不在此列**：它在下次切换后才会变成旧件）")

rep("deploy/W713_PLAN.md",
    "现已 5 镜像 / 5 容器（0.1.39/.40.1/.40.2/.40.4/.41）",
    "现已 5 镜像 / 4 容器（镜像 0.1.39/.40.1/.40.2/.40.4/.41；容器 -401/-402/strata166 Exited + -404 现役）")

rep("deploy/W713_PLAN.md",
    "`deploy/logs/_w727.out.txt`",
    "`waves/_w727.out.txt`")

if pts:
    lo = [x for x in pts if x < 3000]
    rep("deploy/W713_PLAN.md", "档（实测 token）", "档（PARAS 段数）")
    if lo:
        rep("deploy/W713_PLAN.md", "| 25（约 1,125） |", "| 25（实测 %s token） |" % "/".join(str(x) for x in lo[:2]))

rep("deploy/W713_PLAN.md",
    "| 读日志即得，顺手做 |",
    "| 判据：`grep -c 'lend coverage' 166:data/strata-ud-iq4_xs.log`，>0 记证据并入账，=0 即关项 |")

rep("PROJECT.md", "-> docker restart -t 30 strata166-402", "-> docker restart -t 30 strata166-404")
rep("HANDOVER.md", "容器 `strata166-402` 是否 `Up`", "容器 `strata166-404` 是否 `Up`")

# ---- 2) SESSION_KICKOFF.md：先报计数再定 ----
sk = io.open(os.path.join(WS, "SESSION_KICKOFF.md"), encoding="utf-8").read()
print("\nSESSION_KICKOFF.md: 'strata166-402' x%d, '0.1.40.2' x%d, 'strata-gfx906:0.1.40.2' x%d"
      % (sk.count("strata166-402"), sk.count("0.1.40.2"), sk.count("strata-gfx906:0.1.40.2")))
for ln in sk.splitlines():
    if "strata166-402" in ln or "0.1.40.2" in ln:
        print("   |", ln[:150])

# ---- 3) 清 6 个 0 字节残留 ----
junk = ["写于", "升级实施与自证见", "所有性能读数一律", "本件", "环境声明：本件所有现场读数均在", "编码规范：本件"]
for n in junk:
    fp = os.path.join(WS, n)
    if os.path.exists(fp) and os.path.getsize(fp) == 0:
        os.remove(fp)
        REPORT.append(("DEL", n, "", "0 字节残留"))
    else:
        REPORT.append(("SKIP", n, "", "不存在或非 0 字节"))

print("\n=== 修复台账 ===")
for st, path, extra, what in REPORT:
    print("  %-5s %-32s %-10s %s" % (st, path, extra, what))

# ---- 4) 复验 CR/BAN ----
print("\n=== 触达件 CR/BAN 复验 ===")
for path in ["PROJECT.md", "HANDOVER.md", "deploy/W712_UPGRADE.md", "deploy/W713_PLAN.md"]:
    d = open(os.path.join(WS, path), "rb").read()
    t = d.decode("utf-8")
    n = sum(1 for c in t if ord(c) in BAN)
    print("  %-30s CR=%d BAN=%d bytes=%d" % (path, d.count(b"\r"), n, len(d)))
