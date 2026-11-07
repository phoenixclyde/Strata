# -*- coding: utf-8 -*-
"""v43：主机卡内部分工与显卡卡拉平
左半 = 环 + 内存条 + 8 瓦片 + 走势（与显卡卡完全同构）
右半 = 两张**独立磁盘卡**，左右并排、撑满整个高度
"""
import io, hashlib, re

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


# ---------- 1) 主机卡 HTML ----------
NEW = '''<section class="card wide" id="card-host">
    <div class="chead">
      <span class="badge" style="color:var(--accent2)">HOST</span>
      <h2>主机</h2><span class="id" id="host-id"></span>
    </div>
    <div class="hostgrid">
      <div class="hostleft">
        <div class="top">
          <div class="ring">
            <svg viewBox="0 0 132 132" width="132" height="132">
              <circle cx="66" cy="66" r="56" fill="none" stroke="var(--grid)" stroke-width="11"></circle>
              <circle id="host-ring" cx="66" cy="66" r="56" fill="none" stroke="var(--accent)" stroke-width="11"
                      stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="351.86"></circle>
            </svg>
            <div class="val"><b id="host-util">--</b><span>利用率 %</span></div>
          </div>
          <div class="gr">
            <div class="bar">
              <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>
              <div class="track stack">
                <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
                <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>
              </div>
            </div>
            <div class="subline">
              <span class="sub2" id="host-ram-dtl">--</span>
              <span class="hload">负载<b id="host-load1">--</b><b id="host-load5">--</b><b id="host-load15">--</b></span>
            </div>
            <div class="tiles">
              <div class="tile"><div class="k">CPU 温度</div><div class="v" id="host-cput">--<small>°C</small></div></div>
              <div class="tile"><div class="k">CPU 功耗</div><div class="v" id="host-cpw">--<small>W</small></div></div>
              <div class="tile"><div class="k">CPU 风扇</div><div class="v" id="host-fan">--<small>rpm</small></div></div>
              <div class="tile"><div class="k">主板温度</div><div class="v" id="host-mbt">--<small>°C</small></div></div>
              <div class="tile"><div class="k">网络接收</div><div class="v" id="host-net-rx">--<small>kbit/s</small></div></div>
              <div class="tile"><div class="k">网络发送</div><div class="v" id="host-net-tx">--<small>kbit/s</small></div></div>
              <div class="tile"><div class="k">磁盘读</div><div class="v" id="host-io-in">--</div></div>
              <div class="tile"><div class="k">磁盘写</div><div class="v" id="host-io-out">--</div></div>
            </div>
          </div>
          <!-- CPU 条与环内数字同源，保留节点供 JS 写入但不显示 -->
          <div class="bar" hidden><div class="track"><i id="host-cpu-bar" style="width:0%"></i></div></div>
        </div>
        <div class="chart">
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存 %</span><span id="host-range" style="margin-left:auto"></span></div>
        </div>
      </div>
      <div class="hostright">
        <div class="dcards" id="disk-rows"><div class="dcard"><div class="dhead2"><span class="dname">存储</span></div><div class="dmeta">读取中…</div></div></div>
      </div>
    </div>
  </section>'''

i = s.find('<section class="card wide" id="card-host">')
j = s.find("</section>", i) + len("</section>")
s = s[:i] + NEW + s[j:]

# ---------- 2) CSS ----------
rep("""  .hostright{gap:10px;justify-content:space-between}""",
    """  /* 右半只剩两张磁盘卡：左右并排、撑满整高 */
  .hostright{min-height:0}""")
rep("""  .hostright .tiles{grid-auto-rows:48px;margin-top:0}""",
    """  .subline{display:flex;align-items:baseline;justify-content:space-between;gap:14px;
           min-width:0;margin-top:-2px}
  .hload{display:inline-flex;align-items:baseline;gap:8px;font-size:10px;color:var(--dim2);
         white-space:nowrap;flex:0 0 auto}
  .hload b{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--text);
           font-variant-numeric:tabular-nums}""")

# 旧 .hload 规则整块删除
m = re.search(r"  \.hload\{display:flex;align-items:baseline;gap:26px;.*?\n  \.hram \.lab\{[^}]*\}\n", s, re.S)
assert m, "旧 hload 未找到"
s = s[:m.start()] + s[m.end():]

# 磁盘卡：并排 + 撑满 + 竖向分布
rep("  .dcards{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;flex:0 0 auto}",
    "  .dcards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;height:100%}")
rep("""  .dcard{min-width:0;padding:9px 12px 10px;border-radius:8px;
         background:var(--tile-bg);border:1px solid var(--line-soft);
         display:flex;flex-direction:column;gap:0}""",
    """  .dcard{min-width:0;padding:12px 14px;border-radius:8px;
         background:var(--tile-bg);border:1px solid var(--line-soft);
         display:flex;flex-direction:column;justify-content:space-between;gap:10px}
  .dcap .cap{display:flex;align-items:baseline;justify-content:space-between;
             font-size:10px;color:var(--dim2);margin-bottom:6px}
  .dcap .cap b{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text)}
  .dfoot{display:flex;align-items:baseline;justify-content:space-between;
         border-top:1px solid var(--line-soft);padding-top:8px;
         font-size:10px;color:var(--dim2)}
  .dfoot b{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text);
           margin-left:4px}""")
rep("  .dvals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px}",
    "  .dvals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 10px}")

# ---------- 3) renderSSD：卡片内容撑满 ----------
OLD = re.search(r"      html \+= '<div class=\"dcard\">'.*?\+ '</div>';", s, re.S)
assert OLD, "renderSSD 行未找到"
NEWROW = """      var capTxt = usedPct === null ? "--" : fmt(usedPct, 1) + "%";
      html += '<div class="dcard">'
        + '<div>'
        +   '<div class="dhead2"><span class="dname">' + model + '</span>'
        +     '<span class="dstat ' + hCls + '">' + hTxt + '</span></div>'
        +   '<div class="dmeta">' + [x.key, hasNum(m.cap) ? bytes(m.cap) : null, x.tag]
                                   .filter(function(z){ return z; }).join(" · ") + '</div>'
        + '</div>'
        + '<div class="dcap">'
        +   '<div class="cap"><span>容量占用</span><b>' + capTxt + '</b></div>'
        +   '<div class="track"><i style="width:' + (usedPct === null ? 0 : usedPct) + '%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i></div>'
        + '</div>'
        + '<div class="dvals">'
        +   '<div class="dv"><span>读</span><b>' + rateTxt(rd) + '</b></div>'
        +   '<div class="dv"><span>写</span><b>' + rateTxt(wr) + '</b></div>'
        +   '<div class="dv"><span>温度</span><b>' + fmt(m.temp, 0) + '<small>°C</small></b></div>'
        +   '<div class="dv' + lifeLvl + '" title="' + lifeTitle + '"><span>寿命</span><b>'
        +     (life === null ? "--" : fmt(life, 0)) + '<small>%</small></b></div>'
        + '</div>'
        + '<div class="dfoot"><span>已写入<b>' + (hasNum(m.written) ? fmt(m.written / 1e9, 0) + " GB" : "--") + '</b></span>'
        +   '<span>通电<b>' + (hasNum(m.hours) ? fmt(m.hours, 0) + " h" : "--") + '</b></span></div>'
        + '</div>';"""
s = s[:OLD.start()] + NEWROW + s[OLD.end():]

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
