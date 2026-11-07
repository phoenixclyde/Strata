# -*- coding: utf-8 -*-
"""List phoenixclyde repos/branches and how far each is behind its upstream."""
import json
import urllib.request
import os

TOK = open(r"D:\workbuddy_space\strata_ws\deploy\tmp\_tok.txt").read().strip()


def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "token " + TOK,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-w863"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


print("=== phoenixclyde repos ===")
repos = api("/users/phoenixclyde/repos?per_page=100&sort=updated")
for r in repos:
    print("  %-28s fork=%-5s pushed=%s  default=%s" % (r["name"], r["fork"], r["pushed_at"], r["default_branch"]))

for repo in ("Strata",):
    print("\n=== phoenixclyde/%s branches ===" % repo)
    brs = api("/repos/phoenixclyde/%s/branches?per_page=100" % repo)
    for b in brs:
        c = b["commit"]
        print("  %-32s %s  %s" % (b["name"], c["sha"][:8], c["commit"]["message"].split("\n")[0][:70]))

    print("\n=== Niko1221/%s branches ===" % repo)
    try:
        ups = api("/repos/Niko1221/%s/branches?per_page=100" % repo)
        for b in ups:
            c = b["commit"]
            print("  %-32s %s  %s" % (b["name"], c["sha"][:8], c["commit"]["message"].split("\n")[0][:70]))
    except Exception as e:
        print("  FAIL", e)

    print("\n=== compare: our branch vs upstream default ===")
    up_repo = api("/repos/Niko1221/%s" % repo)
    default = up_repo["default_branch"]
    print("  upstream default:", default, "pushed:", up_repo["pushed_at"])
