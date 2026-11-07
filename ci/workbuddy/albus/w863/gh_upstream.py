# -*- coding: utf-8 -*-
"""What is the latest upstream state?  Authoritative: the GitHub API, not a local fetch."""
import json
import urllib.request

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()


def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "token " + TOK,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-w863"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


for repo in ("Niko1221/Strata", "phoenixclyde/Strata"):
    print("=" * 70)
    print(repo)
    info = api("/repos/" + repo)
    print("  default_branch =", info["default_branch"], " pushed_at =", info["pushed_at"])
    for br in ("main",):
        b = api("/repos/%s/branches/%s" % (repo, br))
        c = b["commit"]
        print("  %s -> %s  %s" % (br, c["sha"][:12], c["commit"]["author"]["date"]))
        print("      %s" % c["commit"]["message"].split("\n")[0][:110])

    print("  tags:")
    tags = api("/repos/%s/tags?per_page=10" % repo)
    for t in tags:
        print("    %-10s %s" % (t["name"], t["commit"]["sha"][:12]))

    print("  latest commits on default branch:")
    cs = api("/repos/%s/commits?per_page=6&sha=%s" % (repo, info["default_branch"]))
    for c in cs:
        print("    %s %s  %s" % (c["sha"][:10], c["commit"]["author"]["date"][:16],
                                 c["commit"]["message"].split("\n")[0][:78]))

    try:
        rel = api("/repos/%s/releases?per_page=5" % repo)
        print("  releases:", [(r["tag_name"], r["published_at"][:10]) for r in rel] or "none")
    except Exception as e:
        print("  releases: n/a", e)
