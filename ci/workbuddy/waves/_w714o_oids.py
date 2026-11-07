# 重新独立坐实两个候选：从 hf-mirror 拉 unsloth 官方仓 与 huihui 仓的 LFS oid（= sha256）
import json, urllib.request

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "Mozilla/5.0"), ("Accept", "application/json")]
BASE = "https://hf-mirror.com/api/models/"
REPOS = {
    "unsloth(官方 base)": "unsloth/Qwen3.8-Flash-Next-GGUF",
    "huihui(abliterated)": "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF",
}


def tree(repo):
    url = BASE + repo + "/tree/main?recursive=true"
    with op.open(url, timeout=45) as r:
        return json.loads(r.read().decode())


for lab, repo in REPOS.items():
    print("=" * 100)
    print("### %s   %s" % (lab, repo))
    try:
        items = tree(repo)
    except Exception as e:
        print("  拉取失败:", repr(e)); continue
    for it in items:
        if it.get("type") != "file":
            continue
        p = it["path"]
        if "IQ4_XS" in p or "mmproj" in p.lower():
            sz = it.get("size")
            oid = ((it.get("lfs") or {}).get("oid") or "(非LFS)")
            print("   %-70s %14s  %s" % (p, sz, oid))
