# 最后三处：配置件两行 + 该件指向的旧方案 + W712_UPGRADE 的禁用码位
import io, os

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
log = []


def rep(path, old, new, must=1):
    full = os.path.join(WS, path)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != must:
        log.append(("MISS", path, "%d!=%d" % (n, must), old[:60])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    log.append(("OK", path, "", old[:60])); return True


rep("deploy/configs/workbuddy-strata166.md",
    "可能的解法是把 chunk 调小（`--prefill 4096`，引擎 help 支持显式尺寸），但**尚未实测**，\n"
    "已列为下一步 B1b（见 `deploy/W712_PLAN.md`）。",
    "解法是把 chunk 调小（`--prefill 4096`，引擎 help 支持显式尺寸）：**B1b 已实测**，"
    "4.6k 会话温 TTFT 10.58 -> 3.59 s（冷预填 -11%），但**尚未采纳**"
    "（未在 0.1.41 复核、答案是否变未测）。现行方案与全量账见 `deploy/W713_PLAN.md`。")

rep("deploy/configs/workbuddy-strata166.md",
    "- 全部细节与证据链：`deploy/W712_UPGRADE.md`；后续方案：`deploy/W712_PLAN.md`。",
    "- 全部细节与证据链：`deploy/W712_UPGRADE.md`；**后续方案：`deploy/W713_PLAN.md`**（`W712_PLAN.md` 已被取代）。")

rep("deploy/W712_UPGRADE.md", " 的口径 —— 故本条只判", " 的口径，故本条只判")

for st, path, extra, what in log:
    print("  %-5s %-38s %-8s %s" % (st, path, extra, what))

print("\n=== 全交付件 CR/BAN 终检 ===")
files = ["PROJECT.md", "HANDOVER.md", "MAP_OLD_TO_NEW.md", "SESSION_KICKOFF.md",
         "deploy/W712_UPGRADE.md", "deploy/W712_PLAN.md", "deploy/W713_PLAN.md",
         "deploy/W709_HANDOVER.md", "deploy/W709_PARAM_OPTIMUM.md",
         "deploy/configs/workbuddy-strata166.md", "deploy/params/PARAM_REGISTER.tsv",
         "deploy/params/verify_config.py", "deploy/params/gen_config.py",
         "deploy/scripts/_w712_switch_404.sh", "deploy/scripts/_w712_b1_cacheevery.sh",
         "deploy/scripts/_w712_b1b_chunk.sh", "deploy/docker/Dockerfile-0.1.41",
         ".workbuddy/memory/MEMORY.md"]
bad = 0
for p in files:
    fp = os.path.join(WS, p)
    if not os.path.exists(fp):
        print("  %-46s 不存在" % p); bad += 1; continue
    d = open(fp, "rb").read()
    n = sum(1 for c in d.decode("utf-8") if ord(c) in BAN)
    flag = "" if (n == 0 and d.count(b"\r") == 0) else "  <== 未达标"
    if flag: bad += 1
    print("  %-46s CR=%d BAN=%d%s" % (p, d.count(b"\r"), n, flag))
print("未达标件数 =", bad)
