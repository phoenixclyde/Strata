# -*- coding: utf-8 -*-
import io, re, collections

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8").replace("\r\n", "\n")
css = s[s.find("<style"):s.find("</style>")]
vals = re.findall(r"font-size:\s*([0-9.]+)px", css)
print("px sizes:", sorted(set(float(v) for v in vals)))
print("count:", dict(collections.Counter(vals)))
print()
pat = re.compile(r"([^{}\n]+)\{([^{}]*?font-size:\s*([^;}]+))")
keys = (".dv", ".dt", ".dname", ".dmeta", ".dcap", ".dstat", ".tile", ".kpi",
        ".ring .val", ".hsi", ".legend", ".chart")
for m in pat.finditer(css):
    sel = m.group(1).strip()
    if any(k in sel for k in keys):
        print("%-24s %s" % (sel[:24], m.group(3).strip()))
