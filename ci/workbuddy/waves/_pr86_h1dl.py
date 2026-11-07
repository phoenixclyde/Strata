import io, os, re, time, urllib.request, urllib.error

FG = r"D:/strata166/upstream/v0.1.40.2/src__kernels__cuda__fused_gr.cu"
t = io.open(FG, encoding="utf-8", errors="replace").read()
L = t.split("\n")

print("=== [1] H1 精确验证：fused_gr_read_multi 函数体 ===")
start = None
for i, l in enumerate(L):
    if re.match(r"\s*bool\s+fused_gr_read_multi\s*\(", l):
        start = i
        break
print("  函数起始行 =", start + 1 if start is not None else "NOT FOUND")
if start is not None:
    # 打印到函数结束（第一个行首单独 '}'）
    end = start
    for j in range(start + 1, min(len(L), start + 260)):
        if L[j] == "}":
            end = j
            break
    for j in range(start, end + 1):
        mark = ""
        if "STRATA_HIP_GFX906" in L[j]:
            mark = "   <== GFX906"
        if re.search(r"\breturn\b", L[j]):
            mark += "   <== RETURN"
        print("  %5d| %s%s" % (j + 1, L[j][:126], mark))
    print("  ---")
    print("  split_on 出现 =", t.count("split_on"))

print()
print("=== [2] 上一版(0.1.40.1)同函数对照 ===")
FGOLD = r"D:/strata166/upstream/v0.1.40.1/src__kernels__cuda__fused_gr.cu"
if os.path.isfile(FGOLD):
    to = io.open(FGOLD, encoding="utf-8", errors="replace").read()
    Lo = to.split("\n")
    s2 = None
    for i, l in enumerate(Lo):
        if re.match(r"\s*bool\s+fused_gr_read_multi\s*\(", l):
            s2 = i
            break
    if s2 is not None:
        for j in range(s2, min(len(Lo), s2 + 70)):
            if re.search(r"\breturn\b|STRATA_HIP_GFX906|split_on", Lo[j]):
                print("  %5d| %s" % (j + 1, Lo[j][:126]))
else:
    print("  0.1.40.1 副本不存在")

print()
print("=== [3] 下载 v0.1.40.2 源码 zip（gh-proxy）===")
DST = r"D:/strata166/transfer/strata-src-0.1.40.2.zip"
URL = "https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/v0.1.40.2.zip"
if os.path.isfile(DST) and os.path.getsize(DST) > 1_000_000:
    print("  已存在，跳过:", DST, os.path.getsize(DST), "B")
else:
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        t0 = time.time()
        rq = urllib.request.Request(URL, headers={"User-Agent": "routek-client"})
        with op.open(rq, timeout=300) as resp:
            data = resp.read()
        open(DST, "wb").write(data)
        dt = time.time() - t0
        print("  OK  %d B  (%.1fs, %.2f MB/s)" % (len(data), dt, len(data) / dt / 1e6))
        print("  ->", DST)
    except urllib.error.HTTPError as ex:
        print("  HTTPError", ex.code)
    except Exception as ex:
        print("  ERR", type(ex).__name__, ex)
