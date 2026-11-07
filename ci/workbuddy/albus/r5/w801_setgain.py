#!/usr/bin/env python3
# 正确设置 --conversation-cache-park-gain：删掉「参数名 + 紧随其后的非 - 开头 token」，再按需追加
import json, sys
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
FLAG = "--conversation-cache-park-gain"
v = sys.argv[1] if len(sys.argv) > 1 else ""
d = json.load(open(p))
a = list(d.get("args") or [])
out, i, dropped = [], 0, []
while i < len(a):
    if a[i] == FLAG:
        dropped.append(a[i])
        if i + 1 < len(a) and not a[i + 1].startswith("-"):
            dropped.append(a[i + 1]); i += 2
        else:
            i += 1
        continue
    out.append(a[i]); i += 1
if v not in ("", "0"):
    out += [FLAG, v]
d["args"] = out
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("PARK_GAIN=%s dropped=%s tail=%s" % (v or "ABSENT", dropped, out[-4:]))
