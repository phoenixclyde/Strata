# -*- coding: utf-8 -*-
"""v40c：把「显存占用」条从右侧列里提出来，横跨整卡。

问题（实测坐标，1920x1078）：
  right col 顶 284 起（含 lab 15 + 条 4 + 12 间距 + 瓦片 116 = 153 高）
  环形 128 在该列里居中 => 297..425，中心 361
  瓦片 321..437，中心 379  => 环形比瓦片高 18px
  肉眼就是「环浮在上面、瓦片沉在下面」，两张卡都这样。

结构改成：条（整卡宽） -> 环 + 瓦片（同排、同一 top） -> 图。
环与瓦片同排后，环 128 对瓦片 116 => 居中差 6px，视觉是一条线。
"""
import io, hashlib, re

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def match_div(t, i):
    """i 指向一个 <div ...> 的开头，返回其配对的 </div> 之后的位置。"""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", t[i:]):
        if m.group(0) == "</div>":
            depth -= 1
            if depth == 0:
                return i + m.end()
        else:
            depth += 1
    raise ValueError("unbalanced")


def dedent(block):
    lines = block.split("\n")
    pad = min((len(l) - len(l.lstrip(" ")) for l in lines if l.strip()), default=0)
    return [l[pad:] if l.strip() else "" for l in lines]


def reind(block, n):
    pre = " " * n
    return "\n".join((pre + l) if l.strip() else l for l in dedent(block))


def rebuild(t, search_from):
    A = t.find('<div class="top">', search_from)
    assert A > 0
    line_start = t.rfind("\n", 0, A) + 1
    ind = A - line_start

    ring_s = t.find('<div class="ring">', A)
    ring_e = match_div(t, ring_s)
    bar_s = t.find('<div class="bar">', ring_e)
    bar_e = match_div(t, bar_s)
    tiles_s = t.find('<div class="tiles">', bar_e)
    tiles_e = match_div(t, tiles_s)
    top_e = match_div(t, A)

    ring = t[ring_s:ring_e]
    bar = t[bar_s:bar_e]
    tiles = t[tiles_s:tiles_e]

    out = []
    out.append(reind(bar, ind))
    out.append(" " * ind + '<div class="top">')
    out.append(reind(ring, ind + 2))
    out.append(reind(tiles, ind + 2))
    out.append(" " * ind + "</div>")
    return t[:line_start] + "\n".join(out) + t[top_e:]


# 从后往前替换，避免偏移错位
s = rebuild(s, s.find('<section class="card" id="card-nvd">'))
s = rebuild(s, s.find('<section class="card" id="card-amd">'))

# .top 现在是「环 + 瓦片」同排；瓦片不再需要上边距
s = s.replace("""    .top{display:grid;grid-template-columns:128px minmax(0,1fr);gap:20px;align-items:center;flex:0 0 auto}""",
              """    .top{display:grid;grid-template-columns:128px minmax(0,1fr);gap:20px;align-items:center;
         flex:0 0 auto;margin-top:12px}
    .top > .tiles{margin-top:0}""")

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
