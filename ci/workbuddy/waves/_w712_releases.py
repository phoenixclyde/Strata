# 拉取上游 Niko1221/Strata 最近 release 列表与变更正文（只读）
import json, urllib.request, os, sys

OUT = r"D:/workbuddy_space/strata_ws/waves/_w712_releases.json"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
opener.addheaders = [("User-Agent", "curl/8.0"), ("Accept", "application/vnd.github+json")]

def get(url):
    with opener.open(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

rels = json.loads(get("https://api.github.com/repos/Niko1221/Strata/releases?per_page=12"))
print("releases fetched:", len(rels))
for r in rels:
    print("%-12s %-22s %s  assets=%d" % (r["tag_name"], r["published_at"], r["name"][:40], len(r.get("assets", []))))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rels, f, ensure_ascii=False, indent=1)
print("saved", OUT)
