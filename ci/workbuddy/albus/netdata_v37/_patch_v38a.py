# -*- coding: utf-8 -*-
"""v38 版面重做（视觉层）—— 2026-11-05 01:2x
机主原话：「真难看，信息重复，空多空少，字体不统一，你整体看啊」。

三条硬毛病与对应改法（对照公开的 dense-dashboard 排版准则：一套字阶不超过 4~5 档、
正文/说明不低于 12px、数字用 tabular-nums 并右对齐、间距走 4/8 网格）：
  1) 信息重复：总览右侧三行（MI50/2070/CPU）把两张显卡卡片里的 温度/功耗/显存/风扇 又抄了一遍，
     而且 GPU 利用率/显存/功耗 在 KPI 与行里出现两三次。
     => 总览只留 8 个**聚合**KPI（一行），删掉三行明细；CPU 功耗/风扇挪进主机卡瓦片，数据不丢。
  2) 空多空少：卡片行高用 1.1fr/0.9fr 硬撑，图表 svg 用 flex:1 吸收全部余量 =>
     两张卡片的图表区各空出 ~200px，页面拉长到 1446。
     => 图表固定 88px，卡片高度由内容决定；`main` 行改为 auto。
  3) 字体不统一：全页 9/9.5/10/10.5/11/11.5/12/12.5/13/13.5/14/18/32 共 13 档。
     => 收到 5 档 token：12(说明) / 13(次值) / 15(紧凑值) / 19(瓦片值) / 30(KPI)，
        磁盘行为「标题+元信息+读写+状态」结构，不再有 9px 标签。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
assert s.count("\r\n") and s.count("\n") == s.count("\r\n"), "行尾不统一，先归一化"

# ============================================================ 1) CSS
css = '''
  /* ===================== v38 版面重做（2026-11-05） =====================
     一条规则一件事，全部写在文件末尾覆盖旧值（旧规则保留可回滚）。
     字阶 5 档：12 说明 / 13 次值 / 15 紧凑值 / 19 瓦片 / 30 KPI。 */
  :root{ --fs-cap:12px; --fs-sub:13px; --fs-row:15px; --fs-tile:19px; --fs-kpi:30px;
         --sp:8px; }
  body{padding:0 16px 16px}
  main{gap:14px;grid-template-rows:auto auto auto}
  .card{padding:16px 20px}
  .chead{margin-bottom:14px}

  /* --- 总览：8 个聚合 KPI 一行 --- */
  .kpis{grid-template-columns:repeat(8,minmax(0,1fr));gap:0 22px}
  .kpi{padding:0}
  .kpi:nth-child(n+5){border-top:0;padding-top:0}
  .kpi .k{font-size:var(--fs-cap);letter-spacing:.2px;color:var(--dim2)}
  .kpi .v{font-size:var(--fs-kpi);margin-top:8px;line-height:1.05;letter-spacing:-.02em}
  .kpi .v small{font-size:var(--fs-cap);margin-left:5px}
  .kpi .sub{font-size:var(--fs-cap);margin-top:8px;color:var(--dim2);letter-spacing:0}

  /* --- 卡片内图表：固定高度，不再吸收空白 --- */
  .card .chart{margin-top:14px;flex:0 0 auto}
  .card .chart svg{flex:0 0 auto;height:88px;min-height:0}
  .card .legend{font-size:var(--fs-cap);margin-top:6px}

  /* --- 瓦片统一：4 列 / 行高 52 / 值 19 --- */
  .tiles{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(0,52px);gap:14px 16px}
  .tile .k{font-size:var(--fs-cap);margin-bottom:4px;letter-spacing:.2px}
  .tile .v{font-size:var(--fs-tile);letter-spacing:-.02em}
  .tile .v small{font-size:var(--fs-cap);margin-left:4px}

  /* --- 主机：三栏（环+条 / 瓦片 / 存储+走势） --- */
  .hostgrid{grid-template-columns:340px minmax(0,1fr) minmax(0,1.32fr);gap:28px}
  .hostgrid .tiles{grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:minmax(0,56px);gap:12px 18px}
  .hostgrid .hostrow{grid-template-columns:132px minmax(0,1fr);gap:18px}
  .hostrow .ring svg{width:112px;height:112px}
  .hostrow .ring .val b{font-size:28px}
  .sub2{font-size:var(--fs-cap);margin-top:6px;letter-spacing:0}

  /* --- 存储行：标题 + 元信息 + 读写 + 状态，无 9px 小标签 --- */
  .diskstrip{flex:0 0 auto;padding-bottom:12px;margin-bottom:0;border-bottom:1px solid var(--line)}
  .drow{display:grid;grid-template-columns:minmax(0,1fr) 92px 92px 64px;gap:14px;align-items:center;padding:7px 0}
  .drow + .drow{border-top:1px solid color-mix(in srgb, var(--line) 55%, transparent)}
  .dname{font-size:var(--fs-sub);font-weight:600;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dmeta{font-size:var(--fs-cap);color:var(--dim2);font-family:var(--mono);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:0}
  .dio .k{font-size:var(--fs-cap);color:var(--dim2);line-height:1}
  .dio .v{font-family:var(--mono);font-size:var(--fs-row);font-weight:600;font-variant-numeric:tabular-nums;margin-top:4px;line-height:1;letter-spacing:-.02em}
  .dio .v small{font-size:11px;color:var(--dim2);font-weight:400;margin-left:3px}
  .dstat{font-size:var(--fs-cap);font-weight:600;text-align:right;letter-spacing:.2px}
  .dstat.ok{color:var(--good)} .dstat.bad{color:var(--bad)} .dstat.na{color:var(--dim2);font-weight:400}

  /* --- 顶端状态条：与卡片正文同级，不再比正文还小 --- */
  .hsi{font-size:var(--fs-cap)}
  .hsi b{font-size:var(--fs-sub)}
  .hsi .hsl{font-size:11px}

  @media (max-width:1500px){
    .kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px 22px}
    .kpi:nth-child(n+5){border-top:0;padding-top:0}
    .hostgrid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
    .hcol-c{grid-column:1 / -1}
  }
'''
s = s.replace("</style>", css + "</style>", 1)

# ============================================================ 2) 总览 HTML
i = s.find('  <section class="card wide" id="card-ov">')
j = s.find('  <section class="card" id="card-amd">')
assert i > 0 and j > i
ov = '''  <section class="card wide" id="card-ov">\r
    <div class="chead">\r
      <span class="badge" style="color:var(--accent);border-color:color-mix(in srgb,var(--accent) 50%,transparent)">OVERVIEW</span>\r
      <h2>总览</h2>\r
      <span class="id" id="ov-id"></span>\r
    </div>\r
    <!-- [v38] 只放**聚合**指标：单卡的 温度/功耗/显存/风扇 归它自己的卡片，不在这里复述。\r
         8 项 ⇄ 两张卡 + 主机卡，每项在页面上只有一处。 -->\r
    <div class="kpis">\r
      <div class="kpi" id="ov-k-power">\r
        <div class="k">整机功耗</div>\r
        <div class="v" id="ov-power">--<small>W</small></div>\r
        <div class="sub" id="ov-power-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-util">\r
        <div class="k">GPU 利用率</div>\r
        <div class="v" id="ov-util">--<small>%</small></div>\r
        <div class="sub" id="ov-util-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-vram">\r
        <div class="k">显存合计</div>\r
        <div class="v" id="ov-vram">--<small>%</small></div>\r
        <div class="sub" id="ov-vram-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-cpu">\r
        <div class="k">CPU 使用率</div>\r
        <div class="v" id="ov-cpu">--<small>%</small></div>\r
        <div class="sub" id="ov-cpu-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-ram">\r
        <div class="k">主机内存</div>\r
        <div class="v" id="ov-ram">--<small>%</small></div>\r
        <div class="sub" id="ov-ram-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-load">\r
        <div class="k">负载 1 分钟</div>\r
        <div class="v" id="ov-load">--</div>\r
        <div class="sub" id="ov-load-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-disk">\r
        <div class="k">磁盘吞吐</div>\r
        <div class="v" id="ov-disk">--</div>\r
        <div class="sub" id="ov-disk-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-net">\r
        <div class="k">网络吞吐</div>\r
        <div class="v" id="ov-net">--</div>\r
        <div class="sub" id="ov-net-sub">--</div>\r
      </div>\r
    </div>\r
  </section>\r
\r
'''
s = s[:i] + ov + s[j:]

# ============================================================ 3) 主机 HTML
i = s.find('  <section class="card wide">\r\n    <div class="chead">\r\n      <span class="badge" style="color:var(--accent2)')
j = s.find('</main>', i)
assert i > 0 and j > i
host = '''  <section class="card wide" id="card-host">\r
    <div class="chead">\r
      <span class="badge" style="color:var(--accent2);border-color:color-mix(in srgb,var(--accent2) 50%,transparent)">HOST</span>\r
      <h2>主机</h2><span class="id" id="host-id"></span>\r
    </div>\r
    <!-- [v38] 三栏：①CPU/内存 ②传感器与网络 ③存储与走势。\r
         瓦片里原来的「系统盘已用/可用」「磁盘读/写」已下掉 —— 那是**重复**：\r
         文件系统占用进了存储行的元信息，读写在存储行里逐盘给出。 -->\r
    <div class="hostgrid">\r
      <div class="hcol hcol-a">\r
        <div class="hostrow">\r
          <div class="ring">\r
            <svg viewBox="0 0 132 132" width="132" height="132">\r
              <circle cx="66" cy="66" r="56" fill="none" stroke="var(--grid)" stroke-width="11"></circle>\r
              <circle id="host-ring" cx="66" cy="66" r="56" fill="none" stroke="var(--accent)" stroke-width="11"\r
                      stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="351.86"></circle>\r
            </svg>\r
            <div class="val"><b id="host-util">--</b><span>CPU %</span></div>\r
          </div>\r
          <div class="hostbars">\r
            <div class="bar">\r
              <div class="lab"><span>CPU</span><b id="host-cpu-txt">--</b></div>\r
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
      </div>\r
      <div class="hcol hcol-b">\r
        <div class="tiles">\r
          <div class="tile"><div class="k">CPU 温度</div><div class="v" id="host-cput">--<small>°C</small></div></div>\r
          <div class="tile"><div class="k">CPU 功耗</div><div class="v" id="host-cpw">--<small>W</small></div></div>\r
          <div class="tile"><div class="k">CPU 风扇</div><div class="v" id="host-fan">--<small>rpm</small></div></div>\r
          <div class="tile"><div class="k">主板温度</div><div class="v" id="host-mbt">--<small>°C</small></div></div>\r
          <div class="tile"><div class="k">网络接收</div><div class="v" id="host-net-rx">--<small>kbit/s</small></div></div>\r
          <div class="tile"><div class="k">网络发送</div><div class="v" id="host-net-tx">--<small>kbit/s</small></div></div>\r
        </div>\r
      </div>\r
      <div class="hcol hcol-c">\r
        <div class="diskstrip" id="disk-rows"><div class="drow"><div><div class="dname">存储</div><div class="dmeta">读取中…</div></div></div></div>\r
        <div class="chart" style="margin-top:12px">\r
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>\r
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存 %</span><span id="host-range" style="margin-left:auto"></span></div>\r
        </div>\r
      </div>\r
    </div>\r
  </section>\r
</main>'''
s = s[:i] + host + s[j + len('</main>'):]

io.open(P, "wb").write(s.encode("utf-8"))
print("HTML/CSS 段完成 bytes=%d" % len(s.encode("utf-8")))
