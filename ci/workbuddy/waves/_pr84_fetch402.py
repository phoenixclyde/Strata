import os, json, base64, urllib.request, urllib.error, time

REPO = "Niko1221/Strata"
REF = "v0.1.40.2"
OUT = r"D:/strata166/upstream/v0.1.40.2"
os.makedirs(OUT, exist_ok=True)
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def gh(url, timeout=60, raw=False):
    rq = urllib.request.Request(url, headers={"User-Agent": "routek-client",
                                             "Accept": "application/vnd.github+json"})
    try:
        with op.open(rq, timeout=timeout) as resp:
            b = resp.read()
            return resp.status, (b if raw else json.loads(b.decode()))
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode()[:200]
    except Exception as ex:
        return -1, "%s: %s" % (type(ex).__name__, ex)

FILES = [
    "src/kernels/cuda/fused_gr.cu",
    "src/core/mtp.cpp",
    "src/core/vmm.cpp",
    "include/strata/platform/hip_compat/strata_hip.h",
]

print("=== [1] 拉 %s 的 4 个关键文件 ===" % REF, flush=True)
for f in FILES:
    url = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, f, REF)
    t0 = time.time()
    st, d = gh(url)
    if st != 200:
        print("  [!!] %-52s HTTP %s %s" % (f, st, str(d)[:120]), flush=True)
        continue
    content = d.get("content")
    if content:
        raw = base64.b64decode(content)
        name = f.replace("/", "__")
        open(os.path.join(OUT, name), "wb").write(raw)
        print("  [ok] %-52s %8d B  (%.1fs)" % (f, len(raw), time.time() - t0), flush=True)
    else:
        print("  [??] %-52s no inline content, download_url=%s" % (f, d.get("download_url")), flush=True)

print()
print("=== [2] PR / issue 状态（gfx906 编译相关）===", flush=True)
for num in (1083, 1187, 1084):
    st, d = gh("https://api.github.com/repos/%s/pulls/%d" % (REPO, num))
    if st == 200:
        print("  PR #%-5d %-8s merged=%s  %s" % (num, d["state"], d.get("merged"),
                                                d["title"][:64]), flush=True)
        print("           updated=%s  head=%s" % (d["updated_at"][:19], d["head"]["label"]), flush=True)
    else:
        # 可能是 issue 而非 PR
        st2, d2 = gh("https://api.github.com/repos/%s/issues/%d" % (REPO, num))
        if st2 == 200:
            print("  #%-6d (issue) %-8s %s" % (num, d2["state"], d2["title"][:64]), flush=True)
            print("           updated=%s" % d2["updated_at"][:19], flush=True)
        else:
            print("  #%-6d HTTP %s" % (num, st), flush=True)

print()
print("=== [3] 列出落盘文件 ===", flush=True)
for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print("  %-56s %9d B" % (f, os.path.getsize(p)), flush=True)
