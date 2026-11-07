# -*- coding: utf-8 -*-
"""v42：只解决两件事
① 高度一致：main 两行改 1fr 1fr（三张卡同高），图表定高 112 且吸底 => 三张图同尺寸
② 同类一致：环 104（三处）、瓦片 48（三处）、图表 112（三处）、磁盘卡同宽同高
"""
import io, hashlib, re

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def match_div(t, i):
    depth = 0
    for m in re.finditer(r"<div\b|</div>", t[i:]):
        if m.group(0) == "</div>":
            depth -= 1
            if depth == 0:
                return i + m.end()
        else:
            depth += 1
    raise ValueError("unbalanced")


def rebuild_card(t, sec_id):
    """把显卡卡里的 .bar 从 .top 之前挪进 .top 右列（tiles 上方），包一层 .gr"""
    sec = t.find('id="%s"' % sec_id)
    assert sec > 0, sec_id
    bar_s = t.find('<div class="bar">', sec)
    assert bar_s > 0
    bar = t[bar_s:match_div(t, bar_s)]
    t = t[:bar_s] + t[match_div(t, bar_s):]

    top_s = t.find('<div class="top">', sec)
    top_e = match_div(t, top_s)
    ring_s = t.find('<div class="ring">', top_s)
    ring_e = match_div(t, ring_s)
    tiles_s = t.find('<div class="tiles">', top_e and ring_e)
    tiles_e = match_div(t, tiles_s)
    assert top_s < ring_s < ring_e < tiles_s < tiles_e

    ring = t[ring_s:ring_e]
    tiles = t[tiles_s:tiles_e]
    ind = " " * (t.rfind("\n", 0, top_s) + 1 and (top_s - t.rfind("\n", 0, top_s) - 1))
    base = t.rfind("\n", 0, top_s) + 1
    pad = top_s - base
    p = " " * pad

    def reind(block, n):
        lines = block.split("\n")
        mn = min((len(l) - len(l.lstrip(" ")) for l in lines if l.strip()), default=0)
        return "\n".join(((" " * n) + l[mn:]) if l.strip() else l for l in lines)

    new = (p + '<div class="top">\n'
           + reind(ring, pad + 2) + "\n"
           + p + '  <div class="gr">\n'
           + reind(bar, pad + 4) + "\n"
           + reind(tiles, pad + 4) + "\n"
           + p + "  </div>\n"
           + p + "</div>")
    return t[:top_s] + new + t[top_e:]


s = rebuild_card(s, "card-nvd")
s = rebuild_card(s, "card-amd")

# ---------- 主机卡左半：38px 数字 -> 环形（与显卡卡同构、同尺寸） ----------
OLD_HL = re.search(r"<div class=\"hostleft\">.*?<div class=\"chart\">", s, re.S)
assert OLD_HL, "hostleft 未找到"
NEW_HL = '''<div class="hostleft">
        <div class="top">
          <div class="ring">
            <svg viewBox="0 0 132 132" width="132" height="132">
              <circle cx="66" cy="66" r="56" fill="none" stroke="var(--grid)" stroke-width="11"></circle>
              <circle id="host-ring" cx="66" cy="66" r="56" fill="none" stroke="var(--accent)" stroke-width="11"
                      stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="351.86"></circle>
            </svg>
            <div class="val"><b id="host-util">--</b><span>利用率 %</span></div>
          </div>
          <div class="hram">
            <div class="lab"><span>内存</span><b id="host-ram-txt">--</b></div>
            <div class="track stack">
              <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
              <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 45%, transparent)"></i>
            </div>
            <div class="sub2" id="host-ram-dtl">--</div>
          </div>
          <!-- CPU 条与环内数字同源，保留节点供 JS 写入但不显示 -->
          <div class="bar" hidden><div class="track"><i id="host-cpu-bar" style="width:0%"></i></div></div>
        </div>
        <div class="chart">'''
s = s[:OLD_HL.start()] + NEW_HL + s[OLD_HL.end():]

# ---------- CSS ----------
def rep(a, b):
    """s 已在开头归一成 LF，这里不要再转 CRLF（转了反而一处都匹配不上）。"""
    global s
    assert s.count(a) == 1, (s.count(a), a[:60])
    s = s.replace(a, b)

rep("    grid-template-rows:auto 415px minmax(min-content,1fr);",
    "    /* 三张卡同高：两行 1fr */\n    grid-template-rows:auto 1fr 1fr;")

rep("  .ring{position:relative;width:128px;height:128px}",
    "  .ring{position:relative;width:104px;height:104px}")

rep("  .ring .val b{font-size:var(--fs-6);font-weight:600;line-height:1;letter-spacing:-.04em;",
    "  .ring .val b{font-size:var(--fs-5);font-weight:600;line-height:1;letter-spacing:-.03em;")

rep("  .top{display:grid;grid-template-columns:128px minmax(0,1fr);gap:20px;align-items:center;flex:0 0 auto}",
    "  .top{display:grid;grid-template-columns:104px minmax(0,1fr);gap:16px;align-items:start;flex:0 0 auto}")
rep("  #nvd-body{display:flex;flex-direction:column;min-height:0;flex:1 1 auto}",
    "  #nvd-body{display:flex;flex-direction:column;min-height:0;flex:1 1 auto}\n  .gr{display:flex;flex-direction:column;gap:10px;min-width:0}")

rep("  .tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));\n         grid-auto-rows:54px;gap:8px;margin-top:12px}",
    "  .tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));\n         grid-auto-rows:48px;gap:8px;margin-top:12px}")

rep("  .tile{min-width:0;padding:5px 10px;", "  .tile{min-width:0;padding:4px 9px;")
rep("  .tile .v{font-family:var(--mono);font-size:var(--fs-4);font-weight:600;line-height:1.1;",
    "  .tile .v{font-family:var(--mono);font-size:20px;font-weight:600;line-height:1.1;")
rep("  .tile .k{font-size:var(--fs-1);color:var(--dim2);margin-bottom:4px;letter-spacing:.02em;",
    "  .tile .k{font-size:10px;color:var(--dim2);margin-bottom:3px;letter-spacing:.02em;")

# 图表：定高 + 吸底 => 三张同尺寸
rep("  .chart{margin-top:14px;display:flex;flex-direction:column;min-height:0;flex:1 1 auto}\n  .chart svg{display:block;width:100%;flex:1 1 0;height:0;min-height:72px}",
    """  /* 图表定高 112（绘图 88 + 图例 24）并吸底：三张卡的行高相同 => 三张图必然同尺寸；
     多余高度落在图上方（深色底上等同内边距），不会把某一张图拉长。 */
  .chart{margin-top:auto;display:flex;flex-direction:column;min-height:0;flex:0 0 auto;height:112px}
  .chart svg{display:block;width:100%;flex:1 1 auto;height:0;min-height:0}""")

# 主机左半：环 + 内存条同一行（与显卡卡 .top 同栅格）
rep("""  /* 左上：CPU 主值 | 竖线 | 内存条 */
  .hprim{display:grid;grid-template-columns:168px minmax(0,1fr);gap:0 22px;align-items:center;flex:0 0 auto}
  .hprim > .hram{border-left:1px solid var(--line);padding-left:22px}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:var(--fs-6);font-weight:600;line-height:1;
            letter-spacing:-.04em;font-variant-numeric:tabular-nums}
  .cpunum span{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.1em}
  .hram .lab{display:flex;align-items:baseline;gap:10px;font-size:var(--fs-1);
             color:var(--dim2);margin-bottom:6px}""",
    """  /* 左半与显卡卡同构：环 + 右侧信息块（.top 共用同一套栅格） */
  .hram{min-width:0;align-self:center;max-width:360px}
  .hram .lab{display:flex;align-items:baseline;gap:10px;font-size:var(--fs-1);
             color:var(--dim2);margin-bottom:6px}""")

rep("  .hostright .tiles{grid-auto-rows:54px;margin-top:0}",
    "  .hostright .tiles{grid-auto-rows:48px;margin-top:0}")

# 状态栏四组：只留能区分四条的间隔，右侧留白给以后新增
rep("""  .hstat{display:flex;flex-wrap:nowrap;align-items:center;justify-content:space-between;
         gap:0 14px;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}""",
    """  .hstat{display:flex;flex-wrap:nowrap;align-items:center;justify-content:flex-start;
         gap:0;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}""")
rep("""  .hsg + .hsg{border-left:1px solid var(--line);padding-left:14px}""",
    """  /* 组间只留 12+12：够区分四段即可，右侧空出来给以后新增的格子 */
  .hsg + .hsg{border-left:1px solid var(--line);margin-left:12px;padding-left:12px}""")

# 磁盘卡：竖排两张，宽度与高度一致
rep("  .dcards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;flex:0 0 auto}",
    "  .dcards{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;flex:0 0 auto}")

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
