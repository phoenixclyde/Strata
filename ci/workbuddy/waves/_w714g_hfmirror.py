# 经 hf-mirror 拉 huihui 两仓的文件清单 + 每文件 size/sha256（lfs oid），并与我们的 base 钉死值对撞
import json, urllib.request, time

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "Mozilla/5.0"), ("Accept", "application/json")]
BASE = "https://hf-mirror.com/api/models/"

PINS = {  # 上游 setup.py 钉死的官方 base UD-IQ4_XS 三片
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf": (10946624, "5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf": (49835229856, "577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7"),
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf": (43836407744, "d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833"),
}


def get(url, timeout=30):
    try:
        with op.open(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return "ERR %r" % (e,)


for repo in ["huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF",
             "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated"]:
    print("=" * 96)
    print("### 仓:", repo)
    tj = get(BASE + repo)
    try:
        d = json.loads(tj)
        print("  gated=%s  license=%s  downloads=%s  likes=%s  lastModified=%s"
              % (d.get("gated"), d.get("cardData", {}).get("license"), d.get("downloads"), d.get("likes"), d.get("lastModified")))
        sib = [s.get("rfilename") for s in d.get("siblings", [])]
        print("  siblings(%d):" % len(sib))
        for s in sib[:40]:
            print("     ", s)
    except Exception as e:
        print("  model JSON 解析失败:", repr(e), tj[:200])

    tr = get(BASE + repo + "/tree/main?recursive=true")
    try:
        items = json.loads(tr)
        print("  --- tree（size / lfs oid 前 16）---")
        for it in items:
            if it.get("type") != "file":
                continue
            sz = it.get("size")
            oid = ((it.get("lfs") or {}).get("oid") or "")[:16]
            nm = it["path"]
            tag = ""
            if nm in PINS:
                psz, psh = PINS[nm]
                full = (it.get("lfs") or {}).get("oid") or ""
                tag = "  <= 与 base 钉死值: size %s / sha256 %s" % (
                    "同" if sz == psz else "异(%s vs %s)" % (sz, psz),
                    "**完全一致**" if full == psh else "不同")
            print("     %-62s %14s  %s%s" % (nm, sz, oid, tag))
    except Exception as e:
        print("  tree 解析失败:", repr(e), tr[:300])
    print()
