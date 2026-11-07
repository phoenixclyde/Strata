import json, os, sys, urllib.request

TOK = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "albus-strata"}


def get(url):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def one(n):
    try:
        d = get("https://api.github.com/repos/Niko1221/Strata/issues/%d" % n)
        kind = "PR" if d.get("pull_request") else "issue"
        print("#%-5d %-5s %-8s %s" % (n, kind, d.get("state"), (d.get("title") or "")[:95]))
        print("        merged=%s closed=%s updated=%s comments=%d"
              % (d.get("pull_request", {}).get("merged_at"), d.get("closed_at"),
                 d.get("updated_at"), d.get("comments", 0)))
    except Exception as e:
        print("#%-5d ERR %s" % (n, repr(e)[:80]))


print("=== 定点核查 ===")
for n in (4283, 4781, 3073, 4766, 3986, 4474, 4420, 4051, 4616, 4159, 3779, 4766):
    one(n)

print()
print("=== 仓库概览 ===")
r = get("https://api.github.com/repos/Niko1221/Strata")
print("default_branch=%s pushed_at=%s open_issues=%s" % (r["default_branch"], r["pushed_at"], r["open_issues_count"]))
b = get("https://api.github.com/repos/Niko1221/Strata/branches/main")
print("main head=%s" % b["commit"]["sha"][:8])

print()
print("=== 搜 gfx906 ===")
for page in (1, 2):
    q = "https://api.github.com/search/issues?q=repo:Niko1221/Strata+gfx906&per_page=50&page=%d&sort=updated&order=desc" % page
    d = get(q)
    print("total=%d page=%d" % (d.get("total_count", -1), page))
    for it in d.get("items", []):
        kind = "PR" if it.get("pull_request") else "is"
        print("  #%-5d %-3s %-6s %-10s %s" % (it["number"], kind, it["state"],
                                             (it.get("closed_at") or "")[:10],
                                             it["title"][:88]))
