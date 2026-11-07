# -*- coding: utf-8 -*-
"""v38f：CSS 清理 —— 删掉已无对应元素的死规则，把仍生效的字号收进 5 档。
动机（机主："字体不统一"）：全表 18 个字号值。其中 .ovgpu*（总览三行已删）、
.ssdgrid/.ssdrow/.ssdcell（存储独立卡已删）、.dcell*（改为 .dio/.dmeta）都是死规则，
但留在源码里会误导后续维护者，也让"到底几档"看不出来。
"""
import io, re, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

i = s.find("<style>"); j = s.find("</style>")
css = s[i:j]

DEAD = ("#ov-gpus", ".ovgpu", ".ssdgrid", ".ssdrow", ".ssdname", ".ssdcell", ".dcell", ".dname .t", ".dname .s")

def drop_rules(css, prefixes):
    out, k, removed = [], 0, 0
    while True:
        m = re.compile(r"([^{}]+)\{").search(css, k)
        if not m:
            out.append(css[k:]); break
        sel = m.group(1).strip()
        # 找匹配的右括号（本文件内无嵌套，取第一个 }）
        end = css.find("}", m.end())
        if any(sel.startswith(p) for p in prefixes):
            out.append(css[k:m.start()])
            k = end + 1
            removed += 1
        else:
            out.append(css[k:end + 1])
            k = end + 1
    return "".join(out), removed

css2, n = drop_rules(css, DEAD)
print("删除死规则", n, "条")

# 字号归一：仍生效的 <12px 文本抬到 12（.hsl 分组标签与 .legend 例外，保留 11）
bumps = [
    (".chead .id{font-size:11px", ".chead .id{font-size:12px"),
    (".ring .val span{font-size:10px", ".ring .val span{font-size:11px"),
    (".bar .lab{display:flex;justify-content:space-between;align-items:baseline;font-size:11.5px",
     ".bar .lab{display:flex;justify-content:space-between;align-items:baseline;font-size:12px"),
    (".bar .lab b{color:var(--text);font-family:var(--mono);font-size:12.5px",
     ".bar .lab b{color:var(--text);font-family:var(--mono);font-size:13px"),
    (".legend{display:flex;align-items:center;gap:14px;font-size:10.5px",
     ".legend{display:flex;align-items:center;gap:14px;font-size:11px"),
    (".chip{", ".chip{"),
]
for a, b in bumps:
    if a != b and a in css2:
        css2 = css2.replace(a, b, 1)

s = s[:i] + css2 + s[j:]
io.open(P, "wb").write(s.encode("utf-8"))

vals = sorted(set(re.findall(r"font-size:([0-9.]+)px", css2)), key=float)
print("剩余字号档位:", vals)
print("CSS 花括号:", css2.count("{"), css2.count("}"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
