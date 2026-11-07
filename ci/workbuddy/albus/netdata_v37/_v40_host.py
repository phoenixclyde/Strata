# -*- coding: utf-8 -*-
"""v40b：主机卡从「三栏」改成「两栏」。
三栏的问题：中栏只有 8 块瓦片（2 行 116px），右栏是存储表+走势（撑满 267px），
左栏更矮 => 中栏下方凭空空出 150px，就是机主说的「空多空少」。
两栏后：左栏 = 数值条 + 8 瓦片（1fr 行高，自己撑满），右栏 = 存储表 + 走势（撑满），
两栏同高同底，没有一处是「为对齐而留的白」。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

OLD = '''    <div class="hostgrid">
      <div class="hcol hcol-a">
        <div class="cpunum"><b id="host-util">--</b><span>CPU %</span></div>
        <div class="hostbars">
          <div class="bar">
            <div class="lab"><span>CPU</span><b></b></div>
            <div class="track"><i id="host-cpu-bar" style="width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2))"></i></div>
          </div>
          <div class="bar">
            <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>
            <div class="track stack">
              <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
              <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>
            </div>
            <div class="sub2" id="host-ram-dtl">--</div>
          </div>
        </div>
      </div>
      <div class="hcol hcol-b">
        <div class="tiles">'''

NEW = '''    <div class="hostgrid">
      <div class="hostmain">
        <div class="hstrip">
          <div class="cpunum"><b id="host-util">--</b><span>CPU %</span></div>
          <div class="hostbars">
            <!-- CPU 条与左边 38px 的大数字是同一个读数，留着只是重复;hidden 保留节点供 JS 写入 -->
            <div class="bar" hidden>
              <div class="track"><i id="host-cpu-bar" style="width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2))"></i></div>
            </div>
            <div class="bar">
              <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>
              <div class="track stack">
                <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
                <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>
              </div>
              <div class="sub2" id="host-ram-dtl">--</div>
            </div>
          </div>
        </div>
        <div class="tiles">'''
assert s.count(OLD) == 1, s.count(OLD)
s = s.replace(OLD, NEW)

OLD2 = '''        </div>
      </div>
      <div class="hcol hcol-c">
        <div class="diskstrip" id="disk-rows">'''
NEW2 = '''        </div>
      </div>
      <div class="hostside">
        <div class="diskstrip" id="disk-rows">'''
assert s.count(OLD2) == 1, s.count(OLD2)
s = s.replace(OLD2, NEW2)

# --- CSS：三栏 -> 两栏 ---
OLD3 = '''  /* ---------- 主机：三栏 + 竖发丝线 ---------- */
  .hostgrid{display:grid;grid-template-columns:236px minmax(0,1fr) minmax(0,1.02fr);
            gap:0;height:100%;align-items:start}
  .hostgrid > .hcol{min-width:0;display:flex;flex-direction:column;padding:0 22px}
  .hostgrid > .hcol:first-child{padding-left:0}
  .hostgrid > .hcol:last-child{padding-right:0}
  .hostgrid > .hcol + .hcol{border-left:1px solid var(--line)}
  .hcol-a{gap:10px}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:var(--fs-6);font-weight:600;line-height:1;
            letter-spacing:-.04em;font-variant-numeric:tabular-nums}
  .cpunum span{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.1em}
  .hostbars{display:flex;flex-direction:column;gap:16px}
  /* CPU 那个数值已在上面用 38px 写过一遍，条上再写一遍就是重复 => 只留条 */
  .hcol-a .hostbars .bar:first-child .lab{display:none}
  .hcol-b .tiles{margin-top:0}
  .hcol-c{gap:12px;height:100%}'''

NEW3 = '''  /* ---------- 主机：两栏（左=数值+8 瓦片，右=存储表+走势）+ 竖发丝线 ---------- */
  .hostgrid{display:grid;grid-template-columns:minmax(0,1.08fr) minmax(0,1fr);
            gap:0;height:100%;align-items:stretch}
  .hostgrid > div{min-width:0;min-height:0;display:flex;flex-direction:column;padding:0 22px}
  .hostgrid > div:first-child{padding-left:0}
  .hostgrid > div:last-child{padding-right:0;border-left:1px solid var(--line)}
  .hostmain{gap:14px}
  .hostside{gap:12px}
  /* 第一行：38px 大数字 + 内存条（CPU 条已隐藏，同一个数不写两遍） */
  .hstrip{display:grid;grid-template-columns:auto minmax(0,1fr);gap:24px;align-items:center;flex:0 0 auto}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:var(--fs-6);font-weight:600;line-height:1;
            letter-spacing:-.04em;font-variant-numeric:tabular-nums}
  .cpunum span{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.1em}
  .hostbars{display:flex;flex-direction:column;gap:8px;min-width:0}
  /* 瓦片行高 1fr：吃掉左栏剩余高度 => 左栏底边与右栏齐平，不留空 */
  .hostmain .tiles{flex:1 1 auto;grid-auto-rows:minmax(0,1fr);margin-top:0}'''

assert s.count(OLD3) == 1, s.count(OLD3)
s = s.replace(OLD3, NEW3)

# 媒体查询里旧类名
s = s.replace('''    .hostgrid{grid-template-columns:200px minmax(0,1fr) minmax(0,1fr)}
    .hostgrid > .hcol{padding:0 16px}''',
'''    .hostgrid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
    .hostgrid > div{padding:0 16px}''')
s = s.replace('''    .hostgrid{grid-template-columns:minmax(0,1fr)}
    .hostgrid > .hcol{padding:0;border-left:0}
    .hostgrid > .hcol + .hcol{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}
    .hcol-c{height:auto}''',
'''    .hostgrid{grid-template-columns:minmax(0,1fr)}
    .hostgrid > div{padding:0;border-left:0}
    .hostgrid > div + div{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}
    .hostside{height:auto}''')

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
