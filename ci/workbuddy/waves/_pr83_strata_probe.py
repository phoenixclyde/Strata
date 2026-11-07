import os, json, urllib.request, urllib.error, time

print("=== [1] 现有部署目录 D:/strata166 ===")
R = r"D:/strata166"
if not os.path.isdir(R):
    print("  ABSENT:", R)
else:
    for dp, dn, fn in os.walk(R):
        depth = dp[len(R):].count(os.sep)
        if depth > 2:
            dn[:] = []
            continue
        rel = dp[len(R):] or "\\"
        print("  [%s]  dirs=%d files=%d" % (rel, len(dn), len(fn)))
        for f in sorted(fn)[:25]:
            p = os.path.join(dp, f)
            try:
                sz = os.path.getsize(p)
            except Exception:
                sz = -1
            print("       %-52s %10d" % (f, sz))
        if len(fn) > 25:
            print("       ... (+%d more)" % (len(fn) - 25))

print()
print("=== [2] Strata 最新 release / tag（api.github.com）===")
REPO = "Niko1221/Strata"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 不走代理

def gh(url, timeout=20):
    rq = urllib.request.Request(url, headers={"User-Agent": "routek-client",
                                             "Accept": "application/vnd.github+json"})
    t0 = time.time()
    try:
        with op.open(rq, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode()), time.time() - t0
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read().decode()[:200], time.time() - t0
    except Exception as ex:
        return -1, "%s: %s" % (type(ex).__name__, ex), time.time() - t0

st, d, dt = gh("https://api.github.com/repos/%s/releases?per_page=15" % REPO)
print("  HTTP %s  (%.1fs)" % (st, dt))
if st == 200:
    for r in d[:15]:
        print("    %-14s %-20s %s  assets=%d" % (
            r.get("tag_name"), r.get("published_at", "")[:19],
            (r.get("name") or "")[:34], len(r.get("assets") or [])))
else:
    print("   ", d)

st, d, dt = gh("https://api.github.com/repos/%s/commits?per_page=5" % REPO)
print()
print("  --- main 最近 5 个 commit (HTTP %s, %.1fs) ---" % (st, dt))
if st == 200:
    for c in d:
        print("    %s  %s  %s" % (c["sha"][:10], c["commit"]["committer"]["date"][:19],
                                  c["commit"]["message"].splitlines()[0][:74]))

st, d, dt = gh("https://api.github.com/repos/%s" % REPO)
print()
print("  --- repo meta (HTTP %s) ---" % st)
if st == 200:
    print("    pushed_at=%s  default=%s  stars=%s  archived=%s"
          % (d["pushed_at"], d["default_branch"], d["stargazers_count"], d["archived"]))
