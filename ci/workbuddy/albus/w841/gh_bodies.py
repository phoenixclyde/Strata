import json, re, urllib.request

TOK = open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "albus-strata"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40) as r:
        return json.load(r)


for n in (4158, 3987, 4206, 4283, 4781, 3073, 3264, 3476, 3913, 2883, 4156, 3094):
    try:
        d = get("https://api.github.com/repos/Niko1221/Strata/issues/%d" % n)
    except Exception as e:
        print("#%d ERR %s" % (n, e)); continue
    pr = d.get("pull_request") or {}
    print("=" * 78)
    print("#%d %s state=%s merged_at=%s" % (n, "PR" if pr else "issue", d["state"], pr.get("merged_at")))
    print("title: %s" % d["title"])
    body = (d.get("body") or "")
    body = re.sub(r"\r", "", body)
    print("body[:1100]:\n%s" % body[:1100])
