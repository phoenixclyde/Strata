# -*- coding: utf-8 -*-
"""v51：磁盘卡走势图重做（修「写」为负值被裁 + 加图例 + 说明表征）"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


# ---------------- 1) sparkSvg：镜像双向 + 绝对值 + 各自归一 ----------------
i0 = s.find("// 磁盘卡里的读/写走势：直接用已取到的 disk.io 序列画 polyline")
i1 = s.find("function renderSSD(){")
assert i0 > 0 and i1 > i0

NEW_SPARK = "\n".join([
    '// 磁盘卡里的读/写走势（镜像双向）。',
    '// [!] netdata 的 disk.io 里 writes 是负值：这是一张镜像双向图，reads 画在 0 上方、writes 画在 0 下方。',
    '//   旧实现直接拿原值算 y，负的写值全落到画布外、被 viewBox 裁掉 => 屏上只剩一条线，',
    '//   「到底几条线」都说不清（2026-11-05 机主指出）。现在一律取绝对值，并按方向各自归一。',
    'function sparkSvg(st, W, H){',
    '  var out = { svg: "", pkR: 0, pkW: 0, n: 0 };',
    '  if (!st || !st.rows || st.rows.length < 2) return out;',
    '  var cr = colOf(st, "reads"), cw = colOf(st, "writes");',
    '  if (cr < 0) return out;',
    '  var rs = st.rows, n = rs.length, i, a, b;',
    '  var mid = H / 2, half = H / 2 - 1;',
    '  for (i = 0; i < n; i++){',
    '    a = Math.abs(+rs[i][cr] || 0); b = Math.abs(+rs[i][cw] || 0);',
    '    if (a > out.pkR) out.pkR = a;',
    '    if (b > out.pkW) out.pkW = b;',
    '  }',
    '  out.n = n;',
    '  function band(c, pk, up){',
    '    if (!(pk > 0)) return "";',
    '    var d = "", k, v, x, y, col = up ? "var(--accent)" : "var(--warn)";',
    '    for (k = 0; k < n; k++){',
    '      v = Math.abs(+rs[k][c] || 0);',
    '      x = (k / (n - 1) * W).toFixed(2);',
    '      y = (up ? mid - v / pk * half : mid + v / pk * half).toFixed(2);',
    '      d += (k ? "L" : "M") + x + " " + y;',
    '    }',
    '    d += "L" + W + " " + mid + "L0 " + mid + "Z";',
    '    return \'<path d="\' + d + \'" fill="\' + col + \'" fill-opacity=".18" stroke="\' + col',
    '      + \'" stroke-width="1.2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>\';',
    '  }',
    '  out.svg = \'<svg class="dspark" viewBox="0 0 \' + W + \' \' + H + \'" preserveAspectRatio="none" aria-hidden="true">\'',
    '    + \'<line x1="0" y1="\' + mid + \'" x2="\' + W + \'" y2="\' + mid + \'" stroke="var(--line)" \'',
    '    +   \'stroke-width="1" vector-effect="non-scaling-stroke"/>\'',
    '    + band(cr, out.pkR, true) + band(cw, out.pkW, false)',
    '    + \'</svg>\';',
    '  return out;',
    '}',
    '',
])
s = s[:i0] + NEW_SPARK + s[i1:]

# ---------------- 2) 读/写两行加色点（就地充当图例） ----------------
OLD_DV = (
    "        +   '<div class=\"dv\"><span>读</span><b>' + rateTxt(rd) + '</b></div>'\n"
    "        +   '<div class=\"dv\"><span>写</span><b>' + rateTxt(wr) + '</b></div>'"
)
NEW_DV = (
    "        +   '<div class=\"dv\"><span><i class=\"dot rd\"></i>读</span><b>' + rateTxt(rd) + '</b></div>'\n"
    "        +   '<div class=\"dv\"><span><i class=\"dot wr\"></i>写</span><b>' + rateTxt(wr) + '</b></div>'"
)
rep(OLD_DV, NEW_DV)

# ---------------- 3) 走势块：顶部小标题 + 空态 ----------------
OLD_BOX = (
    "        + '<div class=\"dsparkbox\" title=\"近 60 s 读写（蓝=读 橙=写，纵轴按本盘峰值归一）\">'"
    " + sparkSvg(s, 400, 60) + '</div>'"
)
NEW_BOX = (
    "        + '<div class=\"dsparkbox\" title=\"' + spTitle + '\">'\n"
    "        +   '<span class=\"spk-t\">近 60 s 速率</span>'\n"
    "        +   (sp.svg || '<span class=\"spk-empty\">近 60 s 无读写</span>')\n"
    "        + '</div>'"
)
rep(OLD_BOX, NEW_BOX)

# 在 capPair 之后插入 spark 计算
OLD_CAP = (
    '      var capPair = (capGiB !== null && usedPct !== null)\n'
    '        ? "(" + fmt(capGiB * usedPct / 100, 0) + " / " + fmt(capGiB, 0) + " GiB)" : "";'
)
NEW_CAP = OLD_CAP + "\n" + "\n".join([
    '      // 走势：读画零线上方、写画零线下方（netdata 的 disk.io 本就是镜像双向图），',
    '      // 两侧各自按本方向峰值归一 —— 否则 3 GiB/s 的读会把 40 KiB/s 的写压成一条直线。',
    '      var sp = sparkSvg(s, 400, 64);',
    '      var spTitle = "近 60 秒读写速率：读画在零线上方（峰值 " + rateTxt(sp.pkR || 0)',
    '        + "），写画在零线下方（峰值 " + rateTxt(sp.pkW || 0) + "）。"',
    '        + "两条线各自按本方向峰值归一，只看形状与变化，不要横向比高低；绝对量看上面「读 / 写」两行。";',
])
rep(OLD_CAP, NEW_CAP)

# ---------------- 4) CSS ----------------
rep("  .dsparkbox{flex:1 1 auto;min-height:44px;display:flex;align-items:stretch}",
    "\n".join([
        "  /* 走势块：右上角小标题绝对定位，不吃高度；无 IO 时给空态说明 */",
        "  .dsparkbox{position:relative;flex:1 1 auto;min-height:44px;display:flex;align-items:stretch}",
        "  .spk-t{position:absolute;right:0;top:-2px;font-size:10px;color:var(--dim2);",
        "         letter-spacing:.02em;pointer-events:none;background:var(--tile-bg);padding-left:6px}",
        "  .spk-empty{position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);",
        "             text-align:center;font-size:10px;color:var(--dim2);pointer-events:none}",
    ]))

rep("  .dv span{font-size:10px;color:var(--dim2);letter-spacing:.02em;white-space:nowrap}",
    "\n".join([
        "  .dv span{font-size:10px;color:var(--dim2);letter-spacing:.02em;white-space:nowrap}",
        "  /* 色点＝走势图图例：与下方两条线颜色一一对应，不额外占一行 */",
        "  .dv .dot{display:inline-block;width:7px;height:4px;border-radius:1px;margin-right:6px;vertical-align:2px}",
        "  .dv .dot.rd{background:var(--accent)}",
        "  .dv .dot.wr{background:var(--warn)}",
    ]))

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
