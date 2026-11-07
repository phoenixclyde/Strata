# 修复 workbuddy-strata166.md：
#   1) 重写本波追加的 §九（上一次经 bash -c + 反引号导致内容被 shell 吃掉，已作废）
#   2) 清掉全文禁用码位（含存量命中），并留下替换台账
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/deploy/configs/workbuddy-strata166.md"
t = io.open(P, encoding="utf-8").read()
before_md5 = hashlib.md5(t.encode("utf-8")).hexdigest()
n_lines_before = t.count("\n")

# ---- 1) 砍掉损坏的 §九，重写 ----
i = t.find("## 九、升级记录")
assert i > 0, "section 9 not found"
t = t[:i].rstrip("\n") + "\n\n"

sec9 = """## 九、升级记录（0.1.40.2 -> 0.1.40.4，2026-10-08）

- 新版时间线：`0.1.40.1`(10-06 09:53) -> `0.1.40.2`(10-07 12:13) -> `0.1.40.3`(10-07 18:01) -> `0.1.40.4`(10-08 08:04)。
- 源码指纹：`strata-src-0.1.40.4.zip` sha256 `7d19b4d5cc8922d4e558f2cddec9a28b7595775ccfb4e6085b02287d95059300`（本机与 166 各自下载、哈希相同）。
- 补丁面与 0.1.40.2 **完全相同**（H1~H4 上游已修 / H5+H6 仍需打），补丁器 `patch_gfx906_402.py`(v3) 一字未改直接复用；
  `LLAMA_CPP_COMMIT` 也未变 => `llama.cpp-3cf0325.tar.gz` 复用。
- 镜像 `strata-gfx906:0.1.40.4`（`8f8f6e87e664` / 6.57 GB）；
  引擎 `/src/build-906/strata` = 24,841,832 B / md5 `b0020081b8292d48c4a555c5f036081b`。
- 切换：20:11:47 停 `strata166-402` -> 20:11:52 起 `strata166-404` -> **20:12:28 ready（35 s）**；
  复验 `verify_config.py` **PASS=15 / FAIL=0**；LIVE config md5 未变
  （`d2b10f0c4e8293ba010614c7acc70bea`，本波未改任何参数）。
- 中性验证：背靠背 A/B（0.1.40.4 vs 0.1.40.2，18,084-token 冷 prompt）实测两版不可分辨，见上面第 5 条。
- 全部细节与证据链：`deploy/W712_UPGRADE.md`；后续方案：`deploy/W712_PLAN.md`。
"""
t = t + sec9

# ---- 2) 清禁用码位（含存量）----
SUB = [("\u2014\u2014", " - "), ("\u2014", "-"), ("\u2192", "->"),
       ("\u2264", "<="), ("\u2265", ">="), ("\u2260", "!="),
       ("\u2212", "-"), ("\u00d7", "x"), ("\u2026", "..."), ("\u21d2", "=>")]
log = []
for a, b in SUB:
    c = t.count(a)
    if c:
        log.append("%-8s -> %-6s  %d 处" % (hex(ord(a[0])) if len(a) == 1 else "U+2014x2", b.strip() or "space", c))
        t = t.replace(a, b)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)

BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
raw = open(P, "rb").read()
print("before md5", before_md5)
print("after  md5", hashlib.md5(raw).hexdigest())
print("bytes %d -> %d, lines %d -> %d" % (len(before_md5 and t.encode('utf-8')), len(raw), n_lines_before, raw.count(b"\n")))
print("CR =", raw.count(b"\r"))
print("BAN =", sum(1 for ch in raw.decode("utf-8") if ord(ch) in BAN))
print("---- substitution ledger ----")
for x in log:
    print("  ", x)
