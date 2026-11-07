import json, urllib.request

TOK = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus-strata"}


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40) as r:
        return json.load(r)


print("=== 队列里的上游条目：状态是否变了（对比 17:5x 那次） ===")
for n in (3987, 4158, 4283, 3073, 4781, 3264, 3476, 4206):
    d = get("https://api.github.com/repos/Niko1221/Strata/issues/%d" % n)
    pr = d.get("pull_request") or {}
    print("#%-5d %-3s state=%-6s merged=%-24s updated=%s" %
          (n, "PR" if pr else "is", d["state"], str(pr.get("merged_at")), d["updated_at"]))

print()
print("=== 今天有更新的 gfx906 条目（updated:>=2026-10-30） ===")
d = get("https://api.github.com/search/issues?q=repo:Niko1221/Strata+gfx906+updated:%3E=2026-10-30"
        "&sort=updated&order=desc&per_page=30")
print("total=%d" % d.get("total_count", -1))
for it in d.get("items", []):
    kind = "PR" if it.get("pull_request") else "is"
    print("  #%-5d %-3s %-6s %s  %s" % (it["number"], kind, it["state"], it["updated_at"][:16],
                                        it["title"][:78]))

print()
print("=== main 是否前进 ===")
b = get("https://api.github.com/repos/Niko1221/Strata/branches/main")
print("main head=%s  (我们分支基线是 c62d5e3a)" % b["commit"]["sha"][:8])
