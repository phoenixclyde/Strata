# 终批：PROJECT.md / configs 件 同步新事实（容器 -406、LIVE md5、模型路径）+ MEMORY.md（技能规程）
import hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
led = []


def rep(p, old, new, tag=""):
    full = os.path.join(WS, p)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != 1:
        led.append(("MISS", p, "%d" % n, tag or old[:44])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    led.append(("OK", p, "", tag or old[:44])); return True


# 1) PROJECT.md：LIVE md5 + 模型路径行
rep("PROJECT.md", "（当前 md5 `d2b10f0c4e8293ba010614c7acc70bea`）",
    "（当前 md5 `69aa8607bd0a58dc79466b1b71d6a4f9`；2026-10-08 因 `--native` 改指 /models 而变化）",
    "PROJECT LIVE md5")
t = io.open(os.path.join(WS, "PROJECT.md"), encoding="utf-8").read()
row = [l for l in t.splitlines() if "/home/albus/strata166/params/" in l]
if row:
    print("  §三 现有 params 行:", row[0][:120])
rep("PROJECT.md", "| `/home/albus/strata166/build-ctx-402/` | 0.1.40.2 构建上下文 |",
    "| `/home/albus/strata166/build-ctx-402/` | 0.1.40.2 构建上下文（历史） |\n"
    "| `/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/` | **模型权重（2026-10-08 起）**：3 分片 + `mmproj-Qwen3.8-Flash-Next-BF16.gguf`；"
    "容器挂 `/models:ro`；`/home/albus/strata166/weights` 现为指向此处的符号链接（保旧容器回滚） |",
    "PROJECT 模型路径行") or None

# 2) configs 件：容器名 -405 -> -406（多处）
CFG = os.path.join(WS, "deploy/configs/workbuddy-strata166.md")
c = io.open(CFG, encoding="utf-8").read()
n405 = c.count("strata166-405")
if n405:
    io.open(CFG, "w", encoding="utf-8", newline="\n").write(c.replace("strata166-405", "strata166-406"))
    led.append(("OK", "configs", "替换 %d 处" % n405, "-405 -> -406"))
else:
    led.append(("MISS", "configs", "0", "-405 命中 0"))

for x in led:
    print("  %-5s %-34s %-10s %s" % x)

# 3) MEMORY.md（先备份 + 五断言 + 报数）
MEM = os.path.join(WS, ".workbuddy", "memory", "MEMORY.md")
old = io.open(MEM, encoding="utf-8").read()
bak = os.path.join(WS, ".workbuddy", "memory", "_bak", "MEMORY.md.bak_w714_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(MEM, bak)
new = old.replace("| **`strata-gfx906:0.1.41` / `strata166-405`**", "| **`strata-gfx906:0.1.41` / `strata166-406`**") \
         .replace("**`strata-gfx906:0.1.41` / `strata166-405`**", "**`strata-gfx906:0.1.41` / `strata166-406`**")
if "strata166-406" not in new:
    # 兜底：按实际字符串改
    import re
    new = re.sub(r"strata166-405", "strata166-406", old)
new = new.replace("`--native`", "`--native`", 1)
fails = []
if "\r" in new: fails.append("CR")
if len(new) > 2900: fails.append("chars=%d" % len(new))
if sum(1 for c_ in new if ord(c_) in BAN): fails.append("BAN")
if not new.endswith("\n"): fails.append("结尾换行")
print("MEMORY 断言:", fails if fails else "[]  容器名含 -406:", "strata166-406" in new)
if not fails:
    io.open(MEM, "w", encoding="utf-8", newline="\n").write(new)
    b = open(MEM, "rb").read()
    print("MEMORY 报数：chars=%d headroom=%d md5=%s（备份 %s）"
          % (len(new), 3000 - len(new), hashlib.md5(b).hexdigest(), os.path.basename(bak)))

# 4) 终检
print("=== 终检 ===")
for p in ["PROJECT.md", "deploy/configs/workbuddy-strata166.md", ".workbuddy/memory/MEMORY.md",
          "deploy/params/PARAM_REGISTER.tsv"]:
    d = open(os.path.join(WS, p), "rb").read()
    n = sum(1 for c_ in d.decode("utf-8") if ord(c_) in BAN)
    print("  %-44s CR=%d BAN=%d bytes=%d" % (p, d.count(b"\r"), n, len(d)))
print("   仍含 -405 的文件:", [p for p in ["PROJECT.md", "deploy/configs/workbuddy-strata166.md", ".workbuddy/memory/MEMORY.md"]
                              if "strata166-405" in io.open(os.path.join(WS, p), encoding="utf-8").read()])
