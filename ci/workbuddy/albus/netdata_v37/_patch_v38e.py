# -*- coding: utf-8 -*-
"""v38e：主机三栏宽度、内存行文案去重、存储行补回「温度」列、整体再收 60~90px。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
pairs = []

# 1) 主机三栏：左栏 340 太窄（环形 112 + 条只剩 200，内存行折行）
pairs.append((
    '  .hostgrid{grid-template-columns:340px minmax(0,1fr) minmax(0,1.32fr);gap:28px;height:100%}',
    '  .hostgrid{grid-template-columns:392px minmax(0,.92fr) minmax(0,1.28fr);gap:26px;height:100%}'))

# 2) 内存行：百分比已在总览 KPI 里，这里只留绝对量（去重）；明细不再重复「已用」
pairs.append((
    '''      setText("host-ram-txt", bytes(mUsed) + "/" + bytes(M.total) + " · " + fmt(upct, 1) + "%");''',
    '''      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total));'''))
pairs.append((
    '''      setText("host-ram-dtl", "已用 " + bytes(mUsed) + " · 可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree)
        + (hasNum(M.unevict) && M.unevict > 0 ? " · 锁定 " + bytes(M.unevict) : ""));''',
    '''      setText("host-ram-dtl", "可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree)
        + (hasNum(M.unevict) && M.unevict > 0 ? " · 锁定 " + bytes(M.unevict) : ""));'''))
pairs.append((
    '''      setText("host-ram-txt", bytes((usedM || 0) * 1048576) + " / " + bytes(totM * 1048576) +
        "  (" + fmt(totM ? (usedM || 0) / totM * 100 : 0, 1) + "%)");''',
    '''      setText("host-ram-txt", bytes((usedM || 0) * 1048576) + " / " + bytes(totM * 1048576));'''))

# 3) 存储行补回「温度」列（v38 第一版把温度塞进元信息，等于降级了关键数据）
pairs.append((
    '  .drow{display:grid;grid-template-columns:minmax(0,1fr) 92px 92px 64px;gap:14px;align-items:center;padding:7px 0}',
    '  .drow{display:grid;grid-template-columns:minmax(0,1fr) 88px 88px 60px 60px 56px;gap:12px;align-items:center;padding:7px 0}'))
pairs.append((
    '''        + '<div class="dio"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="dio' + lifeLvl + '" title="' + lifeTitle + '">''',
    '''        + '<div class="dio"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="dio"><div class="k">温度</div><div class="v">' + fmt(m.temp, 0) + '<small>°C</small></div></div>'
        + '<div class="dio' + lifeLvl + '" title="' + lifeTitle + '">'''))
pairs.append((
    '''        usedPct === null ? null : ("已用 " + fmt(usedPct, 1) + "%"),
        hasNum(m.written) ? (fmt(m.written / 1e9, 0) + " GB 写入") : null,''',
    '''        usedPct === null ? null : ("已用 " + fmt(usedPct, 1) + "%"),
        hasNum(m.written) ? (fmt(m.written / 1e9, 0) + " GB 写入") : null,'''))

# 4) 整体收高：环形 132 -> 104（左右两处），图表上限 132 -> 120
pairs.append((
    '  .hostrow .ring svg{width:112px;height:112px}',
    '  .hostrow .ring svg{width:104px;height:104px}'))
pairs.append((
    '  .card .chart svg{flex:1 1 auto;height:72px;min-height:72px;max-height:132px;width:100%;display:block}',
    '  .card .chart svg{flex:1 1 auto;height:72px;min-height:72px;max-height:120px;width:100%;display:block}'))
pairs.append((
    '  .top{', '  .top{'))

for old, new in pairs:
    if old == new:
        continue
    old = old.replace("\n", "\r\n") if "\n" in old and "\r\n" not in old else old
    new = new.replace("\n", "\r\n") if "\n" in new and "\r\n" not in new else new
    n = s.count(old)
    assert n == 1, (n, old[:60])
    s = s.replace(old, new)

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
