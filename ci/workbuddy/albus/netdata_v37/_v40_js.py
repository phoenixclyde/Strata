# -*- coding: utf-8 -*-
"""v40 JS：存储表改成「一个表头 + 两行数据」。
原来每行都自带 读/写/温度/寿命 四个小标签 => 两行盘就重复了两遍，是「信息重复」的直接来源。
表头只出一次，数据行只出值。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

OLD_INIT = '    var html = "", rdSum = 0, wrSum = 0, nIO = 0;'
NEW_INIT = ('    // [v40] 表头只出一次；数据行不再重复四个中文标签（原来两行盘 = 八个小标签）\n'
            '    var html = \'<div class="dhead"><div>盘</div><div>读</div><div>写</div>'
            '<div>温度</div><div>寿命</div><div>健康</div></div>\', rdSum = 0, wrSum = 0, nIO = 0;')
assert s.count(OLD_INIT) == 1, s.count(OLD_INIT)
s = s.replace(OLD_INIT, NEW_INIT)

OLD_ROW = """      html += '<div class="drow">'
        + '<div><div class="dname">' + model + '</div><div class="dmeta">' + meta + '</div></div>'
        + '<div class="dio"><div class="k">读</div><div class="v">' + rateTxt(rd) + '</div></div>'
        + '<div class="dio"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="dio"><div class="k">温度</div><div class="v">' + fmt(m.temp, 0) + '<small>°C</small></div></div>'
        + '<div class="dio' + lifeLvl + '" title="' + lifeTitle + '"><div class="k">寿命</div><div class="v">'
        +   (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>'
        + '<div class="dstat ' + hCls + '">' + hTxt + '</div>'
        + '</div>';"""
NEW_ROW = """      html += '<div class="drow">'
        + '<div class="dname-cell"><div class="dname">' + model + '</div><div class="dmeta">' + meta + '</div></div>'
        + '<div class="dio" title="读">' + rateTxt(rd) + '</div>'
        + '<div class="dio" title="写">' + rateTxt(wr) + '</div>'
        + '<div class="dio" title="温度">' + fmt(m.temp, 0) + '<small>°C</small></div>'
        + '<div class="dio' + lifeLvl + '" title="' + lifeTitle + '">'
        +   (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div>'
        + '<div class="dstat ' + hCls + '">' + hTxt + '</div>'
        + '</div>';"""
assert s.count(OLD_ROW) == 1, s.count(OLD_ROW)
s = s.replace(OLD_ROW, NEW_ROW)

# 初始占位（disk-rows 里原来那行「存储 / 读取中…」）也对齐成表头 + 一行占位
OLD_PH = ('<div class="diskstrip" id="disk-rows"><div class="drow"><div><div class="dname">存储</div>'
          '<div class="dmeta">读取中…</div></div></div></div>')
NEW_PH = ('<div class="diskstrip" id="disk-rows"><div class="dhead"><div>盘</div><div>读</div><div>写</div>'
          '<div>温度</div><div>寿命</div><div>健康</div></div>'
          '<div class="drow"><div class="dname-cell"><div class="dname">存储</div>'
          '<div class="dmeta">读取中…</div></div></div></div>')
assert s.count(OLD_PH) == 1, s.count(OLD_PH)
s = s.replace(OLD_PH, NEW_PH)

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
