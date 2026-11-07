# -*- coding: utf-8 -*-
"""v39 整体重设计（不是打补丁）——
机主两次否定后，改的是**构图**，不是字号：

1) 减少"盒子"：4 张卡 -> 3 张。总览不再是一张卡片，而是标题下的**记分板**（无边框、无底色、组间竖线），
   视觉上从"又一个面板"变成"仪表盘头"。卡片只留给内容（两张卡 + 主机）。
2) 建立层级：记分板 6 项（34px）> 卡内主值（22px）> 标签（11px 字距放宽）。原来 8 个等大数字 = 一堵墙。
   磁盘/网络从记分板移回主机卡瓦片 —— 它们本来就是主机指标，放上面只是重复。
3) 瓦片加"底"：rgba 白 2.5% + 10px 圆角 + 内边距，让数字有落脚点；原来数字是浮在背景上的。
4) 图表去噪：5 条虚线网格 -> 1 条基线 + 1 条中线（极淡），加面积渐变；虚线网格是这张图看起来"脏"的主因。
5) 主机卡改两栏（1.15fr / 1fr）：左 = 环比条 + 8 瓦片；右 = 存储表 + 走势。原来三栏三种密度，左右失衡。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
assert s.count("\r\n") == s.count("\n"), "行尾不统一，先归一化"

# ============================================================ 1) CSS
css = '''
  /* ===================== v39 设计系统（覆盖 v38） =====================
     一套尺度：间距 4 的倍数；字号 6 档（11/12/15/22/34/40）；所有数字 tabular。
     卡片三件套统一：标题 24 高 + 内容 + 20 padding。 */
  :root{
    --fs-cap:11.5px;   /* 标签 / 元信息 */
    --fs-sub:13px;     /* 次值 */
    --fs-tile:22px;    /* 卡内主值 */
    --fs-kpi:34px;     /* 记分板 */
    --fs-hero:40px;    /* 环形 */
    --tilebg:rgba(255,255,255,.028);
    --tilebg-h:rgba(255,255,255,.05);
    --pad:20px;
  }
  body{padding:0 20px 12px}
  main{gap:16px}
  .card{padding:var(--pad);border-radius:14px}
  .chead{margin-bottom:16px;min-height:24px;align-items:center}
  .chead h2{font-size:15px;letter-spacing:.01em}
  .chead .badge{font-size:10.5px;letter-spacing:.12em;padding:3px 8px}
  .chead .id{font-size:11.5px;color:var(--dim2);letter-spacing:.02em}

  /* --- 记分板：不是卡片 --- */
  #card-ov{background:none;border:0;box-shadow:none;padding:6px 0 2px;border-radius:0}
  #card-ov::before{content:none}
  #card-ov .chead{display:none}
  .kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:0}
  .kpi{padding:2px 26px}
  .kpi + .kpi{border-left:1px solid var(--line)}
  .kpi:first-child{padding-left:2px;border-left:0}
  .kpi.grp{border-left-color:var(--line2)}
  .kpi .k{font-size:var(--fs-cap);letter-spacing:.1em;color:var(--dim2);text-transform:uppercase}
  .kpi .v{font-size:var(--fs-kpi);margin-top:10px;line-height:1;letter-spacing:-.03em}
  .kpi .v small{font-size:12px;margin-left:6px;color:var(--dim2);letter-spacing:0}
  .kpi .sub{font-size:11.5px;margin-top:9px;color:var(--dim2);letter-spacing:0}

  /* --- 瓦片：给数字一个底 --- */
  .tiles{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(0,64px);gap:10px}
  .tile{background:var(--tilebg);border:1px solid rgba(255,255,255,.05);border-radius:10px;
        padding:10px 12px;display:flex;flex-direction:column;justify-content:center;min-width:0}
  .tile:hover{background:var(--tilebg-h)}
  .tile .k{font-size:11px;color:var(--dim2);margin-bottom:6px;letter-spacing:.06em;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .tile .v{font-size:var(--fs-tile);letter-spacing:-.03em;line-height:1.05}
  .tile .v small{font-size:11px;margin-left:4px;color:var(--dim2);letter-spacing:0}

  /* --- 环形：主值 40px --- */
  .ring .val b{font-size:var(--fs-hero)}
  .ring .val span{font-size:11px;letter-spacing:.1em;color:var(--dim2)}
  .bar .lab{font-size:11.5px;letter-spacing:.04em}
  .bar .lab b{font-size:13px}
  .sub2{font-size:11px;margin-top:7px;letter-spacing:0}

  /* --- 主机：两栏 --- */
  .hostgrid{grid-template-columns:minmax(0,1.18fr) minmax(0,1fr);gap:24px;height:100%}
  .hostgrid .hcol .tiles{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(0,62px);gap:10px}
  .hostrow{grid-template-columns:112px minmax(0,1fr);gap:20px}

  /* --- 存储表 --- */
  .diskstrip{padding-bottom:12px;margin-bottom:12px;border-bottom:1px solid var(--line)}
  .drow{grid-template-columns:minmax(0,1fr) 76px 76px 58px 58px 54px;gap:10px;padding:8px 0}
  .drow + .drow{border-top:1px solid rgba(255,255,255,.04)}
  .dname{font-size:12.5px;font-weight:600;letter-spacing:-.01em}
  .dmeta{font-size:11px;color:var(--dim2);margin-top:3px;letter-spacing:0}
  .dio .k{font-size:11px;color:var(--dim2);letter-spacing:.06em}
  .dio .v{font-size:15px;margin-top:5px;letter-spacing:-.02em}
  .dio .v small{font-size:10.5px;margin-left:2px}
  .dstat{font-size:11.5px;letter-spacing:.04em}

  /* --- 图表：去噪 --- */
  .card .chart{margin-top:12px}
  .card .chart svg{height:76px;min-height:76px;max-height:150px}
  .legend{font-size:11px;gap:16px;letter-spacing:.02em;margin-top:8px}

  /* --- 顶端状态条：更淡、更小、成组 --- */
  .hstat{gap:10px 18px;margin-top:14px;padding-top:14px}
  .hsg{gap:12px}
  .hsg > .hsl{font-size:10px;letter-spacing:.1em;opacity:.75}
  .hsi{font-size:11.5px;gap:5px}
  .hsi b{font-size:12px;letter-spacing:0}
  .hsi i{width:5px;height:5px}

  @media (max-width:1400px){
    .kpis{grid-template-columns:repeat(3,minmax(0,1fr));row-gap:14px}
    .kpi:nth-child(4){border-left:0;padding-left:2px}
    .hostgrid{grid-template-columns:minmax(0,1fr)}
  }
'''
s = s.replace("</style>", css.replace("\n", "\r\n") + "</style>", 1)

# ============================================================ 2) 总览 -> 记分板 6 项
i = s.find('  <section class="card wide" id="card-ov">')
j = s.find('  <section class="card" id="card-amd">')
assert i > 0 and j > i
score = '''  <section class="card wide" id="card-ov">\r
    <div class="chead"><h2>总览</h2><span class="id" id="ov-id"></span></div>\r
    <!-- [v39] 记分板：6 项、无边框、组间竖线。磁盘/网络已移回主机卡瓦片（它们本来就是主机指标，\r
         放在这里只是把主机卡的数抄一遍）。 -->\r
    <div class="kpis">\r
      <div class="kpi" id="ov-k-power">\r
        <div class="k">整机功耗</div>\r
        <div class="v" id="ov-power">--<small>W</small></div>\r
        <div class="sub" id="ov-power-sub">--</div>\r
      </div>\r
      <div class="kpi grp" id="ov-k-util">\r
        <div class="k">GPU 利用率</div>\r
        <div class="v" id="ov-util">--<small>%</small></div>\r
        <div class="sub" id="ov-util-sub">--</div>\r
      </div>\r
      <div class="kpi" id="ov-k-vram">\r
        <div class="k">显存合计</div>\r
        <div class="v" id="ov-vram">--<small>%</small></div>\r
        <div class="sub" id="ov-vram-sub">--</div>\r
      </div>\r
      <div class="kpi grp" id="ov-k-cpu">\r
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
    </div>\r
  </section>\r
\r
'''
s = s[:i] + score + s[j:]

# ============================================================ 3) 主机 -> 两栏
i = s.find('  <section class="card wide" id="card-host">')
j = s.find('</main>', i)
assert i > 0 and j > i
host = '''  <section class="card wide" id="card-host">\r
    <div class="chead">\r
      <span class="badge" style="color:var(--accent2);border-color:color-mix(in srgb,var(--accent2) 45%,transparent)">HOST</span>\r
      <h2>主机</h2><span class="id" id="host-id"></span>\r
    </div>\r
    <div class="hostgrid">\r
      <div class="hcol hcol-a">\r
        <div class="hostrow">\r
          <div class="ring">\r
            <svg viewBox="0 0 132 132" width="132" height="132">\r
              <circle cx="66" cy="66" r="56" fill="none" stroke="var(--grid)" stroke-width="10"></circle>\r
              <circle id="host-ring" cx="66" cy="66" r="56" fill="none" stroke="var(--accent)" stroke-width="10"\r
                      stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="351.86"></circle>\r
            </svg>\r
            <div class="val"><b id="host-util">--</b><span>CPU</span></div>\r
          </div>\r
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
      <div class="hcol hcol-c">\r
        <div class="diskstrip" id="disk-rows"><div class="drow"><div><div class="dname">存储</div><div class="dmeta">读取中…</div></div></div></div>\r
        <div class="chart">\r
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>\r
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存 %</span><span id="host-range" style="margin-left:auto"></span></div>\r
        </div>\r
      </div>\r
    </div>\r
  </section>\r
</main>'''
s = s[:i] + host + s[j + len('</main>'):]

io.open(P, "wb").write(s.encode("utf-8"))
print("OK bytes=%d md5=%s" % (len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest()))
