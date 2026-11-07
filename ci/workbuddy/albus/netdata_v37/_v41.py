# -*- coding: utf-8 -*-
"""v41：按机主 5 条意见改
1) 主机卡内部中线与上面两张显卡卡之间的间隙中心对齐（1fr/1fr => 分隔线正好落在 959）
2) 状态栏单行（去掉分组色块，改竖发丝线；字号 10.5/11，item 间距 7）
3) 同类元素同尺寸：所有瓦片 54px 高、同 padding/圆角
4) 磁盘改成卡片（两张并排，各自 名称/健康 + 元信息 + 读/写/温度/寿命）
5) 主机：小卡片全在右半，趋势图放左下
"""
import io, hashlib, re

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def cut(t, start_mark, end_mark):
    """返回 (start_idx, end_idx)：从 start_mark 所在行首，到 end_mark 所在行首。"""
    i = t.find(start_mark)
    assert i > 0, start_mark
    i = t.rfind("\n", 0, i) + 1
    j = t.find(end_mark, i)
    assert j > i, end_mark
    j = t.rfind("\n", 0, j) + 1
    return i, j


def swap(t, start_mark, end_mark, new):
    i, j = cut(t, start_mark, end_mark)
    return t[:i] + new + t[j:]


# ---------------- 1. 状态栏：单行 ----------------
HSTAT = """  /* 状态栏：**一行**。23 格 + 4 组，靠 10.5px 标签 / 11px 数值 / 7px 间距塞进 1816px。
     分组不再用色块标题（占 150px），改竖发丝线 —— 省下来的宽度正好够一行。 */
  .hstat{display:flex;flex-wrap:nowrap;align-items:center;justify-content:space-between;
         gap:0 14px;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
  .hsg{display:flex;flex-wrap:nowrap;align-items:center;gap:0 7px;min-width:0;white-space:nowrap}
  .hsg + .hsg{border-left:1px solid var(--line);padding-left:14px}
  .hsg > .hsl{display:none}
  .hsi{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;color:var(--dim2);white-space:nowrap}
  .hsi i{width:5px;height:5px;border-radius:50%;background:var(--dim2);flex:0 0 auto}
  .hsi b{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--text);letter-spacing:0}
  .hsi.ok i{background:var(--good)}
  .hsi.warn i{background:var(--warn)}  .hsi.warn b{color:var(--warn)}
  .hsi.bad i{background:var(--bad)}    .hsi.bad b{color:var(--bad)}
  .hsi.defer i{background:transparent;box-shadow:inset 0 0 0 1.5px var(--warn)}
  .hsi.defer b{color:var(--text)}
  .hsi.busy b{font-size:12px;font-weight:700;color:var(--warn);letter-spacing:.02em}

"""
s = swap(s, "  /* 2×2 固定栅格", "  /* ---------- 主体栅格", HSTAT)

# ---------------- 2. 主机：1fr/1fr 对齐 + 卡片全在右半 ----------------
HOST = """  /* ---------- 主机：左右各半（分隔线正好落在两张显卡卡的间隙中心）+ 竖发丝线 ---------- */
  .hostgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
            gap:0;height:100%;align-items:stretch}
  .hostgrid > div{min-width:0;min-height:0;display:flex;flex-direction:column;padding:0 22px}
  .hostgrid > div:first-child{padding-left:0}
  .hostgrid > div:last-child{padding-right:0;border-left:1px solid var(--line)}
  /* 左上：CPU 主值 | 竖线 | 内存条 */
  .hprim{display:grid;grid-template-columns:168px minmax(0,1fr);gap:0 22px;align-items:center;flex:0 0 auto}
  .hprim > .hram{border-left:1px solid var(--line);padding-left:22px}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:var(--fs-6);font-weight:600;line-height:1;
            letter-spacing:-.04em;font-variant-numeric:tabular-nums}
  .cpunum span{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.1em}
  .hram .lab{display:flex;align-items:baseline;gap:10px;font-size:var(--fs-1);
             color:var(--dim2);margin-bottom:6px}
  .hram .lab b{font-family:var(--mono);font-size:var(--fs-2);font-weight:600;color:var(--text)}
  /* 右下：小卡片（8 瓦片 + 2 磁盘卡）；瓦片 54px 与显卡卡**同尺寸** */
  .hostright{gap:10px}
  .hostright .tiles{grid-auto-rows:54px;margin-top:0}
  /* 左下：走势吃掉剩余高度 */
  .hostleft .chart{margin-top:12px}

"""
s = swap(s, "  /* ---------- 主机：两栏", "  /* ---------- 存储表", HOST)

# ---------------- 3. 磁盘卡片 ----------------
DISK = """  /* ---------- 磁盘卡片：两张并排，与瓦片同材质同圆角 ---------- */
  .dcards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;flex:0 0 auto}
  .dcard{min-width:0;padding:9px 12px 10px;border-radius:8px;
         background:var(--tile-bg);border:1px solid var(--line-soft);
         display:flex;flex-direction:column;gap:0}
  .dcard:hover{background:color-mix(in srgb, var(--text) 6%, transparent)}
  .dhead2{display:flex;align-items:baseline;gap:8px;min-width:0}
  .dname{font-size:12.5px;font-weight:600;letter-spacing:-.01em;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
  .dmeta{font-size:10px;line-height:1.3;color:var(--dim2);font-family:var(--mono);
         margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dvals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px}
  .dv{min-width:0}
  .dv span{display:block;font-size:10px;color:var(--dim2);letter-spacing:.02em}
  .dv b{display:block;font-family:var(--mono);font-size:13.5px;font-weight:600;margin-top:2px;
        letter-spacing:-.02em;white-space:nowrap;font-variant-numeric:tabular-nums}
  .dv b small{font-size:10px;color:var(--dim2);font-weight:400;margin-left:1px}
  .dv.warn b{color:var(--warn)}
  .dv.bad b{color:var(--bad)}
  .dstat{margin-left:auto;font-size:10.5px;font-weight:600;letter-spacing:.04em;white-space:nowrap}
  .dstat.ok{color:var(--good)}
  .dstat.bad{color:var(--bad)}
  .dstat.na{color:var(--dim2);font-weight:400}

"""
s = swap(s, "  /* ---------- 存储表", "  /* ---------- 页脚", DISK)

# 响应式里旧类名
s = s.replace("""    .hostgrid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
    .hostgrid > div{padding:0 16px}""",
"""    .hostgrid > div{padding:0 14px}""")
s = s.replace("""  @media (max-width:1300px){
    .hstat{grid-template-columns:minmax(0,1fr)}
  }
""", "")

# ---------------- 4. 主机卡 HTML ----------------
NEW_HOST = """<section class="card wide" id="card-host">
    <div class="chead">
      <span class="badge" style="color:var(--accent2)">HOST</span>
      <h2>主机</h2><span class="id" id="host-id"></span>
    </div>
    <div class="hostgrid">
      <div class="hostleft">
        <div class="hprim">
          <div class="cpunum"><b id="host-util">--</b><span>CPU %</span></div>
          <div class="hram">
            <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>
            <div class="track stack">
              <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
              <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>
            </div>
            <div class="sub2" id="host-ram-dtl">--</div>
          </div>
          <!-- CPU 条与左侧 38px 大数字同源，保留节点但不显示（JS 仍会写宽度） -->
          <div class="bar" hidden><div class="track"><i id="host-cpu-bar" style="width:0%"></i></div></div>
        </div>
        <div class="chart">
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存 %</span><span id="host-range" style="margin-left:auto"></span></div>
        </div>
      </div>
      <div class="hostright">
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
        <div class="dcards" id="disk-rows"><div class="dcard"><div class="dhead2"><span class="dname">存储</span></div><div class="dmeta">读取中…</div></div></div>
      </div>
    </div>
  </section>"""

i = s.find('<section class="card wide" id="card-host">')
j = s.find("</section>", i) + len("</section>")
s = s[:i] + NEW_HOST + s[j:]

# ---------------- 5. renderSSD：卡片化 ----------------
OLD_INIT = re.search(r"    // \[v40\].*?var html = .*?rdSum = 0, wrSum = 0, nIO = 0;", s, re.S)
assert OLD_INIT, "找不到 renderSSD 初始化"
s = s[:OLD_INIT.start()] + '    var html = "", rdSum = 0, wrSum = 0, nIO = 0;' + s[OLD_INIT.end():]

OLD_ROW = re.search(r"      html \+= '<div class=\"drow\">'.*?\+ '</div>';", s, re.S)
assert OLD_ROW, "找不到磁盘行拼装"
NEW_ROW = """      html += '<div class="dcard">'
        + '<div class="dhead2"><span class="dname">' + model + '</span>'
        +   '<span class="dstat ' + hCls + '">' + hTxt + '</span></div>'
        + '<div class="dmeta">' + meta + '</div>'
        + '<div class="dvals">'
        +   '<div class="dv"><span>读</span><b>' + rateTxt(rd) + '</b></div>'
        +   '<div class="dv"><span>写</span><b>' + rateTxt(wr) + '</b></div>'
        +   '<div class="dv"><span>温度</span><b>' + fmt(m.temp, 0) + '<small>°C</small></b></div>'
        +   '<div class="dv' + lifeLvl + '" title="' + lifeTitle + '"><span>寿命</span><b>'
        +     (life === null ? "--" : fmt(life, 0)) + '<small>%</small></b></div>'
        + '</div>'
        + '</div>';"""
s = s[:OLD_ROW.start()] + NEW_ROW + s[OLD_ROW.end():]

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
