# -*- coding: utf-8 -*-
"""v53：走势图改成「上下两条独立泳道」——各自基线，避免零值线与中线重合看不出几条线"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


i0 = s.find("// 磁盘卡里的读/写走势（镜像双向）。")
i1 = s.find("function renderSSD(){")
assert i0 > 0 and i1 > i0

NEW_SPARK = "\n".join([
    '// 磁盘卡里的读/写走势：**上下两条独立泳道**，各自一条基线。',
    '// [!] netdata 的 disk.io 里 writes 是负值（镜像双向图，reads 在 0 上方、writes 在 0 下方）。',
    '//   旧实现直接拿原值算 y，负的写值全落到画布外被 viewBox 裁掉 => 屏上只剩一条线，',
    '//   「到底几条线」都说不清（2026-11-05 机主指出）。现在一律取绝对值。',
    '// [!] 也不能让两条道共用一条零线：某一路恒为 0 时它的折线正好压在零线上，',
    '//   看上去又变成"一条线"。所以上道（读）基线在 1/2 上方、下道（写）基线在 1/2 下方，',
    '//   中间留 6px 空隙，两条基线本身用各自颜色画一根 26% 的细线 —— 恒零也看得出"这条是 0"。',
    '// [!] 面积与描边分开画：闭合填充路径的收边段也会被描边，会把基线描成彩色粗线。',
    'function sparkSvg(st, W, H, floor){',
    '  var out = { svg: "", pkR: 0, pkW: 0, n: 0 };',
    '  if (!st || !st.rows || st.rows.length < 2) return out;',
    '  var cr = colOf(st, "reads"), cw = colOf(st, "writes");',
    '  if (cr < 0) return out;',
    '  var rs = st.rows, n = rs.length, i, a, b;',
    '  var gap = 6, laneH = Math.max(6, (H - gap) / 2);',
    '  var baseR = laneH, baseW = laneH + gap;',
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
    '    var col = up ? "var(--accent)" : "var(--warn)", base = up ? baseR : baseW;',
    '    var k, v, x, y, line = "", area = "";',
    '    for (k = 0; k < n; k++){',
    '      v = Math.abs(+rs[k][c] || 0);',
    '      x = (k / (n - 1) * W).toFixed(2);',
    '      y = (up ? base - v / sc * laneH : base + v / sc * laneH).toFixed(2);',
    '      line += (k ? "L" : "M") + x + " " + y;',
    '      area += (k ? "L" : "M") + x + " " + y;',
    '    }',
    '    var o = \'<line x1="0" y1="\' + base + \'" x2="\' + W + \'" y2="\' + base',
    '      + \'" stroke="\' + col + \'" stroke-opacity=".26" stroke-width="1" \'',
    '      + \'vector-effect="non-scaling-stroke"/>\';',
    '    if (pk > 0){',
    '      o += \'<path d="\' + area + \'L\' + W + " " + base + "L0 " + base + \'Z" fill="\' + col',
    '        + \'" fill-opacity=".14" stroke="none"/>\';',
    '    }',
    '    o += \'<path d="\' + line + \'" fill="none" stroke="\' + col',
    '      + \'" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" \'',
    '      + \'vector-effect="non-scaling-stroke"/>\';',
    '    return o;',
    '  }',
    '  out.svg = \'<svg class="dspark" viewBox="0 0 \' + W + \' \' + H + \'" preserveAspectRatio="none" aria-hidden="true">\'',
    '    + band(cr, sR, out.pkR, true) + band(cw, sW, out.pkW, false)',
    '    + \'</svg>\';',
    '  return out;',
    '}',
    '',
])
s = s[:i0] + NEW_SPARK + s[i1:]

rep('        + spurTitle if False else "      var spTitle = "近 60 秒读写速率：读画在零线上方（峰值 " + rateTxt(sp.pkR || 0)',
    '      var spTitle = "近 60 秒读写速率：读画在上道（峰值 " + rateTxt(sp.pkR || 0)') if False else None

# 说明文案同步成"泳道"说法
rep('        + "），写画在零线下方（峰值 " + rateTxt(sp.pkW || 0) + "）。"',
    '        + "），写画在下道（峰值 " + rateTxt(sp.pkW || 0) + "）。"')

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
