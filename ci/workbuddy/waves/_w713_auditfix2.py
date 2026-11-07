# 收尾修复：L139 的错字与禁用码位 + L206 锚点 + SESSION_KICKOFF.md 时效更正
import io, os

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
log = []


def rep(path, old, new, must=1):
    full = os.path.join(WS, path)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        log.append(("MISS", path, "%d!=%d" % (n, must), old[:70])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    log.append(("OK", path, "", old[:70])); return True


rep("deploy/W713_PLAN.md",
    "2. **B1b 已于 22:12 干收尾**（镜像是在它之后才建的）——本条纪律已满足；",
    "2. **B1b 已于 22:12 干净收尾**（0.1.41 镜像是在它之后才建的）；本条纪律已满足；")

rep("deploy/W713_PLAN.md",
    "现已 5 镜像 / 5 容器（0.1.39 / .40.1 / .40.2 / .40.4 / .41）",
    "现已 5 镜像 / 4 容器（镜像 0.1.39 / .40.1 / .40.2 / .40.4 / .41；容器 -401 / -402 / strata166 Exited 保留 + -404 现役）")

rep("SESSION_KICKOFF.md",
    "- 引擎 Strata `v0.1.40.2`（上游 `Niko1221/Strata`）；镜像 `strata-gfx906:0.1.40.2`；容器 `strata166-402`；端口 8090。",
    "- 引擎 Strata `v0.1.40.4`（上游 `Niko1221/Strata`）；镜像 `strata-gfx906:0.1.40.4`；容器 `strata166-404`；端口 8090。\n"
    "  **（2026-10-08 审计后更正**：本件原写 0.1.40.2 / -402，那是 19:38 的快照；现役见 `PROJECT.md` §二。0.1.41 镜像已建待切。）")

rep("SESSION_KICKOFF.md", "docker restart -t 30 strata166-402", "docker restart -t 30 strata166-404")

print("=== 台账 ===")
for st, path, extra, what in log:
    print("  %-5s %-28s %-8s %s" % (st, path, extra, what))

print("\n=== 复验 ===")
for path in ["deploy/W713_PLAN.md", "SESSION_KICKOFF.md", "PROJECT.md", "HANDOVER.md",
             "deploy/W712_UPGRADE.md", "deploy/W713_PLAN.md"]:
    d = open(os.path.join(WS, path), "rb").read()
    t = d.decode("utf-8")
    print("  %-30s CR=%d BAN=%d bytes=%d" % (path, d.count(b"\r"), sum(1 for c in t if ord(c) in BAN), len(d)))
print("残留 0 字节件:", [n for n in os.listdir(WS) if os.path.isfile(os.path.join(WS, n)) and os.path.getsize(os.path.join(WS, n)) == 0])
