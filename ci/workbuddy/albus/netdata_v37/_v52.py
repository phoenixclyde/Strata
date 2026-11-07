# -*- coding: utf-8 -*-
"""v52：磁盘卡走势图打磨 —— 填充/描边分离、纵轴稳定、标题让位、方向说明"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


# ---------------- 1) sparkSvg 重写：面积与折线分开画 + 纵轴带衰减下限 ----------------
i0 = s.find("// 磁盘卡里的读/写走势（镜像双向）。")
i1 = s.find("function renderSSD(){")
assert i0 > 0 and i1 > i0

NEW_SPARK = "\n".join([
    '// 磁盘卡里的读/写走势（镜像双向）。',
    '// [!] netdata 的 disk.io 里 writes 是负值：这是一张镜像双向图，reads 画在 0 上方、writes 画在 0 下方。',
    '//   旧实现直接拿原值算 y，负的写值全落到画布外被 viewBox 裁掉 => 屏上只剩一条线，',
    '//   「到底几条线」都说不清（2026-11-05 机主指出）。现在一律取绝对值，并按方向各自归一。',
    '// [!] 面积与描边必须分开画：闭合填充路径的最后一段（回到零线）也会被描边，',
    '//   结果零线被画成一条 1.4px 的彩色粗线（实测截图可见），看着像"第三条线"。',
    'function sparkSvg(st, W, H, floor){',
    '  var out = { svg: "", pkR: 0, pkW: 0, n: 0 };',
    '  if (!st || !st.rows || st.rows.length < 2) return out;',
    '  var cr = colOf(st, "reads"), cw = colOf(st, "writes");',
    '  if (cr < 0) return out;',
    '  var rs = st.rows, n = rs.length, i, a, b;',
    '  var mid = H / 2, half = Math.max(1, H / 2 - 1);',
    '  for (i = 0; i < n; i++){',
    '    a = Math.abs(+rs[i][cr] || 0); b = Math.abs(+rs[i][cw] || 0);',
    '    if (a > out.pkR) out.pkR = a;',
    '    if (b > out.pkW) out.pkW = b;',
    '  }',
    '  out.n = n;',
    '  if (!(out.pkR > 0) && !(out.pkW > 0)) return out;   // 整窗无 IO：交给空态文案',
    '  // 纵轴下限＝上一轮刻度 ×0.88 衰减：否则峰值一变（每 2 s）全图就整体跳一下，趋势没法看',
    '  var sR = Math.max(out.pkR, (floor && floor.r) || 0) || 1;',
    '  var sW = Math.max(out.pkW, (floor && floor.w) || 0) || 1;',
    '  function band(c, sc, pk, up){',
    '    var col = up ? "var(--accent)" : "var(--warn)", k, v, x, y, line = "", area = "";',
    '    for (k = 0; k < n; k++){',
    '      v = Math.abs(+rs[k][c] || 0);',
    '      x = (k / (n - 1) * W).toFixed(2);',
    '      y = (up ? mid - v / sc * half : mid + v / sc * half).toFixed(2);',
    '      line += (k ? "L" : "M") + x + " " + y;',
    '      area += (k ? "L" : "M") + x + " " + y;',
    '    }',
    '    var o = "";',
    '    if (pk > 0){',
    '      o += \'<path d="\' + area + \'L\' + W + " " + mid + "L0 " + mid + \'Z" fill="\' + col',
    '        + \'" fill-opacity=".14" stroke="none"/>\';',
    '    }',
    '    o += \'<path d="\' + line + \'" fill="none" stroke="\' + col',
    '      + \'" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" \'',
    '      + \'vector-effect="non-scaling-stroke"/>\';',
    '    return o;',
    '  }',
    '  out.svg = \'<svg class="dspark" viewBox="0 0 \' + W + \' \' + H + \'" preserveAspectRatio="none" aria-hidden="true">\'',
    '    + \'<line x1="0" y1="\' + mid + \'" x2="\' + W + \'" y2="\' + mid + \'" stroke="var(--line)" \'',
    '    +   \'stroke-width="1" vector-effect="non-scaling-stroke"/>\'',
    '    + band(cr, sR, out.pkR, true) + band(cw, sW, out.pkW, false)',
    '    + \'</svg>\';',
    '  return out;',
    '}',
    '',
])
s = s[:i0] + NEW_SPARK + s[i1:]

# ---------------- 2) 调用处：接入纵轴下限状态 ----------------
OLD_CAP = (
    '      var sp = sparkSvg(s, 400, 64);'
)
NEW_CAP = "\n".join([
    '      state.spark = state.spark || {};',
    '      var spPrev = state.spark[x.key] || { r: 0, w: 0 };',
    '      var sp = sparkSvg(s, 400, 64, spPrev);',
    '      state.spark[x.key] = { r: Math.max(sp.pkR, spPrev.r * 0.88),',
    '                             w: Math.max(sp.pkW, spPrev.w * 0.88) };',
])
rep(OLD_CAP, NEW_CAP)

# ---------------- 3) 走势块头部：左「近 60 s」右「上读 / 下写」 ----------------
OLD_BOX = (
    "        + '<div class=\"dsparkbox\" title=\"' + spTitle + '\">'\n"
    "        +   '<span class=\"spk-t\">近 60 s 速率</span>'\n"
    "        +   (sp.svg || '<span class=\"spk-empty\">近 60 s 无读写</span>')\n"
    "        + '</div>'"
)
NEW_BOX = (
    "        + '<div class=\"dsparkbox\" title=\"' + spTitle + '\">'\n"
    "        +   '<div class=\"spk-hd\"><span>近 60 s</span>'\n"
    "        +     '<span><i class=\"dot rd\"></i>上 读　<i class=\"dot wr\"></i>下 写</span></div>'\n"
    "        +   (sp.svg || '<span class=\"spk-empty\">近 60 s 无读写</span>')\n"
    "        + '</div>'"
)
rep(OLD_BOX, NEW_BOX)

# ---------------- 4) CSS：绝对定位改回流排版 ----------------
rep("  .dsparkbox{position:relative;flex:1 1 auto;min-height:44px;display:flex;align-items:stretch}",
    "\n".join([
        "  /* 走势块：标题改回流小行（绝对定位会压在图上），图吃剩余高度 */",
        "  .dsparkbox{position:relative;flex:1 1 auto;min-height:52px;display:flex;",
        "             flex-direction:column;gap:3px}",
        "  .spk-hd{display:flex;align-items:center;justify-content:space-between;",
        "          font-size:10px;color:var(--dim2);line-height:1;letter-spacing:.02em;white-space:nowrap}",
    ]))

rep("""  .spk-t{position:absolute;right:0;top:-2px;font-size:10px;color:var(--dim2);
         letter-spacing:.02em;pointer-events:none;background:var(--tile-bg);padding-left:6px}
""", "")

# 色点选择器去作用域：卡片头（.spk-hd）里也要用
rep("  .dv .dot{display:inline-block;width:7px;height:4px;border-radius:1px;margin-right:6px;vertical-align:2px}",
    "  .dot{display:inline-block;width:7px;height:4px;border-radius:1px;margin-right:5px;vertical-align:2px}")
rep("  .dv .dot.rd{background:var(--accent)}", "  .dot.rd{background:var(--accent)}")
rep("  .dv .dot.wr{background:var(--warn)}", "  .dot.wr{background:var(--warn)}")

rep("  .dspark{width:100%;height:100%;min-height:44px;display:block;opacity:.85}",
    "  .dspark{width:100%;flex:1 1 0;height:0;min-height:34px;display:block}")

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
