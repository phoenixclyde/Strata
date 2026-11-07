# 侦察（只读）：找 D 盘新下载的 UD-IQ4_XS(vision)；查 166 现有布局与"现役在用"的具体文件
import os, subprocess, base64, re, time

WS = r"D:/workbuddy_space/strata_ws"
print("=== 1) D 盘上与 Qwen/Flash/IQ4 相关的目录（深度<=3）===")
roots = ["D:/"]
pat = re.compile(r"qwen|flash|next|iq4|iq4_xs|unsloth", re.I)
seen = 0
for r in roots:
    for dp, dn, fn in os.walk(r):
        depth = dp[len(r):].count(os.sep)
        if depth > 3:
            dn[:] = []
            continue
        # 跳过已知的大目录，避免扫爆
        if any(x in dp.lower() for x in ["workbuddy_space", "\\windows", "/windows", "program files", "$recycle", "system volume"]):
            dn[:] = []
            continue
        for d in list(dn):
            if pat.search(d):
                p = os.path.join(dp, d)
                try:
                    n = sum(len(f) for _x, _y, f in os.walk(p))
                    sz = 0
                    for _x, _y, f in os.walk(p):
                        for ff in f:
                            try: sz += os.path.getsize(os.path.join(_x, ff))
                            except OSError: pass
                except OSError:
                    n, sz = -1, -1
                print("  [dir] %-70s files=%s size=%.2f GB" % (p, n, sz / 1e9))
                seen += 1
        for f in list(fn):
            if pat.search(f) and os.path.getsize(os.path.join(dp, f)) > 1_000_000:
                fp = os.path.join(dp, f)
                print("  [file] %-70s %.2f GB" % (fp, os.path.getsize(fp) / 1e9))
                seen += 1
print("  (命中 %d)" % seen)
