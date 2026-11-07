# 取 v0.1.41 完整 release 正文 + 下载源码 + 全树比对 + 补丁面复核（全部本机，不碰 166）
import json, urllib.request, os, hashlib, zipfile, time, difflib, io

TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"
TMP = r"D:/workbuddy_space/strata_ws/deploy/tmp"
OUT = os.path.join(TMP, "_w713_relnote.txt")
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "curl/8.0"), ("Accept", "application/vnd.github+json")]

rel = json.loads(op.open("https://api.github.com/repos/Niko1221/Strata/releases/tags/v0.1.41", timeout=30).read().decode())
body = rel["body"]
io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
print("release body chars:", len(body), "->", OUT)
print("assets:", [(a["name"], a["size"]) for a in rel.get("assets", [])])
print()
print(body[2400:9000])
