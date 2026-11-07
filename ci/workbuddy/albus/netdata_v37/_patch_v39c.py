# -*- coding: utf-8 -*-
"""v39c：主机卡改成「三组」而不是「四象限」。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

css = '''
  /* --- v39c 主机三组：左=CPU 数值+两条，中=8 瓦片，右=存储+趋势 --- */
  .hostgrid{grid-template-columns:236px minmax(0,1fr) minmax(0,1.18fr);gap:26px;align-items:start;height:auto}
  .hcol-a{display:flex;flex-direction:column;gap:14px}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:38px;font-weight:600;letter-spacing:-.04em;
            font-variant-numeric:tabular-nums;line-height:1}
  .cpunum span{font-size:11px;color:var(--dim2);letter-spacing:.12em}
  .hostbars{display:flex;flex-direction:column;gap:12px}
  .hostgrid .hcol .tiles{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(0,64px);gap:8px}
  .hcol-c{display:flex;flex-direction:column;gap:12px}
'''
s = s.replace("</style>", css.replace("\n", "\r\n") + "</style>", 1)

i = s.find('      <div class="hcol hcol-a">')
j = s.find('      <div class="hcol hcol-c">')
assert i > 0 and j > i

block = '''      <div class="hcol hcol-a">\r
        <div class="cpunum"><b id="host-util">--</b><span>CPU %</span></div>\r
        <div class="hostbars">\r
          <div class="bar">\r
            <div class="lab"><span>CPU 使用率</span><b id="host-cpu-txt">--</b></div>\r
            <div class="track"><i id="host-cpu-bar" style="width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2))"></i></div>\r
          </div>\r
          <div class="bar">\r
            <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>\r
            <div class="track stack">\r
              <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>\r
              <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>\r
            </div>\r
            <div class="sub2" id="host-ram-dtl">--</div>\r
          </div>\r
        </div>\r
      </div>\r
      <div class="hcol hcol-b">\r
        <div class="tiles">\r
          <div class="tile"><div class="k">CPU 温度</div><div class="v" id="host-cput">--<small>°C</small></div></div>\r
          <div class="tile"><div class="k">CPU 功耗</div><div class="v" id="host-cpw">--<small>W</small></div></div>\r
          <div class="tile"><div class="k">CPU 风扇</div><div class="v" id="host-fan">--<small>rpm</small></div></div>\r
          <div class="tile"><div class="k">主板温度</div><div class="v" id="host-mbt">--<small>°C</small></div></div>\r
          <div class="tile"><div class="k">网络接收</div><div class="v" id="host-net-rx">--<small>kbit/s</small></div></div>\r
          <div class="tile"><div class="k">网络发送</div><div class="v" id="host-net-tx">--<small>kbit/s</small></div></div>\r
          <div class="tile"><div class="k">磁盘读</div><div class="v" id="host-io-in">--</div></div>\r
          <div class="tile"><div class="k">磁盘写</div><div class="v" id="host-io-out">--</div></div>\r
        </div>\r
      </div>\r
'''
s = s[:i] + block + s[j:]

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
