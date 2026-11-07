import urllib.request, json, base64, re
tok = open("deploy/tmp/_tok.txt").read().strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "albus-audit"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

for ref in ("v0.2.4.2", "main"):
    d = api("/repos/Niko1221/Strata/contents/src/core/arch_defaults.cpp?ref=" + ref)
    s = base64.b64decode(d["content"]).decode("utf-8", "replace")
    i12 = s.find("gfx_arch_is_gfx12(gcn_arch)")
    i11 = s.find("gfx_arch_is_gfx1151(gcn_arch)) return t;")
    seg12 = s[i12:i11] if i12 >= 0 and i11 > i12 else ""
    seg11 = s[i11:] if i11 >= 0 else ""
    seg11 = seg11[:seg11.find("\n}")] if "\n}" in seg11 else seg11
    k12 = re.findall(r'\{"(STRATA_[A-Z0-9_]+)",', seg12)
    k11 = re.findall(r'\{"(STRATA_[A-Z0-9_]+)",', seg11)
    print("%-9s gfx12 %d 项 | gfx1151 %d 项 | 文件 %d 字节" % (ref, len(k12), len(k11), len(s)))
    print("  1151:", ", ".join(k11))
